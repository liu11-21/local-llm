"""Versioned benchmark records and statistical definitions, independent of engines."""
import csv
from hashlib import sha256
from io import StringIO
import json
import math
from statistics import mean, pstdev
from uuid import uuid4

from task_manager import timestamp

SCHEMA = 1
TEXT_WORKLOADS = (
    {"id":"short","prompt":"Explain why the sky looks blue in two concise sentences."},
    {"id":"long","prompt":("A local AI application can execute models on a CPU, a GPU, or a compatible neural processor. "
                            "Execution time depends on the model, precision, input size, compilation, memory bandwidth, "
                            "and transfer overhead. A reliable comparison keeps the workload fixed, measures repeated "
                            "runs, records the actual device, and distinguishes startup from warm inference. "
                            "Summarize these ideas and explain why missing measurements imply uncertainty, "
                            "rather than proving that one device is slower.")},
)


def fingerprint(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    first = int(position)
    last = min(first+1,len(values)-1)
    return values[first]+(values[last]-values[first])*(position-first)


def statistics(samples):
    values = [sample["latency_ms"] for sample in samples if sample["phase"]=="measured"]
    if not values:
        return None
    if any(type(value) not in (int,float) or not math.isfinite(value) or value<0 for value in values):
        raise ValueError("Benchmark 量測數值無效。")
    return {"count":len(values),"mean_ms":mean(values),"stddev_ms":pstdev(values),
            "p50_ms":percentile(values,.5),"p95_ms":percentile(values,.95),
            "requests_per_second":1000/mean(values) if mean(values)>0 else None}


def parameters(data, kind):
    result = {"warmup":data.get("warmup",3),"iterations":data.get("iterations",10),
              "timeout":data.get("timeout",180),"memory_mib":data.get("memory_mib",4096),
              "max_tokens":data.get("max_tokens",32),"context":2048}
    for key,low,high in (("warmup",0,5),("iterations",2,50),("timeout",15,600),("memory_mib",512,8192),("max_tokens",8,128)):
        if type(result[key]) is not int or not low<=result[key]<=high:
            raise ValueError("Benchmark 次數、時間、記憶體或輸出設定超出限制。")
    if kind=="text":
        workloads = [dict(workload) for workload in TEXT_WORKLOADS]
    else:
        workloads = data.get("workloads")
        if not isinstance(workloads,list) or not 1<=len(workloads)<=4:
            raise ValueError("請提供一至四組張量工作量。")
        if len(json.dumps(workloads,allow_nan=False))>180000:
            raise ValueError("Benchmark 輸入超出大小限制。")
        normalized = []
        for index,workload in enumerate(workloads):
            if not isinstance(workload,dict) or not isinstance(workload.get("inputs"),list):
                raise ValueError("張量工作量需提供 inputs 陣列。")
            normalized.append({"id":f"input-{index+1}","inputs":workload["inputs"],"expected":workload.get("expected")})
        workloads = normalized
    return result,workloads


def comparable(left, right):
    """Conservative equivalence, never a ranking across workloads or missing evidence."""
    reasons = []
    if left["state"]!="completed" or right["state"]!="completed":
        reasons.append("至少一份測試未完整完成。")
    key = left.get("config",{}).get("comparison_key")
    if not key or key!=right.get("config",{}).get("comparison_key"):
        reasons.append("模型權重、量化、工作量或參數不同，或尚未完成環境紀錄。")
    if left["engine"]!=right["engine"]:
        reasons.append("不同 Backend，非完全等價比較。")
    versions = [{run["environment"].get("environment",{}).get("backend_version") for run in item["runs"] if run["state"]=="completed"}
                for item in (left,right)]
    if not versions[0] or None in versions[0] or versions[0]!=versions[1]:
        reasons.append("Backend 版本不同或未知。")
    precisions = [{run["environment"].get("preparation",{}).get("requested_precision") for run in item["runs"] if run["state"]=="completed"}
                  for item in (left,right)]
    if not precisions[0] or None in precisions[0] or precisions[0]!=precisions[1]:
        reasons.append("推理精度設定不同或未知。")
    return {"comparable":not reasons,"reasons":reasons,"scope":"相同工作量分開比較，驅動與裝置仍需核對。"}


class BenchmarkStore:
    def __init__(self, connect):
        self.connect = connect

    @staticmethod
    def initialize(db):
        db.executescript("""
            CREATE TABLE IF NOT EXISTS benchmark_sessions (
                id TEXT PRIMARY KEY,schema INTEGER NOT NULL,model TEXT NOT NULL,engine TEXT NOT NULL,
                state TEXT NOT NULL,created TEXT NOT NULL,finished TEXT,config TEXT NOT NULL,message TEXT,started TEXT);
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                id TEXT PRIMARY KEY,session TEXT NOT NULL,device TEXT NOT NULL,state TEXT NOT NULL,
                environment TEXT NOT NULL,summary TEXT,evidence TEXT,error TEXT);
            CREATE TABLE IF NOT EXISTS benchmark_measurements (
                run TEXT NOT NULL,ordinal INTEGER NOT NULL,workload TEXT NOT NULL,phase TEXT NOT NULL,
                metrics TEXT NOT NULL,PRIMARY KEY(run,ordinal));
            CREATE INDEX IF NOT EXISTS benchmark_runs_session ON benchmark_runs(session);
        """)
        db.execute("""UPDATE benchmark_sessions SET state='interrupted',finished=?,message='工作台已關閉，測試未自動重跑。'
                      WHERE state IN ('queued','running')""",(timestamp(),))
        db.execute("UPDATE benchmark_runs SET state='interrupted' WHERE state IN ('queued','running')")
        if db.execute("PRAGMA user_version").fetchone()[0]<11:
            db.execute("PRAGMA user_version=11")

    def create(self, model, engine, config):
        identity = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO benchmark_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (identity,SCHEMA,model,engine,"queued",timestamp(),None,json.dumps(config),None,None))
        return identity

    def begin(self, identity, config):
        with self.connect() as db:
            db.execute("UPDATE benchmark_sessions SET state='running',started=?,config=? WHERE id=?",
                       (timestamp(),json.dumps(config,allow_nan=False),identity))

    def environment(self, run, environment):
        with self.connect() as db:
            db.execute("UPDATE benchmark_runs SET environment=? WHERE id=?",(json.dumps(environment,allow_nan=False),run))

    def start_run(self, session, device, environment):
        identity = uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO benchmark_runs VALUES(?,?,?,?,?,?,?,?)",
                       (identity,session,device,"running",json.dumps(environment),None,None,None))
        return identity

    def measurement(self, run, sample):
        encoded = json.dumps(sample,allow_nan=False)
        with self.connect() as db:
            ordinal = db.execute("SELECT COUNT(*) FROM benchmark_measurements WHERE run=?",(run,)).fetchone()[0]
            db.execute("INSERT INTO benchmark_measurements VALUES(?,?,?,?,?)",
                       (run,ordinal,sample["workload"],sample["phase"],encoded))

    def finish_run(self, run, state, summary=None, evidence=None, error=None):
        with self.connect() as db:
            db.execute("UPDATE benchmark_runs SET state=?,summary=?,evidence=?,error=? WHERE id=?",
                       (state,json.dumps(summary) if summary is not None else None,
                        json.dumps(evidence) if evidence is not None else None,error,run))

    def finish(self, session, state, message):
        with self.connect() as db:
            db.execute("UPDATE benchmark_sessions SET state=?,finished=?,message=? WHERE id=?",
                       (state,timestamp(),message,session))

    def list(self, model="", device="", offset=0):
        with self.connect() as db:
            rows = db.execute("""SELECT s.id,s.model,s.engine,s.state,s.created,s.finished,s.message FROM benchmark_sessions s
                WHERE (?='' OR s.model=?) AND (?='' OR EXISTS
                (SELECT 1 FROM benchmark_runs r WHERE r.session=s.id AND r.device=?))
                ORDER BY s.created DESC,s.rowid DESC LIMIT 20 OFFSET ?""",(model,model,device,device,offset)).fetchall()
        return [dict(zip(("id","model","engine","state","created","finished","message"),row)) for row in rows]

    def get(self, identity):
        if not isinstance(identity,str) or len(identity)!=32 or any(char not in "0123456789abcdef" for char in identity):
            raise ValueError("Benchmark 識別碼無效。")
        with self.connect() as db:
            row = db.execute("SELECT schema,model,engine,state,created,finished,config,message,started FROM benchmark_sessions WHERE id=?",(identity,)).fetchone()
            if row is None:
                raise ValueError("找不到 Benchmark 紀錄。")
            result = dict(zip(("schema","model","engine","state","created","finished","config","message","started"),row))
            result.update(id=identity,config=json.loads(result["config"]),runs=[])
            for run,device,state,environment,summary,evidence,error in db.execute(
                    "SELECT id,device,state,environment,summary,evidence,error FROM benchmark_runs WHERE session=? ORDER BY rowid",(identity,)):
                samples = [json.loads(item[0]) for item in db.execute("SELECT metrics FROM benchmark_measurements WHERE run=? ORDER BY ordinal",(run,))]
                result["runs"].append({"id":run,"device":device,"state":state,"environment":json.loads(environment),
                                       "summary":json.loads(summary) if summary else None,"evidence":json.loads(evidence) if evidence else None,
                                       "error":error,"measurements":samples})
        return result

    def delete(self, identity):
        self.get(identity)
        with self.connect() as db:
            state = db.execute("SELECT state FROM benchmark_sessions WHERE id=?",(identity,)).fetchone()
            if state[0] in ("queued","running"):
                raise ValueError("請先取消或等待 Benchmark 結束。")
            db.execute("DELETE FROM benchmark_measurements WHERE run IN (SELECT id FROM benchmark_runs WHERE session=?)",(identity,))
            db.execute("DELETE FROM benchmark_runs WHERE session=?",(identity,))
            db.execute("DELETE FROM benchmark_sessions WHERE id=?",(identity,))

    def export(self, identity, format):
        result = self.get(identity)
        if format=="json":
            return json.dumps(result,ensure_ascii=False,indent=2)
        if format!="csv":
            raise ValueError("請選擇 JSON 或 CSV。")
        stream = StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(("session","run","model","engine","created","run_state","device","backend_version","driver","precision",
                         "model_hashes","workload_hash","workload","phase","ordinal","latency_ms","input_tokens","output_tokens",
                         "ttft_ms","decode_tokens_per_s","prefill_tokens_per_s","peak_ram_bytes"))
        hashes = {item["id"]:item["sha256"] for item in result["config"].get("workloads",[]) if "id" in item}
        def cell(value):
            return "'"+value if isinstance(value,str) and value.startswith(("=","+","-","@","\t","\r","\n")) else value
        for run in result["runs"]:
            for index,sample in enumerate(run["measurements"]):
                environment = run["environment"].get("environment",{})
                row = (identity,run["id"],result["model"],result["engine"],result["created"],run["state"],run["device"],
                       environment.get("backend_version"),environment.get("mapping",{}).get("driver"),
                       run["environment"].get("preparation",{}).get("requested_precision"),
                       json.dumps(result["config"].get("model_hashes",{})),hashes.get(sample["workload"]),
                       sample["workload"],sample["phase"],index,
                       *(sample.get(key) for key in ("latency_ms","input_tokens","output_tokens","ttft_ms","decode_tokens_per_s",
                                                     "prefill_tokens_per_s","peak_ram_bytes")))
                writer.writerow([cell(value) for value in row])
        return stream.getvalue()

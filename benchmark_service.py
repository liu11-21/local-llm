"""User-triggered benchmark orchestration; TaskManager alone owns execution lanes."""
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
from time import monotonic

from benchmark_adapters import Budget, LlamaBenchmark, OpenVINOBenchmark
from benchmark_core import BenchmarkStore, fingerprint, parameters, statistics
from hardware import detect_hardware
from load_plan import engine_devices


class BenchmarkService:
    def __init__(self, desktop):
        self.app = desktop
        self.store = BenchmarkStore(desktop.connect)
        with desktop.connect() as db:
            self.store.initialize(db)

    def plan(self):
        ov = self.app.openvino.status()
        models = [{"id":item["id"],"label":item["label"],"kind":item["kind"],"engine":"openvino",
                   "npu_candidate":item.get("npu_candidate",False)} for item in ov["models"]]
        models += [{"id":path.name,"label":path.name,"kind":"text","engine":"llama.cpp"}
                   for path in self.app.models.glob("*.gguf") if path.is_file()]
        try:llama_devices=[item[0] for item in engine_devices(self.app.engine())]
        except (ValueError,OSError):llama_devices=[]
        return {"schema":1,"models":models,"devices":{"openvino":ov["devices"] if ov["installed"] else [],
                "llama.cpp":["CPU",*llama_devices]},"limits":{"timeout_seconds":[15,600],"memory_mib":[512,8192]},
                "remote":{"state":"unsupported","reason":"Remote benchmark execution not implemented."},
                "automatic_execution":False,"hetero":"unsupported"}

    def prepare(self, data):
        if data.get("confirmed") is not True:
            raise ValueError("請確認 Benchmark 的裝置、負載及時間上限。")
        engine,model = data.get("engine"),data.get("model")
        match = next((item for item in self.plan()["models"] if item["engine"]==engine and item["id"]==model),None)
        if match is None:
            raise ValueError("請選擇已安裝的模型。")
        devices = data.get("devices")
        if (not isinstance(devices,list) or not 1<=len(devices)<=4 or len(set(devices))!=len(devices) or
            any(not isinstance(item,str) or not re.fullmatch(r"CPU|GPU(?:\.\d+)?|NPU(?:\.\d+)?|(?:Vulkan|CUDA)\d+",item) for item in devices)):
            raise ValueError("請選擇一至四個明確的裝置，HETERO 尚未支援。")
        if engine=="openvino" and any(item.startswith(("CUDA","Vulkan")) for item in devices):
            raise ValueError("OpenVINO 裝置格式不相容。")
        if engine=="llama.cpp" and any(item!="CPU" and not item.startswith(("CUDA","Vulkan")) for item in devices):
            raise ValueError("llama.cpp 裝置格式不相容。")
        params,workloads = parameters(data,match["kind"])
        if engine=="openvino" and match["kind"]=="text":
            params["context"] = 1024
        config = {"parameters":params,"workloads":[{"id":item["id"],"sha256":fingerprint(item)} for item in workloads],
                  "kind":match["kind"],"devices":devices,"cold_policy":"fresh process; OS file cache uncontrolled",
                  "memory_scope":"child process Job Object commit limit; peak RAM is working set",
                  "vram_limit":None,"temperature":None,"power_watts":None}
        identity = self.store.create(model,engine,config)
        return {"benchmark_id":identity,"model":model,"engine":engine,"parameters":params,
                "workloads":workloads,"devices":devices,"config":config}

    def submit(self, data):
        payload = self.prepare(data)
        identity = payload["benchmark_id"]
        def snapshot(task):
            record = self.store.get(identity)
            if task["state"] in ("cancelled","interrupted","failed") and record["state"] in ("queued","running"):
                self.store.finish(record["id"],task["state"],"Benchmark 未完成，已保留原始量測。")
        try:
            result = self.app.scheduler.submit("benchmark",payload,on_snapshot=snapshot)
        except Exception:
            self.store.finish(payload["benchmark_id"],"failed","無法加入任務佇列。")
            raise
        return {**result,"benchmark_id":payload["benchmark_id"]}

    def run(self, data, cancel, update):
        identity,params,config = data["benchmark_id"],data["parameters"],dict(data["config"])
        budget = Budget(cancel,params["timeout"])
        results = []
        try:
            if self.app.comfy.running():
                raise RuntimeError("請先結束 ComfyUI 工作並停止服務，再執行 Benchmark。")
            # This code runs only after TaskManager grants the compute lane.
            self.app.local.stop()
            self.app.active = None
            if data["engine"]=="openvino":
                directory,metadata = self.app.openvino.validate_model(data["model"])
                if not self.app.openvino.installed():
                    raise ValueError("PROVIDER_MISSING")
                adapter = OpenVINOBenchmark(self.app.openvino)
                config.update(model_hashes=metadata["hashes"],quantization=metadata.get("quantization"),
                              architecture=metadata.get("architecture"),model_bytes=metadata["bytes"])
            else:
                path = self.app.model(data["model"])
                digest = sha256()
                with path.open("rb") as stream:
                    while block:=stream.read(1024**2):
                        budget.check()
                        digest.update(block)
                config.update(model_hashes={"gguf":digest.hexdigest()},quantization="encoded-in-GGUF-hash",model_bytes=path.stat().st_size)
                adapter = LlamaBenchmark(self.app.engine(),path)
            free = detect_hardware(self.app.data).ram_available
            minimum = config["model_bytes"]+512*1024**2
            if minimum>params["memory_mib"]*1024**2 or free is not None and minimum>free:
                raise MemoryError("INSUFFICIENT_RAM")
            config["comparison_key"] = fingerprint({key:config.get(key) for key in
                ("parameters","workloads","kind","model_hashes","quantization","architecture")})
            self.store.begin(identity,config)
            windows = self.app.hardware_monitor.snapshot()
            thread = self.app.hardware_monitor.refresh_thread
            while thread and thread.is_alive():
                budget.check()
                thread.join(timeout=.1)
            windows = self.app.hardware_monitor.snapshot()
            for number,device in enumerate(data["devices"]):
                budget.check()
                environment = {"os":platform.platform(),"machine":platform.machine(),"runtime_id":data["engine"],
                    "cpu":platform.processor(),"hardware":windows,"driver":None,"backend_version":None,
                    "peak_vram_bytes":None,"vram_limit":"Per-process reliable VRAM sampling not available.",
                    "npu_memory_bytes":None,"started_monotonic":monotonic()}
                run = self.store.start_run(identity,device,environment)
                samples = []
                def receive(event):
                    budget.check()
                    if event.get("event")=="measurement":
                        sample = {key:value for key,value in event.items() if key!="event"}
                        self.store.measurement(run,sample)
                        samples.append(sample)
                        update(message=f"Benchmark {device} · {sample['workload']} · {sample['phase']} {sample['index']+1}",
                               benchmark_id=identity,received=len(samples),total=(1+params["warmup"]+params["iterations"])*len(data["workloads"]))
                    elif event.get("event") in ("environment","preparation"):
                        environment[event["event"]] = {key:value for key,value in event.items() if key!="event"}
                        self.store.environment(run,environment)
                        update(message=f"Benchmark {device} · 載入與編譯完成" if event["event"]=="preparation" else f"Benchmark {device} · 正在載入")
                try:
                    update(message=f"Benchmark {device} · {number+1}/{len(data['devices'])}，時間上限共 {params['timeout']} 秒",benchmark_id=identity)
                    result = adapter.run(data["model"],device,params,data["workloads"],windows["devices"],budget,receive)
                    summary = {workload["id"]:statistics([sample for sample in samples if sample["workload"]==workload["id"]])
                               for workload in data["workloads"]}
                    correct = all(sample.get("output_correct") is not False for sample in samples)
                    complete = all(sum(sample["workload"]==workload["id"] and sample["phase"]==phase for sample in samples)==count
                                   for workload in data["workloads"] for phase,count in
                                   (("first",1),("warmup",params["warmup"]),("measured",params["iterations"])))
                    state = "completed" if correct and complete else "failed"
                    self.store.finish_run(run,state,summary,result.get("evidence"),
                                          "INCOMPLETE_MEASUREMENTS" if not complete else None if correct else "OUTPUT_MISMATCH")
                    results.append(state)
                except Exception as error:
                    state,code = failure(error,budget)
                    self.store.finish_run(run,state,error=code)
                    results.append(state)
                    if state in ("cancelled","timeout"):
                        raise
            state = "completed" if all(item=="completed" for item in results) else "partial" if "completed" in results else "failed"
            self.store.finish(identity,state,"Benchmark 完成，請依相同工作量檢視數據與裝置證據。")
            return {"benchmark_id":identity,"message":f"Benchmark {state} · 已保存原始結果。"}
        except Exception as error:
            state,code = failure(error,budget)
            self.store.finish(identity,state,code)
            raise RuntimeError(code) from None

    def export(self, data):
        identity,format = data.get("id"),data.get("format")
        content = self.store.export(identity,format)
        directory = self.app.data/"exports"/"benchmarks"
        directory.mkdir(parents=True,exist_ok=True)
        if directory.is_symlink() or directory.resolve().parent!=self.app.data.resolve()/"exports":
            raise ValueError("匯出目錄不安全。")
        path = directory/f"benchmark-{identity}.{format}"
        if path.is_symlink():
            raise ValueError("匯出路徑不安全。")
        path.write_text(content,encoding="utf-8-sig" if format=="csv" else "utf-8")
        return {"path":str(path),"format":format}


def failure(error,budget):
    if budget.stop.is_set():
        return "cancelled","CANCELLED"
    if monotonic()>=budget.deadline or isinstance(error,TimeoutError):
        return "timeout","TIMEOUT"
    if isinstance(error,OSError) and getattr(error,"winerror",None)==4551:
        return "failed","NEEDS WINDOWS · Windows application control blocked this executable."
    if isinstance(error,MemoryError):
        return "failed","INSUFFICIENT_MEMORY"
    known = {"DEVICE_UNAVAILABLE","NPU_INCOMPATIBLE","PROVIDER_MISSING","CONTEXT_LIMIT","OUTPUT_LENGTH_MISMATCH",
             "INPUT_MISMATCH","INPUT_TOO_LARGE","OUTPUT_TOO_LARGE"}
    return "failed",str(error) if str(error) in known else "BACKEND_FAILED · 檢查引擎、驅動、模型相容性與記憶體上限。"

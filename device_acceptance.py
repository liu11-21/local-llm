"""Real E3-D end-to-end evidence. Imports prior measurements, never auto-benchmarks."""
import argparse
import json
from pathlib import Path
from shutil import copyfile
from time import monotonic,sleep
from uuid import uuid4

from desktop_worker import Desktop


def wait(app,job,seconds=180):
    end=monotonic()+seconds
    while monotonic()<end:
        value=app.rpc("job",job)
        if value["state"] not in ("queued","running"):return value
        sleep(.03)
    app.rpc("cancel",job)
    raise TimeoutError("Native acceptance timed out")


def import_history(app,folder):
    for name in ("benchmark-llama.json","benchmark-text.json","benchmark-tensor.json"):
        record=json.loads((folder/name).read_text(encoding="utf-8"))
        with app.connect() as db:
            db.execute("INSERT OR IGNORE INTO benchmark_sessions VALUES(?,?,?,?,?,?,?,?,?,?)",
                (record["id"],record["schema"],record["model"],record["engine"],record["state"],record["created"],record["finished"],
                 json.dumps(record["config"]),record["message"],record.get("started")))
            for run in record["runs"]:
                db.execute("INSERT OR IGNORE INTO benchmark_runs VALUES(?,?,?,?,?,?,?,?)",
                    (run["id"],record["id"],run["device"],run["state"],json.dumps(run["environment"]),json.dumps(run["summary"]),
                     json.dumps(run["evidence"]),run["error"]))
                for index,sample in enumerate(run["measurements"]):
                    db.execute("INSERT OR IGNORE INTO benchmark_measurements VALUES(?,?,?,?,?)",
                               (run["id"],index,sample["workload"],sample["phase"],json.dumps(sample)))


def public_job(job):
    result=job.get("result") or {}
    return {"id":job["id"],"state":job["state"],"started":job["started"],"finished":job["finished"],"error":job["error"],
            "resource_request":job.get("resource_request"),"execution":job.get("execution"),"nonempty_answer":bool(result.get("answer")),
            "team_run_id":result.get("team_run_id")}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True,help="Existing acceptance profile with imported models and GGUF")
    parser.add_argument("--runtime",type=Path,required=True)
    parser.add_argument("--profile",type=Path,required=True,help="Separate E3-D profile")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    app=Desktop(args.profile.resolve())
    app.openvino.runtime=args.runtime.resolve()
    reports=[]
    try:
        app.models.mkdir(exist_ok=True)
        model="SmolLM2-135M-Instruct-Q4_K_M.gguf"
        if not (app.models/model).exists():copyfile(args.source/"models"/model,app.models/model)
        for directory in (args.source/"openvino"/"models").iterdir():
            if directory.is_dir():app.openvino.import_model(str(directory.resolve()),__import__('threading').Event(),lambda **_:None)
        import_history(app,Path(__file__).parent/"docs"/"evidence"/"benchmark")
        wait(app,app.rpc("run",{"action":"openvino-detect"}))
        app.hardware_monitor.snapshot()
        if app.hardware_monitor.refresh_thread:app.hardware_monitor.refresh_thread.join(timeout=25)
        recommendation=app.rpc("runtime-recommend",{"task":"chat","model":model,"preference":"speed","workload":"short","reference":True})
        (args.output/"recommendation-real.json").write_text(json.dumps(recommendation,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        selected=next(item for item in recommendation["candidates"] if item["id"]==recommendation["recommended"])
        chosen=app.rpc("run",{"action":"chat","runtime":selected["runtime"],"model":model,"chat":uuid4().hex,"prompt":"Say hello in a short sentence.",
            "context":2048,"max_tokens":32,"policy":"local","execution":{"device":selected["device"],"confirmed":True}})
        answer=wait(app,chosen)
        reports.append({"case":"A-recommend-confirm-dispatch","status":"PASS" if answer["state"]=="completed" and answer["result"]["answer"] else "FAIL",
            "selected":selected["id"],"reference_only":True,"task":public_job(answer),"hardware_placement_limit":"llama.cpp configured layers are not full operator placement evidence"})
        tensor=next(item["id"] for item in app.openvino.status()["models"] if item["kind"]=="tensor")
        first=app.rpc("run",{"action":"chat","runtime":"local","model":model,"chat":uuid4().hex,"prompt":"Explain four useful applications of local AI in clear detail.",
            "context":2048,"max_tokens":256,"policy":"local","execution":{"device":"CPU","confirmed":True}})
        second=app.rpc("run",{"action":"openvino-infer","model":tensor,"inputs":[[[1]*512]],"execution":{"device":"GPU","confirmed":True}})
        overlap=[]
        until=monotonic()+180
        while monotonic()<until:
            a,b=app.rpc("job",first),app.rpc("job",second)
            with app.device_execution.lock:
                live=[]
                for scope in app.device_execution.scopes.values():
                    for kind,process in (("llama.cpp",scope.local.process),("openvino",scope.openvino.process)):
                        if process is not None and process.poll() is None:
                            live.append({"engine":kind,"device":scope.execution_target.device,"pid":process.pid})
            if len(live)>=2 and len(overlap)<5:overlap.append({"observed_monotonic":monotonic(),"processes":live})
            if a["state"] not in ("queued","running") and b["state"] not in ("queued","running"):break
            sleep(.01)
        expected=(b.get("result") or {}).get("inference",{}).get("outputs")==[[[256.0]*512]]
        reports.append({"case":"B-real-CPU-and-Intel-GPU-concurrent","status":"PASS" if a["state"]==b["state"]=="completed" and overlap and expected else "FAIL",
                        "overlapping_live_processes":overlap,"reference_output_correct":expected,"jobs":[public_job(a),public_job(b)]})
        text_model=next(item["id"] for item in app.openvino.status()["models"] if item["kind"]=="text")
        before=len(app.rpc("dispatch-runs",{}))
        rejected=False
        try:app.rpc("run",{"action":"chat","runtime":"openvino","model":text_model,"chat":uuid4().hex,"prompt":"Hello","max_tokens":32,
                "execution":{"device":"NPU","confirmed":True},"policy":"local"})
        except ValueError:rejected=True
        reports.append({"case":"C-no-NPU-no-silent-CPU-fallback","status":"PASS" if rejected and len(app.rpc("dispatch-runs",{}))==before else "FAIL",
            "available_devices":app.openvino.status()["devices"],"physical_npu":"NEEDS NPU","unsupported_model_npu_candidate":next(item for item in app.openvino.status()["models"] if item["id"]==text_model).get("npu_candidate")})
        plan=app.rpc("agent-plan",{"role":"general","runtime":"openvino","model":text_model,"prompt":"Say hello in one short sentence.","tools":[],"mode":"simple","policy":"local",
                                   "execution":{"device":"CPU","confirmed":True}})
        agent=wait(app,app.rpc("run",{"action":"agent","id":plan["id"],"version":plan["version"],"confirmed":True}))
        reports.append({"case":"OpenVINO-Agent-approved-plan","status":"PASS" if agent["state"]=="completed" and agent["result"]["answer"] else "FAIL","task":public_job(agent)})
        members=[{"id":f"m{index}","name":device,"role":"writer" if index==1 else "analyst","model":model,"runtime":"local","tools":[],"tokens":64,
                  "execution":{"device":device,"confirmed":True}} for index,device in ((1,"CPU"),(2,"Vulkan0"))]
        team=wait(app,app.rpc("run",{"action":"team-workflow","prompt":"Give one simple tip for using local AI.","policy":"local",
            "team":{"name":"Real CPU and Vulkan Team","mode":"parallel","lead":"m1","members":members,"seconds":120}}))
        run=app.team_store.get(team["result"]["team_run_id"]) if team["state"]=="completed" else None
        reports.append({"case":"Team-child-tasks-and-final-synthesis","status":"PASS" if run and all(node["state"]=="completed" for node in run["nodes"]) else "FAIL",
            "task":public_job(team),"nodes":[{"id":node["id"],"agent":node["agent"],"state":node["state"],"started":node.get("started"),"finished":node.get("finished")} for node in run["nodes"]] if run else [],
            "quality_limit":"Tiny-model semantic answer quality is not graded by this execution acceptance."})
        cancelled=app.rpc("run",{"action":"chat","runtime":"local","model":model,"chat":uuid4().hex,"prompt":"Write a detailed guide to local AI.","context":2048,"max_tokens":512,
                                   "execution":{"device":"CPU","confirmed":True},"policy":"local"})
        until=monotonic()+15
        while monotonic()<until:
            with app.device_execution.lock:started=any(scope.local.process is not None for scope in app.device_execution.scopes.values())
            if started:break
            sleep(.02)
        app.rpc("cancel",cancelled)
        stopped=wait(app,cancelled)
        recovery=wait(app,app.rpc("run",{"action":"openvino-infer","model":tensor,"inputs":[[[1]*512]],"execution":{"device":"GPU","confirmed":True}}))
        with app.device_execution.lock:clean=not app.device_execution.scopes
        reports.append({"case":"cancel-cleanup-recover","status":"PASS" if stopped["state"]=="cancelled" and recovery["state"]=="completed" and clean else "FAIL",
                        "cancelled":public_job(stopped),"recovery":public_job(recovery),"no_live_scopes":clean})
        shutting=app.rpc("run",{"action":"chat","runtime":"local","model":model,"chat":uuid4().hex,"prompt":"Write a long guide to local AI.","context":2048,"max_tokens":512,
                                "execution":{"device":"CPU","confirmed":True},"policy":"local"})
        until=monotonic()+15
        while monotonic()<until:
            with app.device_execution.lock:live=[scope.local.process.pid for scope in app.device_execution.scopes.values() if scope.local.process and scope.local.process.poll() is None]
            if live:break
            sleep(.02)
        app.close()
        interrupted=wait(app,shutting,15)
        with app.device_execution.lock:closed=not app.device_execution.scopes
        reports.append({"case":"application-close-cleans-live-process","status":"PASS" if live and interrupted["state"]=="interrupted" and closed else "FAIL",
                        "previously_live_pids":live,"task":public_job(interrupted),"no_live_scopes":closed})
        result={"source":"real-native-hardware","cases":reports,"hardware":app.hardware_monitor.snapshot(),
                "limits":{"NPU":"NEEDS NPU","other-vendor-GPU":"NOT RUN","physical-remote-GPU":"NEEDS REMOTE HOST","cloud":"NEEDS CLOUD AUTH"},
                "historical_benchmark_source":"Unmodified E3-C records imported from docs/evidence/benchmark; no Benchmark was run by recommendation."}
        (args.output/"acceptance-real.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (args.output/"dispatch-runs-real.json").write_text(json.dumps(app.rpc("dispatch-runs",{}),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"cases":[{"case":item["case"],"status":item["status"]} for item in reports]}),flush=True)
        if any(item["status"]!="PASS" for item in reports):raise RuntimeError("Native device acceptance failed")
    finally:app.close()


if __name__=="__main__":main()

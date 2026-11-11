"""Exercise cancellation and deadline against a real already-imported text model."""
import argparse
import json
from pathlib import Path
from time import monotonic,sleep

from desktop_worker import Desktop
from openvino_adapter import VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    app = Desktop(args.profile.resolve())
    app.openvino.runtime = args.source.resolve()/"openvino"/("runtime-"+VERSION)
    try:
        model = next(item["id"] for item in app.openvino.status()["models"] if item["kind"]=="text")
        reports = []
        for case in ("cancel","timeout"):
            job = app.rpc("run",{"action":"benchmark","engine":"openvino","model":model,"devices":["CPU"],
                "confirmed":True,"timeout":60 if case=="cancel" else 15,"iterations":50,"max_tokens":128})
            deadline = monotonic()+80
            while monotonic()<deadline:
                record = app.benchmarks.store.get(job["benchmark_id"])
                count = sum(len(run["measurements"]) for run in record["runs"])
                task = app.scheduler.snapshot(job["id"])
                if case=="cancel" and count and task["state"]=="running":
                    app.scheduler.snapshot(job["id"],cancel=True)
                if task["state"] not in ("queued","running"):
                    break
                sleep(.1)
            else:
                raise TimeoutError("Safety acceptance timed out")
            record = app.benchmarks.store.get(job["benchmark_id"])
            expected = "cancelled" if case=="cancel" else "timeout"
            reports.append({"case":case,"expected":expected,"state":record["state"],"raw_rows_retained":count,
                            "child_cleaned":app.openvino.process is None,"status":"PASS" if record["state"]==expected and count and app.openvino.process is None else "FAIL"})
        # Recovery runs after both process kills and must not reuse their cached state.
        job = app.rpc("run",{"action":"benchmark","engine":"openvino","model":model,"devices":["CPU"],
                             "confirmed":True,"timeout":60,"warmup":0,"iterations":2,"max_tokens":8})
        while app.scheduler.snapshot(job["id"])["state"] in ("queued","running"):
            sleep(.1)
        record = app.benchmarks.store.get(job["benchmark_id"])
        reports.append({"case":"recovery","state":record["state"],"status":"PASS" if record["state"]=="completed" else "FAIL"})
        output = {"source":"real-native-hardware","cases":reports}
        args.output.write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(output),flush=True)
        if any(item["status"]!="PASS" for item in reports):
            raise RuntimeError("Safety acceptance failed")
    finally:
        app.close()


if __name__=="__main__":
    main()

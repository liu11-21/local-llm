"""Run the actual managed OpenVINO Adapter through TaskManager on an acceptance PC."""
import argparse
import json
from pathlib import Path
import subprocess
from time import monotonic, sleep
from uuid import uuid4
from tempfile import TemporaryDirectory

from desktop_worker import Desktop
from download_recovery import owned
from openvino_adapter import VERSION

FIXTURE = """
import openvino as ov
from openvino import opset13 as op
import numpy as np
import sys
data=op.parameter([1,4],np.float32,name='input')
output=op.relu(op.multiply(data,op.constant(np.array([2,2,2,2],dtype=np.float32))))
ov.save_model(ov.Model([output],[data],'contract-fixture'),sys.argv[1],compress_to_fp16=False)
"""


def wait(worker, action, data):
    job = worker.scheduler.submit(action,data)
    until = monotonic()+210
    while monotonic()<until:
        value = worker.scheduler.snapshot(job["id"])
        if value["state"] not in ("running","queued"):
            return value
        sleep(.1)
    worker.scheduler.snapshot(job["id"],cancel=True)
    raise TimeoutError("Acceptance task timed out")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True,help="Local LLM data directory with the optional Runtime installed")
    parser.add_argument("--device",default="CPU")
    parser.add_argument("--model",help="An already-imported text model ID, or omit to create a small deterministic IR fixture")
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    source = args.data.resolve()/"openvino"
    runtime = source/("runtime-"+VERSION)
    if not owned(runtime) or not (runtime/"READY.json").is_file():
        raise ValueError("Install the optional OpenVINO Runtime before running acceptance.")
    temporary = TemporaryDirectory(prefix="localllm-openvino-acceptance-")
    worker = Desktop(Path(temporary.name).resolve())
    worker.openvino.runtime = runtime
    try:
        if not worker.openvino.installed():
            raise ValueError("Install the optional OpenVINO Runtime in the app before running acceptance.")
        detect = wait(worker,"openvino-detect",{})
        status = worker.openvino.status()
        if args.device not in status["devices"]:
            record = {"status":"NEEDS NPU" if args.device.startswith("NPU") else "NEEDS GPU",
                      "devices":status["devices"],"detection":detect["state"]}
        elif args.model:
            if len(args.model)!=16 or any(char not in "0123456789abcdef" for char in args.model):
                raise ValueError("Invalid imported model ID")
            imported = wait(worker,"openvino-import",{"directory":str(source/"models"/args.model)})
            if imported["state"]!="completed":
                raise RuntimeError("Acceptance model import failed")
            job = wait(worker,"chat",{"runtime":"openvino","device":args.device,"model":imported["result"]["model"],
                                     "chat":uuid4().hex,"prompt":"Say hello in one short sentence.",
                                     "policy":"local","max_tokens":64})
            record = {"status":"PASS" if job["state"]=="completed" else "FAIL","scope":"text-generation-contract",
                      "task":job,"device_placement":"unverified"}
        else:
            folder = worker.openvino.root/"acceptance-fixture"
            folder.mkdir(exist_ok=True)
            subprocess.run([str(worker.openvino.runtime/"python.exe"),"-I","-B","-c",FIXTURE,
                            str(folder/"openvino_model.xml")],check=True,timeout=30,
                           creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            imported = wait(worker,"openvino-import",{"directory":str(folder)})
            if imported["state"]!="completed":
                raise RuntimeError("Acceptance model import failed")
            identity = imported["result"]["model"]
            job = wait(worker,"openvino-infer",{"model":identity,"device":args.device,"inputs":[[[1,2,3,4]]]})
            result = (job.get("result") or {}).get("inference",{})
            correct = result.get("outputs")==[[[2.0,4.0,6.0,8.0]]]
            verified = result.get("evidence",{}).get("verified_inference") is True
            record = {"status":"PASS" if correct and verified else "FAIL","scope":"deterministic-ir-contract",
                      "correct_output":correct,"task":job}
        record["runs"] = worker.rpc("openvino-runs",{})
        encoded = json.dumps(record,ensure_ascii=True,indent=2)
        if args.output:
            args.output.write_text(encoded+"\n",encoding="utf-8")
        print(encoded)
    finally:
        worker.close()
        temporary.cleanup()


if __name__=="__main__":
    main()

"""Real native benchmark acceptance. Never substitutes controlled data for hardware."""
import argparse
import json
from pathlib import Path
import subprocess
from time import monotonic,sleep

from desktop_worker import Desktop
from openvino_adapter import VERSION

FIXTURE = """
import openvino as ov
from openvino import opset13 as op
import numpy as np
import sys
data=op.parameter([-1,512],np.float32,name='input')
weights=op.constant(np.full((512,512),0.5,dtype=np.float32))
ov.save_model(ov.Model([op.matmul(data,weights,False,False)],[data],'benchmark-matmul-512'),sys.argv[1],compress_to_fp16=False)
"""


def wait(app,action,data):
    job = app.rpc("run",{"action":action,**data})
    until = monotonic()+620
    while monotonic()<until:
        state = app.scheduler.snapshot(job["id"])
        if state["state"] not in ("running","queued"):
            return state
        sleep(.1)
    app.scheduler.snapshot(job["id"],cancel=True)
    raise TimeoutError("Acceptance timed out")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--profile",type=Path,required=True,help="Separate acceptance profile, not the user's normal data")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--text-model",default="6801f654268e3090")
    parser.add_argument("--llama-source",type=Path)
    parser.add_argument("--llama-engine",type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    app = Desktop(args.profile.resolve())
    app.openvino.runtime = args.source.resolve()/"openvino"/("runtime-"+VERSION)
    try:
        if not app.openvino.installed():
            raise ValueError("Install the optional Runtime first")
        wait(app,"openvino-detect",{})
        folder = app.openvino.root/"benchmark-fixture"
        folder.mkdir(exist_ok=True)
        subprocess.run([str(app.openvino.runtime/"python.exe"),"-I","-B","-c",FIXTURE,str(folder/"openvino_model.xml")],
                       check=True,timeout=30,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        imported = wait(app,"openvino-import",{"directory":str(folder)})
        if imported["state"]!="completed":
            raise RuntimeError("Fixture import failed")
        model = imported["result"]["model"]
        devices = [device for device in ("CPU","GPU") if device in app.openvino.status()["devices"]]
        workloads = [{"inputs":[[[value]*512 for _ in range(batch)]],
                      "expected":[[[value*256]*512 for _ in range(batch)]]} for batch,value in ((1,1),(8,2))]
        for name,data in (("tensor",{"model":model,"devices":devices,"workloads":workloads}),
                          ("text",{"devices":["CPU"]})):
            if name=="text":
                imported = wait(app,"openvino-import",{"directory":str(args.source.resolve()/"openvino"/"models"/args.text_model)})
                if imported["state"]!="completed":
                    raise RuntimeError("Text model import failed")
                data["model"] = imported["result"]["model"]
            job = wait(app,"benchmark",{"engine":"openvino","confirmed":True,"timeout":600,**data})
            record = app.benchmarks.store.get(job["benchmark_id"])
            record["acceptance"] = {"data_source":"real-native-hardware","task_state":job["state"]}
            (args.output/f"benchmark-{name}.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(json.dumps({"case":name,"state":record["state"],"id":record["id"],"runs":[
                {"device":run["device"],"state":run["state"],"error":run["error"],"summary":run["summary"]} for run in record["runs"]]}),flush=True)
        absent = {"status":"NEEDS NPU","available_devices":app.openvino.status()["devices"],
                  "reason":"No NPU reported on acceptance hardware. No NPU inference claimed."}
        (args.output/"benchmark-npu.json").write_text(json.dumps(absent,indent=2)+"\n",encoding="utf-8")
        if args.llama_source:
            from shutil import copyfile
            app.models.mkdir(exist_ok=True)
            gguf = next((args.llama_source/"models").glob("SmolLM*.gguf"))
            copyfile(gguf,app.models/gguf.name)
            app.engine = lambda:args.llama_engine.resolve() if args.llama_engine else args.llama_source.resolve()/"engine-vulkan"/"llama-server.exe"
            # Explicit GPU attempt is retained even if this PC's application policy blocks discovery.
            job = wait(app,"benchmark",{"engine":"llama.cpp","model":gguf.name,"devices":["CPU","Vulkan0"],
                                        "confirmed":True,"timeout":180})
            record = app.benchmarks.store.get(job["benchmark_id"])
            record["acceptance"] = {"data_source":"real-native-hardware","task_state":job["state"]}
            (args.output/"benchmark-llama.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            print(json.dumps({"case":"llama.cpp","state":record["state"],"runs":[
                {"device":run["device"],"state":run["state"],"error":run["error"]} for run in record["runs"]]}),flush=True)
    finally:
        app.close()


if __name__=="__main__":
    main()

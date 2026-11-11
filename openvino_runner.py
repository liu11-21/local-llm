"""Isolated OpenVINO process. One bounded request, then unload and exit."""
import json
import os
import sys
from time import perf_counter

# Native plugins sometimes write to stdout. Reserve a separate descriptor for IPC.
protocol = os.fdopen(os.dup(sys.stdout.fileno()),"wb",buffering=0)
null = os.open(os.devnull,os.O_WRONLY)
os.dup2(null,1)
os.dup2(null,2)
os.close(null)


def emit(value):
    protocol.write(json.dumps(value,ensure_ascii=True,allow_nan=False).encode()+b"\n")


def main():
    request = json.loads(sys.stdin.buffer.readline(256*1024))
    os.environ["DO_NOT_TRACK"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import openvino as ov
    core = ov.Core()
    available = list(core.available_devices)
    if request["op"]=="detect":
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("managed_benchmark",Path(__file__).with_name("benchmark_openvino.py"))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        identities = {device:helper.device_properties(core,device,[]) for device in available}
        emit({"event":"result","devices":available,"version":ov.__version__,"identities":identities})
        return
    device = request["device"]
    if device not in available:
        raise ValueError("DEVICE_UNAVAILABLE")
    cache = request["cache"]
    os.makedirs(cache,exist_ok=True)
    if request["op"]=="benchmark":
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("managed_benchmark",Path(__file__).with_name("benchmark_openvino.py"))
        benchmark = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(benchmark)
        benchmark.run(core,request,emit)
        return
    started = perf_counter()
    evidence = {"requested_device":device,"available_devices":available,"execution_devices":[],
                "operator_allocation":"unknown","verified_inference":False,"fallback":"unknown",
                "backend":"OpenVINO","backend_version":ov.__version__}
    if request["kind"]=="tensor":
        import numpy as np
        model = core.read_model(request["model"]+"/openvino_model.xml",request["model"]+"/openvino_model.bin")
        config={"CACHE_DIR":cache,"PERFORMANCE_HINT":"LATENCY","PERF_COUNT":True}
        if request.get("precision")=="f32" and device.startswith(("CPU","GPU")):config["INFERENCE_PRECISION_HINT"]=ov.Type.f32
        if device=="CPU" and request.get("threads"):config["INFERENCE_NUM_THREADS"]=request["threads"]
        compiled = core.compile_model(model,device,config)
        evidence["execution_devices"] = list(compiled.get_property("EXECUTION_DEVICES"))
        inputs = request["inputs"]
        if len(inputs)!=len(compiled.inputs):
            raise ValueError("INPUT_MISMATCH")
        prepared = {}
        for index,port in enumerate(compiled.inputs):
            array = np.asarray(inputs[index],dtype=port.get_element_type().to_dtype())
            if array.size>262144:
                raise ValueError("INPUT_TOO_LARGE")
            prepared[index] = array
        emit({"event":"loaded","load_ms":round((perf_counter()-started)*1000,3)})
        inference = compiled.create_infer_request()
        tick = perf_counter()
        outputs = inference.infer(prepared)
        latency = (perf_counter()-tick)*1000
        results = []
        for value in outputs.values():
            if value.size>262144:
                raise ValueError("OUTPUT_TOO_LARGE")
            results.append(value.tolist())
        profile = inference.get_profiling_info()
        evidence["operator_allocation"] = [{"node":item.node_type,"execution_type":item.exec_type,
                                             "status":str(item.status)} for item in profile[:512]]
        devices = evidence["execution_devices"]
        same = bool(devices) and all(item==device or item.startswith(device+".") for item in devices)
        evidence["fallback"] = "none-reported" if same else "reported-other-device"
        evidence["verified_inference"] = same
        emit({"event":"result","outputs":results,"latency_ms":round(latency,3),"evidence":evidence})
        del inference,compiled,model
    else:
        import openvino_genai as genai
        settings = {"CACHE_DIR":cache}
        if device=="CPU" and request.get("threads"):settings["INFERENCE_NUM_THREADS"]=request["threads"]
        if device=="NPU":
            settings.update(MAX_PROMPT_LEN=1024,MIN_RESPONSE_LEN=128)
        pipeline = genai.LLMPipeline(request["model"],device,settings)
        tokenizer = pipeline.get_tokenizer()
        prompt = tokenizer.apply_chat_template(request["messages"],add_generation_prompt=True)
        tokens = tokenizer.encode(prompt).input_ids.get_size()
        if tokens>1024:
            raise ValueError("CONTEXT_LIMIT")
        emit({"event":"loaded","load_ms":round((perf_counter()-started)*1000,3),"input_tokens":tokens})
        characters = 0
        def stream(text):
            nonlocal characters
            characters += len(text)
            if characters>128000:
                raise ValueError("OUTPUT_TOO_LARGE")
            emit({"event":"token","text":text})
            return False
        tick = perf_counter()
        pipeline.generate(prompt,max_new_tokens=request["max_tokens"],do_sample=False,
                          apply_chat_template=False,streamer=stream)
        # GenAI 2025.4 has no public per-subgraph execution-device query here.
        # Keep actual placement unknown even when the requested plugin succeeds.
        evidence["verification_limit"] = "GenAI pipeline does not expose per-subgraph placement through this adapter."
        emit({"event":"result","latency_ms":round((perf_counter()-tick)*1000,3),"evidence":evidence})
        del pipeline
    del core


if __name__=="__main__":
    try:
        main()
    except Exception as error:
        # Model/plugin exceptions may contain the user's inputs or local paths.
        known = {"DEVICE_UNAVAILABLE","INPUT_MISMATCH","INPUT_TOO_LARGE","OUTPUT_TOO_LARGE","CONTEXT_LIMIT","OUTPUT_LENGTH_MISMATCH"}
        code = error.args[0] if isinstance(error,ValueError) and error.args and isinstance(error.args[0],str) and error.args[0] in known else "OPENVINO_REQUEST_FAILED"
        emit({"event":"error","code":code})
        sys.exit(1)

"""A single loaded-model OpenVINO benchmark session inside the managed runner."""
import ctypes as ct
from hashlib import sha256
import math
import os
from time import perf_counter


def finite(value):
    value = float(value)
    return value if math.isfinite(value) and value>=0 else None


def process_peak_ram():
    if os.name!="nt":
        return None
    class Counters(ct.Structure):
        _fields_ = [("cb",ct.c_uint32),("faults",ct.c_uint32)]+[(name,ct.c_size_t) for name in
                    ("peak","working","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile")]
    counters = Counters(cb=ct.sizeof(Counters))
    library = ct.WinDLL("psapi.dll")
    library.GetProcessMemoryInfo.argtypes = [ct.c_void_p,ct.c_void_p,ct.c_uint32]
    return counters.peak if library.GetProcessMemoryInfo(ct.c_void_p(-1),ct.byref(counters),ct.sizeof(counters)) else None


def device_properties(core, device, windows):
    supported = {str(item) for item in core.get_property(device,"SUPPORTED_PROPERTIES")}
    values = {}
    for key in ("FULL_DEVICE_NAME","DEVICE_UUID","DEVICE_LUID","DRIVER_VERSION","DEVICE_ARCHITECTURE"):
        if key in supported:
            try:
                values[key] = str(core.get_property(device,key))
            except RuntimeError:
                values[key] = None
    mapping = {"state":"unknown","windows_id":None,"driver":None,"method":None}
    luid = values.get("DEVICE_LUID")
    if luid and len(luid)==16:
        try:
            raw = bytes.fromhex(luid)
            identity = f"{int.from_bytes(raw[4:],'little'):08x}_{int.from_bytes(raw[:4],'little'):08x}"
            matches = [item for item in windows if item.get("kind")=="gpu" and item["id"]==identity]
            if len(matches)==1:
                mapping = {"state":"verified","windows_id":identity,"driver":matches[0]["driver"]["value"],
                           "method":"OpenVINO DEVICE_LUID equals DXGI LUID"}
        except ValueError:
            pass
    return {"properties":values,"mapping":mapping}


def run(core, request, emit):
    import numpy as np
    import openvino as ov
    device = request["device"]
    params = request["parameters"]
    identity = device_properties(core,device,request.get("windows_devices",[]))
    emit({"event":"environment",**identity,"backend_version":ov.__version__})
    evidence = {"requested_device":device,"available_devices":list(core.available_devices),"execution_devices":[],
                "operator_allocation":"unknown","verified_inference":False,"fallback":"unknown",
                "verification_limit":None,"identity":identity}
    load_start = perf_counter()
    if request["kind"]=="tensor":
        model = core.read_model(request["model"]+"/openvino_model.xml",request["model"]+"/openvino_model.bin")
        read_ms = (perf_counter()-load_start)*1000
        compile_start = perf_counter()
        config = {"CACHE_DIR":request["cache"],"PERFORMANCE_HINT":"LATENCY","PERF_COUNT":True}
        if device.startswith(("CPU","GPU")):
            config["INFERENCE_PRECISION_HINT"] = ov.Type.f32
        compiled = core.compile_model(model,device,config)
        compile_ms = (perf_counter()-compile_start)*1000
        inference = compiled.create_infer_request()
        evidence["execution_devices"] = list(compiled.get_property("EXECUTION_DEVICES"))
        execution = evidence["execution_devices"]
        same = bool(execution) and all(item==device or item.startswith(device+".") for item in execution)
        evidence.update(verified_inference=same,fallback="none-reported" if same else "reported-other-device")
        preparation = {"read_model_ms":read_ms,"compile_ms":compile_ms,"pipeline_load_ms":None,
                       "requested_precision":"f32" if device.startswith(("CPU","GPU")) else "backend-default",
                       "cold_scope":"fresh-process-and-empty-openvino-cache","os_file_cache":"uncontrolled"}
        def prepare(workload):
            if len(workload["inputs"])!=len(compiled.inputs):
                raise ValueError("INPUT_MISMATCH")
            arrays = {index:np.asarray(workload["inputs"][index],dtype=port.get_element_type().to_dtype())
                      for index,port in enumerate(compiled.inputs)}
            if any(value.size>262144 for value in arrays.values()):
                raise ValueError("INPUT_TOO_LARGE")
            return arrays
        def execute(arrays,workload):
            start = perf_counter()
            outputs = inference.infer(arrays)
            latency = (perf_counter()-start)*1000
            serialize_start = perf_counter()
            values = list(outputs.values())
            expected = workload.get("expected")
            correct = None
            if expected is not None:
                correct = len(expected)==len(values) and all(
                    np.asarray(reference).shape==value.shape and
                    np.allclose(value,np.asarray(reference),rtol=1e-4,atol=1e-4,equal_nan=False)
                    for value,reference in zip(values,expected))
            result = {"latency_ms":latency,"output_correct":bool(correct) if correct is not None else None,
                      "output_fingerprints":[{"sha256":sha256(value.tobytes()).hexdigest(),"shape":list(value.shape),
                                              "dtype":str(value.dtype)} for value in values],
                      "input_tokens":None,"output_tokens":None,"ttft_ms":None,"decode_tokens_per_s":None,
                      "prefill_tokens_per_s":None}
            result["result_processing_ms"] = (perf_counter()-serialize_start)*1000
            return result
    else:
        import openvino_genai as genai
        config = {"CACHE_DIR":request["cache"]}
        if device.startswith("NPU"):
            config.update(MAX_PROMPT_LEN=1024,MIN_RESPONSE_LEN=128)
        pipeline = genai.LLMPipeline(request["model"],device,config)
        tokenizer = pipeline.get_tokenizer()
        preparation = {"read_model_ms":None,"compile_ms":None,"pipeline_load_ms":(perf_counter()-load_start)*1000,
                       "requested_precision":"backend-default","cold_scope":"fresh-process-and-empty-openvino-cache",
                       "os_file_cache":"uncontrolled"}
        evidence["verification_limit"] = "GenAI does not expose per-subgraph placement through this adapter."
        def prepare(workload):
            text = tokenizer.apply_chat_template([{"role":"user","content":workload["prompt"]}],add_generation_prompt=True)
            if tokenizer.encode(text).input_ids.get_size()>1024:
                raise ValueError("CONTEXT_LIMIT")
            return text
        def execute(text,workload):
            first = None
            start = perf_counter()
            def stream(fragment):
                nonlocal first
                if first is None and fragment:
                    first = (perf_counter()-start)*1000
                return False
            outputs = pipeline.generate([text],max_new_tokens=params["max_tokens"],do_sample=False,ignore_eos=True,
                                        apply_chat_template=False,streamer=stream)
            latency = (perf_counter()-start)*1000
            metrics = outputs.perf_metrics
            generated = metrics.get_num_generated_tokens()
            tpot = finite(metrics.get_tpot().mean)
            serialize_start = perf_counter()
            result = {"latency_ms":latency,"input_tokens":metrics.get_num_input_tokens(),"output_tokens":generated,
                      "ttft_ms":finite(metrics.get_ttft().mean),"first_text_callback_ms":first,
                      "decode_tokens_per_s":1000/tpot if tpot and generated>1 else None,
                      "reported_throughput":finite(metrics.get_throughput().mean),"prefill_tokens_per_s":None,
                      "output_correct":None,"nonempty_generation":any(bool(text.strip()) for text in outputs.texts),
                      "raw_token_infer_ms":[finite(value) for value in metrics.raw_metrics.token_infer_durations],
                      "token_count_source":"OpenVINO GenAI PerfMetrics","decode_rate_source":"1000 / reported TPOT ms",
                      "prefill_limit":"API does not isolate a reliable prefill throughput here."}
            result["result_processing_ms"] = (perf_counter()-serialize_start)*1000
            return result
    emit({"event":"preparation",**preparation})
    first_session = True
    for workload in request["workloads"]:
        start = perf_counter()
        inputs = prepare(workload)
        prepare_ms = (perf_counter()-start)*1000
        for phase,count in (("first",1),("warmup",params["warmup"]),("measured",params["iterations"])):
            for index in range(count):
                sample = execute(inputs,workload)
                sample.update(event="measurement",workload=workload["id"],phase=phase,index=index,
                              session_cold=first_session,input_prepare_ms=prepare_ms if phase=="first" else 0,
                              peak_ram_bytes=process_peak_ram())
                first_session = False
                emit(sample)
    if request["kind"]=="tensor":
        evidence["operator_allocation"] = [{"node":item.node_type,"execution_type":item.exec_type,"status":str(item.status)}
                                             for item in inference.get_profiling_info()[:512]]
    emit({"event":"result","preparation":preparation,"evidence":evidence,"peak_ram_bytes":process_peak_ram()})

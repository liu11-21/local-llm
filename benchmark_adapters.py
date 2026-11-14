"""Controlled benchmark sessions, sharing the application's engine adapters."""
from contextlib import ExitStack
import ctypes as ct
from dataclasses import asdict
from hashlib import sha256
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic, perf_counter

from engine import LocalEngine
from llama_app_engine import engine_for
from hardware import detect_hardware
from load_plan import allocate, block_count, engine_devices, engine_environment
from openvino_adapter import memory_limit


class Budget:
    def __init__(self, stop, seconds):
        self.stop, self.deadline = stop,monotonic()+seconds

    def is_set(self):
        return self.stop.is_set() or monotonic()>=self.deadline

    def wait(self, seconds):
        return self.stop.wait(max(0,min(seconds,self.deadline-monotonic()))) or self.is_set()

    def check(self):
        if self.stop.is_set():
            raise InterruptedError("Benchmark 已取消。")
        if monotonic()>=self.deadline:
            raise TimeoutError("Benchmark 已達時間上限。")

    def remaining(self):
        self.check()
        return max(.01,self.deadline-monotonic())


class OpenVINOBenchmark:
    def __init__(self, adapter):
        self.adapter = adapter

    def run(self, model, device, params, workloads, windows, budget, receive):
        directory, metadata = self.adapter.validate_model(model)
        if device.startswith("NPU") and metadata["kind"]=="text" and not metadata.get("npu_candidate"):
            raise ValueError("NPU_INCOMPATIBLE")
        # A session gets its own empty compilation cache, never the user's chat cache.
        with TemporaryDirectory(prefix="benchmark-",dir=self.adapter.root) as cache:
            result = self.adapter.execute({"op":"benchmark","model":str(directory),"kind":metadata["kind"],
                "device":device,"cache":cache,"parameters":params,"workloads":workloads,"windows_devices":windows},
                budget,receive,timeout=budget.remaining(),memory=params["memory_mib"]*1024**2)
        budget.check()
        return result


def native_peak(process):
    if os.name!="nt":
        return None
    class Counters(ct.Structure):
        _fields_ = [("cb",ct.c_uint32),("faults",ct.c_uint32)]+[(name,ct.c_size_t) for name in
                    ("peak","working","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile")]
    counters = Counters(cb=ct.sizeof(Counters))
    api = ct.WinDLL("psapi.dll")
    api.GetProcessMemoryInfo.argtypes = [ct.c_void_p,ct.c_void_p,ct.c_uint32]
    return counters.peak if api.GetProcessMemoryInfo(int(process._handle),ct.byref(counters),ct.sizeof(counters)) else None


class LlamaBenchmark:
    def __init__(self, executable, model):
        self.executable,self.model = Path(executable),Path(model)

    def run(self, model, device, params, workloads, windows, budget, receive):
        version = subprocess.run([str(self.executable),*( ["version"] if self.executable.name.lower() in ("llama.exe","llama") else ["--version"]) ],capture_output=True,timeout=min(8,budget.remaining()),
            env=engine_environment(),creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if version.returncode:
            raise ValueError("PROVIDER_MISSING")
        version_text = (version.stdout+b"\n"+version.stderr).decode("utf-8",errors="replace").strip().splitlines()
        backend_version = version_text[0][:160] if version_text else None
        devices = engine_devices(self.executable) if device!="CPU" else []
        selected = [item for item in devices if item[0]==device]
        if device!="CPU" and not selected:
            raise ValueError("DEVICE_UNAVAILABLE")
        plan = allocate(self.model.stat().st_size,block_count(self.model),selected,
                        detect_hardware(self.model.parent).ram_available)
        if device!="CPU" and (not plan.device or not plan.layers):
            raise MemoryError("INSUFFICIENT_VRAM")
        if plan.ram>params["memory_mib"]*1024**2:
            raise MemoryError("INSUFFICIENT_RAM")
        engine = engine_for(self.executable)
        evidence = {"requested_device":device,"available_devices":["CPU",*[item[0] for item in devices]],
                    "execution_devices":[],"verified_inference":False,"operator_allocation":"unknown",
                    "fallback":"unknown","verification_limit":"Configured layers are not operator placement evidence.",
                    "configured_plan":asdict(plan)}
        receive({"event":"environment","backend_version":backend_version,"executable_sha256":sha256(self.executable.read_bytes()).hexdigest(),
                 "driver":None,"mapping":{"state":"unknown"}})
        try:
            with ExitStack() as guards:
                start = perf_counter()
                engine.start(self.executable,self.model,budget,plan,context=params["context"],
                    on_process=lambda process:guards.enter_context(memory_limit(process,params["memory_mib"]*1024**2)))
                preparation = {"pipeline_load_ms":(perf_counter()-start)*1000,"compile_ms":None,"read_model_ms":None,
                               "cold_scope":"fresh-server-process-cache-prompt-disabled","os_file_cache":"uncontrolled",
                               "requested_precision":"GGUF-native"}
                receive({"event":"preparation",**preparation})
                first_session = True
                for workload in workloads:
                    budget.check()
                    messages = [{"role":"user","content":workload["prompt"]}]
                    start = perf_counter()
                    inputs = engine.prompt_tokens(messages)
                    prepare_ms = (perf_counter()-start)*1000
                    if inputs+params["max_tokens"]>params["context"]:
                        raise ValueError("CONTEXT_LIMIT")
                    for phase,count in (("first",1),("warmup",params["warmup"]),("measured",params["iterations"])):
                        for index in range(count):
                            budget.check()
                            start,first,usage,timings = perf_counter(),None,{},{}
                            for event in engine.completion_events(messages,max_tokens=params["max_tokens"],temperature=0,
                                                                  cancel=budget,benchmark=True):
                                budget.check()
                                usage = event.get("usage") or usage
                                timings = event.get("timings") or timings
                                if first is None and any(choice.get("delta",{}).get("content") for choice in event.get("choices",[])):
                                    first = (perf_counter()-start)*1000
                            budget.check()
                            if usage.get("completion_tokens") is not None and usage["completion_tokens"]!=params["max_tokens"]:
                                raise ValueError("OUTPUT_LENGTH_MISMATCH")
                            receive({"event":"measurement","workload":workload["id"],"phase":phase,"index":index,
                                     "session_cold":first_session,"latency_ms":(perf_counter()-start)*1000,
                                     "input_prepare_ms":prepare_ms if phase=="first" else 0,"result_processing_ms":None,
                                     "input_tokens":usage.get("prompt_tokens"),"output_tokens":usage.get("completion_tokens"),
                                     "token_count_source":"llama.cpp usage" if usage else "unavailable",
                                     "ttft_ms":None,"first_text_callback_ms":first,
                                     "prefill_tokens_per_s":timings.get("prompt_per_second"),
                                     "decode_tokens_per_s":timings.get("predicted_per_second"),
                                     "raw_timings":timings,"output_correct":None,"peak_ram_bytes":native_peak(engine.process)})
                            first_session = False
                # Stop before closing the Job Object, including on success.
                engine.stop()
                return {"preparation":preparation,"evidence":evidence}
        finally:
            engine.stop()

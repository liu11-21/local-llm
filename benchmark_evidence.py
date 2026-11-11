"""Read-only validity of existing benchmark evidence, never a benchmark trigger."""
from datetime import datetime
from time import time

from benchmark_core import fingerprint

AGE_ADVISORY_DAYS = 30
INFERENCE_PARAMETERS = ("context","max_tokens","memory_mib","batch","temperature","do_sample","ignore_eos")


def hardware_identity(environment, engine, device):
    """A backend-configured identity is distinct from verified physical placement."""
    native = environment.get("environment",{})
    mapping = native.get("mapping",{})
    if device=="CPU":
        cpu = environment.get("cpu") or native.get("properties",{}).get("FULL_DEVICE_NAME")
        return {"kind":"cpu","cpu":cpu,"machine":environment.get("machine")} if cpu else None
    if mapping.get("state")=="verified" and mapping.get("windows_id"):
        return {"kind":"physical","id":mapping["windows_id"]}
    devices = environment.get("hardware",{}).get("devices",[])
    inventory = [{"id":item.get("id"),"vendor":item.get("vendor"),"name":item.get("name"),
                  "driver":item.get("driver",{}).get("value")} for item in devices if item.get("kind")=="gpu"]
    if engine=="llama.cpp" and device.startswith(("Vulkan","CUDA")) and len(inventory)==1 and all(item["id"] for item in inventory):
        return {"kind":"backend-configured","backend":engine,"device":device,
                "inventory":sorted(inventory,key=lambda item:item["id"])}
    return None


def describe(session, run):
    config,environment = session["config"],run["environment"]
    native = environment.get("environment",{})
    parameters={"batch":1,"temperature":0,"do_sample":False,"ignore_eos":True,**config.get("parameters",{})}
    return {"model":session["model"],"model_hashes":config.get("model_hashes"),
            "format":config.get("format") or ("OpenVINO IR" if session["engine"]=="openvino" else "GGUF"),
            "quantization":config.get("quantization"),"parameters":parameters,
            "workloads":config.get("workloads",[]),"engine":session["engine"],
            "backend_version":native.get("backend_version"),"executable_sha256":native.get("executable_sha256"),
            "device":run["device"],"device_identity":hardware_identity(environment,session["engine"],run["device"]),
            "driver":native.get("mapping",{}).get("driver"),
            "precision":environment.get("preparation",{}).get("requested_precision"),
            "mapping":native.get("mapping",{}),"hardware":environment.get("hardware")}


def evaluate(session, run, current, usage, *, now=None, advisory_days=AGE_ADVISORY_DAYS):
    """Evaluate one run for one explicitly identified workload and inference recipe.

    current describes live identity; usage describes intended workload, not an arbitrary
    prompt treated as a benchmark. Unknowns do not become measurements or zero scores.
    """
    now = time() if now is None else now
    previous = describe(session,run)
    invalid,stale,missing,limits = [],[],[],[]
    for key in ("model","model_hashes","format","quantization","engine","backend_version","device","device_identity"):
        before,after = previous.get(key),current.get(key)
        if before is None or after is None:
            missing.append(key)
        elif before!=after:
            invalid.append(key)
    if previous["engine"]=="llama.cpp":
        if not previous["executable_sha256"] or not current.get("executable_sha256"):
            missing.append("executable_sha256")
        elif previous["executable_sha256"]!=current["executable_sha256"]:
            invalid.append("executable_sha256")
    if run["device"]!="CPU":
        identity = previous["device_identity"] or {}
        if identity.get("kind")=="physical":
            if not previous["driver"] or not current.get("driver"):
                missing.append("driver")
            elif previous["driver"]!=current["driver"]:
                stale.append("driver")
        elif identity.get("kind")=="backend-configured":
            limits.append("只有 Backend 裝置與 GPU 清單身分，尚未確認 Windows 實體裝置映射。")
        else:
            missing.append("device_mapping")
    try:
        age_days = (now-datetime.fromisoformat(session["created"]).timestamp())/86400
        if age_days<0:
            missing.append("timestamp_in_future")
        elif age_days>advisory_days:
            stale.append("age-advisory")
    except (ValueError,TypeError,KeyError):
        age_days = None
        missing.append("timestamp")
    complete = session["state"]=="completed" and run["state"]=="completed"
    if not complete:
        limits.append("Session 或 Run 未完整完成。")
    workload = usage.get("workload")
    old_workload = next((item for item in previous["workloads"] if item.get("id")==workload),None)
    workload_matches = bool(old_workload and usage.get("workload_sha256")==old_workload.get("sha256"))
    differences = []
    if not workload_matches:
        differences.append("workload")
    for key in INFERENCE_PARAMETERS:
        if key not in usage.get("parameters",{}):
            missing.append("usage."+key)
        elif previous["parameters"].get(key)!=usage["parameters"][key]:
            differences.append("parameters."+key)
    if not previous["precision"] or not current.get("precision"):
        missing.append("precision")
    elif previous["precision"]!=current["precision"]:
        differences.append("precision")
    samples = [item for item in run.get("measurements",[]) if item.get("workload")==workload and item.get("phase")=="measured"]
    iterations = previous["parameters"].get("iterations")
    valid_samples = bool(samples and type(iterations) is int and len(samples)==iterations and
        sum(item.get("workload")==workload and item.get("phase")=="first" for item in run.get("measurements",[]))==1 and
        sum(item.get("workload")==workload and item.get("phase")=="warmup" for item in run.get("measurements",[]))==previous["parameters"].get("warmup",0))
    if not valid_samples:
        limits.append("指定工作量缺少完整正式量測。")
    evidence = run.get("evidence") or {}
    output_correct = True if samples and all(item.get("output_correct") is True for item in samples) else (
        False if any(item.get("output_correct") is False for item in samples) else None)
    placement = evidence.get("verified_inference") is True
    execution = evidence.get("execution_devices") or []
    fallback = evidence.get("fallback","unknown")
    cpu_fallback = run["device"]!="CPU" and any(item=="CPU" for item in execution)
    if cpu_fallback or fallback=="reported-other-device":
        limits.append("實際回報其他裝置或 CPU Fallback，不能歸為所選設備的效能。")
    if not placement:
        limits.append("Backend 測試完成不等於已驗證執行裝置或完整算子分配。")
    full_allocation = evidence.get("operator_allocation_verified") is True
    if not full_allocation:
        limits.append("完整算子分配未驗證。")
    if output_correct is None:
        limits.append("未提供語意品質或參考輸出正確性判準。")
    elif output_correct is False:
        limits.append("參考輸出不符。")
    npu_unverified = run["device"].startswith("NPU") and not placement
    if npu_unverified:
        limits.append("NPU 尚無已驗證的實體推理證據。")
    freshness = "invalidated" if invalid else "stale" if stale else "unknown" if missing else "current"
    comparability = ("not_comparable" if invalid or differences or output_correct is False or cpu_fallback or fallback=="reported-other-device"
                     else "insufficient_evidence" if missing or not complete or not valid_samples or npu_unverified
                     else "equivalent" if placement and full_allocation else "partially_comparable")
    eligible = freshness=="current" and comparability in ("equivalent","partially_comparable") and complete and valid_samples
    summary = (run.get("summary") or {}).get(workload) if eligible else None
    return {"schema":1,"session":session["id"],"run":run["id"],"device":run["device"],
            "freshness":freshness,"comparability":comparability,"eligible_for_ranking":eligible,
            "changed":invalid,"stale_reasons":stale,"missing":sorted(set(missing)),"differences":differences,
            "limitations":limits,"age_days":age_days,"age_advisory_days":advisory_days,
            "benchmark_completed":complete,"output_correct":output_correct,"execution_device_verified":placement,
            "full_operator_allocation_verified":full_allocation,"backend_configured":True,"cpu_fallback":cpu_fallback,
            "mapping":previous["mapping"],"summary":summary,"precision":previous["precision"],
            "memory":{"peak_ram_bytes":max((sample.get("peak_ram_bytes") or 0 for sample in samples),default=0) or None,
                      "peak_vram_bytes":run["environment"].get("peak_vram_bytes"),"current":current.get("resources"),
                      "verified_minimum_requirement":False},
            "condition_key":fingerprint({"hashes":previous["model_hashes"],"engine":previous["engine"],
                "version":previous["backend_version"],"precision":previous["precision"],"workload":old_workload,
                "parameters":{key:previous["parameters"].get(key) for key in INFERENCE_PARAMETERS}})}

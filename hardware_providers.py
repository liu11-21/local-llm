"""Explicit, isolated optional backend discovery. Never downloads or compiles models."""
import importlib
import importlib.util


def probe():
    records = []
    for package, formats in (("openvino",["OpenVINO IR","ONNX"]),("onnxruntime",["ONNX"])):
        entry = {"id":package,"state":"missing","version":None,"devices":[],"providers":[],
                 "formats":formats,"quantization":[],"verified_inference":False,
                 "limitations":"列出裝置或 Provider 尚未驗證模型、算子分配或實際加速。"}
        try:
            if importlib.util.find_spec(package) is not None:
                module = importlib.import_module(package)
                entry["version"] = str(module.__version__)
                if package == "openvino":
                    core = module.Core()
                    entry["devices"] = list(core.available_devices)
                    entry["providers"] = ["OpenVINO"]
                else:
                    entry["providers"] = list(module.get_available_providers())
                entry["state"] = "reported"
        except Exception:
            entry["state"] = "initialization-failed"
        records.append(entry)
    return records

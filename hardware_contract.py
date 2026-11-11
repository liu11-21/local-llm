"""Bounded, evidence-bearing device data for local IPC and paired Runtime records."""
import math

from hardware_monitor import reading

METRICS = ("driver","driver_state","utilization","vram_total","vram_used","vram_available","shared_limit","shared_used")


def validate_hardware(data):
    def text(value, maximum=300):
        if not isinstance(value,str) or not 0 < len(value) <= maximum or any(ord(char)<32 for char in value):
            raise ValueError("硬體描述格式無效。")
        return value

    def metric(item, key):
        if not isinstance(item,dict):
            raise ValueError("硬體量測格式無效。")
        value = item.get("value")
        source, status = item.get("source"),item.get("status")
        if (source not in ("detected","reported","estimated","unknown")
                or status not in ("available","unknown","unsupported")
                or (value is None) != (source=="unknown") or (value is None) != (status!="available")):
            raise ValueError("硬體量測來源無效。")
        if value is not None:
            if key=="driver":
                text(value,80)
            elif key=="npu_present":
                if type(value) is not bool:
                    raise ValueError("NPU 狀態無效。")
            elif (type(value) not in (int,float) or not math.isfinite(value) or value<0
                  or value > (100 if key=="utilization" else 2**53-1)
                  or key!="utilization" and type(value) is not int):
                raise ValueError("硬體量測數值無效。")
        return {"value":value,"source":source,"status":status}

    if not isinstance(data,dict) or type(data.get("schema")) is not int or data["schema"]!=1:
        raise ValueError("硬體契約版本不相容。")
    for key in ("checked_at","inventory_at","provider_checked_at"):
        value = data.get(key)
        if value is not None and (type(value) is not int or not 0 <= value <= 2**53-1):
            raise ValueError("硬體取樣時間無效。")
    if data.get("state") not in ("available","unknown","unsupported"):
        raise ValueError("硬體清單狀態無效。")
    devices = data.get("devices")
    if not isinstance(devices,list) or len(devices)>32:
        raise ValueError("硬體裝置清單無效。")
    result = {key:data.get(key) for key in ("schema","state","checked_at","inventory_at","provider_checked_at")}
    result["devices"] = []
    for device in devices:
        if not isinstance(device,dict) or device.get("kind") not in ("gpu","npu","accelerator"):
            raise ValueError("硬體裝置類型無效。")
        entry = {key:text(device.get(key),500) for key in ("id","name","vendor")}
        entry.update(kind=device["kind"],verified_inference=device.get("verified_inference") is True)
        entry.update({key:metric(device.get(key,reading()),key) for key in METRICS})
        result["devices"].append(entry)
    result["npu_present"] = metric(data.get("npu_present",reading()),"npu_present")
    if data.get("provider_state") not in ("not-checked","checked","failed"):
        raise ValueError("Provider 查詢狀態無效。")
    providers = data.get("providers",[])
    if not isinstance(providers,list) or len(providers)>16:
        raise ValueError("Provider 清單無效。")
    result["provider_state"],result["providers"] = data["provider_state"],[]
    for provider in providers:
        entry = {key:text(provider.get(key),600) for key in ("id","state","limitations")}
        entry["version"] = text(provider["version"],80) if provider.get("version") else None
        for key in ("devices","providers","formats","quantization"):
            values = provider.get(key,[])
            if not isinstance(values,list) or len(values)>40:
                raise ValueError("Provider 能力格式無效。")
            entry[key] = [text(value) for value in values]
        entry["verified_inference"] = provider.get("verified_inference") is True
        result["providers"].append(entry)
    return result

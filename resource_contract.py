"""Memory evidence shared by monitoring, Runtime capabilities and recommendations."""
from time import time

MAX_AGE = 15
UNITS = {"cpu_threads":"count","gpus":"names","ram_total":"bytes","ram_available":"bytes",
         "vram_total":"bytes","vram_available":"bytes","active_jobs":"count"}


def reading(value=None, source="detected", status=None, *, unit="unknown", checked_at=None, evidence=None):
    source = source if value is not None else "unknown"
    return {"value":value,"unit":unit,"source":source,"checked_at":checked_at,
            "status":status or ("available" if value is not None else "unknown"),
            "evidence":evidence or source}


def fresh_measure(item, now=None):
    timestamp = item.get("checked_at")
    return (item.get("status")=="available" and type(timestamp) is int
            and 0 <= (time() if now is None else now)-timestamp <= MAX_AGE)


def gpu_memory(hardware, now=None):
    """Return only a single, identified discrete memory pool for legacy VRAM fields."""
    gpus = [device for device in (hardware or {}).get("devices",[]) if device["kind"]=="gpu"]
    if len(gpus)!=1 or gpus[0].get("memory_type")!="dedicated":
        return None,None
    device = gpus[0]
    available = device["vram_available"]
    if not fresh_measure(available,now):
        return None,None
    return device["vram_total"],available


def memory_explanation(hardware, now=None):
    gpus = [device for device in (hardware or {}).get("devices",[]) if device["kind"]=="gpu"]
    if not gpus:
        return "尚未取得可對應的 GPU 記憶體池。"
    if len(gpus)>1:
        return "多張 GPU 的記憶體分開計算，請先確認實際執行裝置。"
    if gpus[0].get("memory_type") == "unified":
        return "此 GPU 使用統一記憶體，專用顯存數字不足以判斷可執行性。共享上限與實際可分配容量分開計算。"
    if gpus[0].get("memory_type") != "dedicated":
        return "GPU 記憶體類型尚未確認，模型容量需由後端驗證。"
    return "GPU 記憶體取樣已過期或目前可分配容量未知。"

"""Versioned capability records shared by the desktop and the paired Host."""
from time import time

VERSION = 1
TYPES = {"local", "remote-host", "cloud-api", "colab-notebook", "unknown"}
RESOURCES = ("cpu_threads", "gpus", "ram_total", "ram_available", "vram_total", "vram_available", "active_jobs")
FEATURES = ("stream", "cancel", "load", "unload", "download")
EVIDENCE = {"detected", "reported", "estimated", "configured", "unknown"}
MAX_AGE = 60


def observed(value=None, source="detected"):
    return {"value": value, "source": source if value is not None else "unknown"}


def capability(id, label, kind, provider, *, version=None, connected=None, health="unknown", tasks=(), formats=(),
               engines=(), models=(), resources=None, features=None, network=None, destination=None, auth=None,
               cost="unknown", source="registry", error=None, checked_at=None):
    return validate({
        "schema": VERSION, "id": id, "label": label, "kind": kind, "provider": provider, "version": version,
        "connected": connected, "health": health, "tasks": list(tasks), "formats": list(formats),
        "engines": list(engines), "models": list(models), "network": network, "destination": destination,
        "auth": auth, "cost": cost, "source": source, "error": error,
        "checked_at": int(time()) if checked_at is None else checked_at,
        "resources": {key: (resources or {}).get(key, observed()) for key in RESOURCES},
        "features": {key: (features or {}).get(key) for key in FEATURES},
    })


def validate(data):
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != VERSION:
        raise ValueError("Runtime 能力契約版本不相容。")

    def string(value, maximum=300):
        return isinstance(value, str) and 0 < len(value) <= maximum and all(ord(char) >= 32 for char in value)

    keys = ("schema", "id", "label", "kind", "provider", "version", "connected", "health", "tasks", "formats",
            "engines", "models", "network", "destination", "auth", "cost", "source", "error", "checked_at")
    result = {key: data.get(key) for key in keys}
    for key in ("id", "label", "provider", "source"):
        if not string(result[key]):
            raise ValueError("Runtime 能力識別資料無效。")
    for key in ("version", "destination", "auth", "error"):
        if result[key] is not None and not string(result[key], 600):
            raise ValueError("Runtime 能力描述無效。")
    for key, values in {"kind": TYPES, "cost": {"unknown", "no-api-fee", "may-charge"},
                        "health": {"ready", "busy", "offline", "unhealthy", "unknown", "setup"}}.items():
        if not isinstance(result[key], str) or result[key] not in values:
            raise ValueError("Runtime 狀態資料無效。")
    for key in ("tasks", "formats", "engines", "models"):
        values = result[key]
        if not isinstance(values, list) or len(values) > 250 or not all(string(value) for value in values):
            raise ValueError("Runtime 模型或能力清單無效。")
    for key in ("connected", "network"):
        if result[key] is not None and type(result[key]) is not bool:
            raise ValueError("Runtime 連線狀態無效。")
    if type(result["checked_at"]) is not int or not 0 <= result["checked_at"] <= 2**53 - 1:
        raise ValueError("Runtime 能力查詢時間無效。")
    result["features"], result["resources"] = {}, {}
    features, resources = data.get("features", {}), data.get("resources", {})
    if not isinstance(features, dict) or not isinstance(resources, dict):
        raise ValueError("Runtime 資源格式無效。")
    for key in FEATURES:
        value = features.get(key)
        if value is not None and type(value) is not bool:
            raise ValueError("Runtime 功能格式無效。")
        result["features"][key] = value
    for key in RESOURCES:
        item = resources.get(key, observed())
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or item["source"] not in EVIDENCE:
            raise ValueError("Runtime 資源來源無效。")
        value = item.get("value")
        valid = (isinstance(value, list) and len(value) <= 32 and all(string(gpu) for gpu in value)
                 if key == "gpus" else type(value) is int and 0 <= value <= 2**53 - 1)
        if (value is None) != (item["source"] == "unknown") or (value is not None and not valid):
            raise ValueError("Runtime 資源數值無效。")
        result["resources"][key] = observed(value, item["source"])
    return result


def fresh(record, now=None):
    return 0 <= (time() if now is None else now) - record["checked_at"] <= MAX_AGE


def local_capability(info, health, active_jobs):
    hardware = info["hardware"]
    devices = info.get("devices", [])
    text, media = health["llama"]["state"], health["comfyui"]["state"]
    engines = (["llama.cpp"] if info["engine"] else []) + (["ComfyUI"] if info.get("comfy_installed") else [])
    return capability("local", "本機 CPU／GPU", "local", "Local LLM", connected=True, source="desktop",
                      health=("busy" if active_jobs else "unhealthy" if {text, media} & {"unhealthy", "failed"}
                              else "ready" if engines else "setup"),
                      tasks=("chat", "agent", "team", "image", "video", "music"), formats=("GGUF", "safetensors"),
                      engines=engines, models=info["models"][:250], network=False, destination="this-device",
                      cost="no-api-fee", resources={
                          "cpu_threads": observed(hardware["cpu_threads"]), "ram_total": observed(hardware["ram_total"]),
                          "ram_available": observed(hardware["ram_available"]), "active_jobs": observed(active_jobs),
                          "gpus": observed([name for name, _, _ in devices][:32] or None),
                      }, features={"stream": bool(info["engine"]), "cancel": True, "load": bool(info["engine"]),
                                   "unload": bool(info["engine"]), "download": True},
                      error="引擎目前無法回應。" if {text, media} & {"unhealthy", "failed"} else None)


def external_capability(provider):
    return capability(provider["id"], provider["label"], "cloud-api" if provider["kind"] == "cloud" else "unknown",
                      "OpenAI-compatible", connected=provider["connected"],
                      health="ready" if provider["connected"] else "offline", tasks=("chat",), models=provider["models"],
                      features={"stream": None, "cancel": None, "load": False, "unload": False, "download": False},
                      network=True, destination=f'{provider["host"]}:{provider["port"]}', auth="api-key",
                      source="provider-model-list", checked_at=provider.get("checked_at", 0),
                      error=None if provider["connected"] else "端點未連線。")


def colab_capability(available):
    return capability("colab", "Colab Enterprise", "colab-notebook", "Google Cloud", connected=available,
                      health="ready" if available else "setup", tasks=("notebook",), network=True,
                      destination="configured-google-cloud-project", auth="google-oauth", cost="may-charge",
                      features={"stream": False, "load": False, "unload": False, "download": False},
                      source="colab-enterprise-adapter")

"""Discovery and capability records used by the desktop application."""
import re
from datetime import datetime, timezone
from pathlib import Path

from comfy_runtime import PROFILES, VERSION as COMFY_VERSION
from hardware import estimate_ram
from media import DEFAULT_WORKFLOWS, workflow_manifest

QUANT = re.compile(r"[-_.](IQ[1-9][A-Z0-9_]*|Q[1-9][A-Z0-9_]*|F16|F32|BF16)$", re.I)
SIZE = re.compile(r"(?<![0-9.])(\d+(?:\.\d+)?[BM])(?=$|[-_ ])", re.I)


def model_label(name):
    if not name.lower().endswith(".gguf"):
        return name
    stem = name[:-5]
    match = QUANT.search(stem)
    return (stem[:match.start()] if match else stem).replace("_", " ").replace("-Instruct", " Instruct")


def model_identity(path):
    stat = path.stat()
    return [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev]


def installed_models(directory, names, sources):
    result = []
    for name in names:
        path = directory / name
        try:
            if path.resolve().parent != directory.resolve():
                continue
            identity = model_identity(path)
        except OSError:
            continue
        record = sources.get(name.casefold(), {})
        if record.get("identity") != identity:
            record = {}
        size = identity[0]
        repo = record.get("repository")
        quant, parameters = QUANT.search(Path(name).stem), SIZE.search(model_label(name))
        result.append({"id": name, "label": model_label(name), "format": "GGUF", "publisher": repo.split("/")[0] if repo else None,
                       "version": record.get("version"), "parameters": parameters[1].upper() if parameters else None,
                       "quantization": quant[1].upper() if quant else None, "bytes": size, "ram": estimate_ram(size),
                       "tasks": ["chat", "agent", "team"], "engine": "llama", "runtime": "local",
                       "source": record.get("source"), "repository": repo, "sha256": record.get("sha256"),
                       "verification": record.get("verification", "unknown"), "downloaded": record.get("downloaded"),
                       "source_verified": record.get("verification") == "verified",
                       "installed": True, "license": record.get("license")})
    return result


def workspace_registry(info, models, engine_version, sources):
    engines = [
        {"id":"llama", "label":"llama.cpp", "version":engine_version, "formats":["GGUF"], "tasks":["chat","agent","team"],
         "hardware":["CPU","Vulkan"], "installed":info["engine"], "running":bool(info["active"]),
         "actions":["engine-install","engine-start","engine-stop"], "cancel":True},
        {"id":"comfyui", "label":"ComfyUI", "version":COMFY_VERSION, "formats":["safetensors"],
         "tasks":list(DEFAULT_WORKFLOWS), "hardware":list(PROFILES), "installed":info["comfy_installed"], "running":info["comfy_running"],
         "actions":["comfy-install","comfy-start","comfy-stop"], "cancel":True},
    ]
    runtimes = [{"id":"local", "label":"本機 CPU／GPU", "kind":"local", "ready":True, "models":info["models"],
                 "tasks":["chat","agent","team",*DEFAULT_WORKFLOWS]}]
    runtimes.extend({"id":p["id"], "label":p["label"], "kind":p["kind"], "ready":p["connected"],
                     "models":p["models"], "tasks":["chat","team"]} for p in info["providers"])
    runtimes.append({"id":"colab", "label":"Colab Enterprise", "kind":"notebook", "ready":info["colab_ready"],
                     "models":[], "tasks":["notebook"]})
    return {"models":installed_models(models, info["models"], sources), "engines":engines,
            "runtimes":runtimes, "workflows":workflow_manifest()}


def recent_works(directory, limit=24):
    kinds = {".png":"image", ".webm":"video", ".flac":"music"}
    records = []
    for path in directory.glob("*"):
        if not re.fullmatch(r"[a-f0-9]{12}\.(png|webm|flac)", path.name) or path.is_symlink():
            continue
        try:
            stat = path.stat()
            if not path.is_file():
                continue
        except OSError:
            continue
        records.append({"name":path.name, "kind":kinds[path.suffix], "bytes":stat.st_size,
                        "created":datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()})
    return sorted(records, key=lambda record: record["created"], reverse=True)[:limit]

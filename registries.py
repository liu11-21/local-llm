"""Discovery and capability records used by the desktop application."""
import re
import struct
from datetime import datetime, timezone
from pathlib import Path

from comfy_runtime import PROFILES, VERSION as COMFY_VERSION
from hardware import estimate_ram
from media import DEFAULT_WORKFLOWS, workflow_manifest
from media_install import manifest as media_manifest

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
                     "models":p["models"], "tasks":["chat"] if p["kind"] == "paired" else ["chat","team"]}
                    for p in info["providers"])
    runtimes.append({"id":"colab", "label":"Colab Enterprise", "kind":"notebook", "ready":info["colab_ready"],
                     "models":[], "tasks":["notebook"]})
    return {"models":installed_models(models, info["models"], sources), "engines":engines,
            "runtimes":runtimes, "workflows":workflow_manifest(),
            "media_models":[media_manifest(kind) for kind in DEFAULT_WORKFLOWS]}


WORK_KINDS = {".png":"image", ".webm":"video", ".flac":"music"}


def work_file(directory, name):
    if not re.fullmatch(r"[a-f0-9]{12}\.(png|webm|flac)", name):
        raise ValueError("作品檔名無效。")
    path = directory / name
    if directory.resolve() != directory.absolute() or path.is_symlink() or path.resolve() != path.absolute() or not path.is_file():
        raise ValueError("找不到作品原始檔案，請確認檔案是否被移動。")
    return path


def webm_metadata(stream, file_size):
    def vint(identifier=False):
        first = stream.read(1)[0]
        width = 9 - first.bit_length()
        if width > (4 if identifier else 8):
            raise ValueError("invalid EBML field")
        rest = stream.read(width - 1)
        if len(rest) != width - 1:
            raise ValueError("short EBML field")
        value = int.from_bytes(bytes([first]) + rest, "big")
        if identifier:
            return value
        value ^= 1 << (7 * width)
        return None if value == (1 << (7 * width)) - 1 else value

    def elements(end):
        for _ in range(256):
            if stream.tell() >= end:
                break
            tag, size = vint(True), vint()
            start = stream.tell()
            limit = end if size is None else start + size
            if limit > end:
                raise ValueError("EBML element exceeds its container")
            yield tag, limit, size
            stream.seek(limit)

    scale, duration = 1_000_000, None
    dimensions = {}
    try:
        for tag, segment, _ in elements(file_size):
            if tag != 0x18538067:  # Segment
                continue
            for tag, boundary, _ in elements(segment):
                if tag == 0x1549A966:  # Info
                    for key, _, size in elements(boundary):
                        if key == 0x2AD7B1 and size in range(1, 9):
                            scale = int.from_bytes(stream.read(size), "big")
                        elif key == 0x4489 and size in (4, 8):
                            duration = struct.unpack(">f" if size == 4 else ">d", stream.read(size))[0]
                if tag == 0x1654AE6B:  # Tracks
                    for key, track, _ in elements(boundary):
                        if key != 0xAE:
                            continue
                        for key, video, _ in elements(track):
                            if key != 0xE0:
                                continue
                            for key, _, size in elements(video):
                                if key in (0xB0, 0xBA) and size in range(1, 5):
                                    pixels = int.from_bytes(stream.read(size), "big")
                                    dimensions["width" if key == 0xB0 else "height"] = pixels
            break
    except (IndexError, OSError, ValueError, struct.error):
        return {}
    if duration and 0 < duration * scale < float("inf"):
        dimensions["duration"] = duration * scale / 1_000_000_000
    return dimensions


def media_metadata(path):
    """Read media metadata without decoding or loading the full file."""
    try:
        with path.open("rb") as stream:
            if path.suffix == ".webm":
                return webm_metadata(stream, path.stat().st_size)
            header = stream.read(42)
    except OSError:
        return {}
    if path.suffix == ".png" and len(header) >= 24 and header[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR":
        width, height = struct.unpack(">II", header[16:24])
        if width and height:
            return {"width": width, "height": height}
    if path.suffix == ".flac" and len(header) == 42 and header[:4] == b"fLaC" and header[4] & 127 == 0 and header[5:8] == b"\x00\x00\x22":
        packed = int.from_bytes(header[18:26], "big")
        sample_rate, samples = packed >> 44, packed & (2**36 - 1)
        if sample_rate and samples:
            return {"duration": samples / sample_rate}
    return {}


def recent_works(directory, limit=24):
    records = []
    for path in directory.glob("*"):
        try:
            stat = work_file(directory, path.name).stat()
        except (OSError, ValueError):
            continue
        records.append({"name":path.name, "kind":WORK_KINDS[path.suffix], "bytes":stat.st_size,
                        "created":datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()})
    return sorted(records, key=lambda record: (record["created"], record["name"]), reverse=True)[:limit]

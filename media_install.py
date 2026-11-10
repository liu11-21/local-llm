"""Pinned, data-only ComfyUI dependencies for the built-in workflows."""
from dataclasses import asdict, dataclass
import hashlib
import json
import shutil
from urllib.parse import quote

from comfy_runtime import PROFILES, VERSION, install_directory, installed
from download_recovery import BLOCK, Checkpoints, owned
from downloads import download_file
from media import DEFAULT_WORKFLOWS, IMAGE_MODEL, MODELS, MUSIC_MODEL, VIDEO_MODEL, VIDEO_TEXT, VIDEO_VAE, WORKFLOWS, workflow


@dataclass(frozen=True)
class Weight:
    filename: str
    directory: str
    remote_path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Model:
    version: str
    publisher: str
    repo: str
    revision: str
    license: str
    weights: tuple[Weight, ...]


MODELS_FOR_INSTALL = {
    "image": Model("1.5", "Runway / Comfy-Org archive", "Comfy-Org/stable-diffusion-v1-5-archive",
                   "9cfd069101959ca3828bf9c04a4419870832b74f", "creativeml-openrail-m", (
                       Weight(IMAGE_MODEL, "checkpoints", IMAGE_MODEL, 2132696762,
                              "e9476a13728cd75d8279f6ec8bad753a66a1957ca375a1464dc63b37db6e3916"),)),
    "video": Model("2.1 T2V 1.3B", "Wan-AI / Comfy-Org", "Comfy-Org/Wan-2.1",
                   "123acf1cc74bccbb9bfff8ac1ee72edc08c2341d", "apache-2.0", (
                       Weight(VIDEO_MODEL, "diffusion_models", f"split_files/diffusion_models/{VIDEO_MODEL}", 2838303560,
                              "be531024cd9018cb5b48c40cfbb6a6191645b1c792eb8bf4f8c1c6e10f924dc5"),
                       Weight(VIDEO_TEXT, "text_encoders", f"split_files/text_encoders/{VIDEO_TEXT}", 6735906897,
                              "c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68"),
                       Weight(VIDEO_VAE, "vae", f"split_files/vae/{VIDEO_VAE}", 253815318,
                              "2fc39d31359a4b0a64f55876d8ff7fa8d780956ae2cb13463b0223e15148976b"),)),
    "music": Model("v1 3.5B", "ACE-Step / Comfy-Org", "Comfy-Org/ACE-Step",
                   "ea4f3d349e84d5c098cc8e8b904a30fde59fc99a", "apache-2.0", (
                       Weight(MUSIC_MODEL, "checkpoints", f"all_in_one/{MUSIC_MODEL}", 7699743341,
                              "f07cad74c4adce52ca14ca1bdf74cf3c14cbafb0823b95eca4459467fa369f40"),)),
}


def required_nodes(kind, workflow_id=None):
    return sorted({node["class_type"] for node in workflow(kind, "probe", seed=0, workflow_id=workflow_id).values()})


def manifest(kind):
    model = MODELS_FOR_INSTALL[kind]
    source = f"https://huggingface.co/{model.repo}"
    return {
        "id": DEFAULT_WORKFLOWS[kind], "kind": kind, "label": MODELS[kind][1], "publisher": model.publisher,
        "version": model.version, "format": "safetensors", "workflows": [key for key, item in WORKFLOWS.items() if item[0] == kind],
        "engine": "comfyui", "engine_version": VERSION, "platforms": ["windows-x64"], "nodes": required_nodes(kind),
        "source": source, "revision": model.revision, "license": model.license,
        "terms": f"{source}/tree/{model.revision}", "ram": None, "vram": None,
        "requirements": ["ComfyUI 內建節點"],
        "weights": [{**asdict(weight), "url": f"{source}/resolve/{model.revision}/{quote(weight.remote_path)}",
                     "path": f"ComfyUI/models/{weight.directory}/{weight.filename}"} for weight in model.weights],
    }


def install_plan(data, kind, profile):
    if kind not in MODELS_FOR_INSTALL or profile not in PROFILES:
        raise ValueError("請選擇有效的創作模型和 ComfyUI 便攜版。")
    data = data.resolve()
    bundle = install_directory(data / "comfyui", profile)
    cache = data / ".media-downloads" / PROFILES[profile][0]
    if not owned(bundle) or not owned(cache):
        raise ValueError("ComfyUI 安裝目錄不安全。")
    runtime = installed(bundle)
    model = manifest(kind)
    files = []
    needed = 0
    for weight in model["weights"]:
        path = bundle / weight["path"]
        if not owned(path):
            raise ValueError("模型權重或暫存目錄不安全。")
        status = "missing"
        if path.exists():
            status = "present" if path.is_file() and path.stat().st_size == weight["bytes"] else "conflict"
        remaining = weight["bytes"]
        if status == "missing":
            checkpoints = Checkpoints(cache, path)
            record = checkpoints.load()
            if (record and owned(checkpoints.staging) and checkpoints.staging.is_file()
                    and record["total"] == weight["bytes"] and record.get("url") == weight["url"]
                    and record.get("expected_sha") == weight["sha256"]
                    and checkpoints.staging.stat().st_size == record["total"]):
                remaining -= sum(min(BLOCK, record["total"] - int(index) * BLOCK) for index in record["blocks"])
            needed += remaining
        files.append({**weight, "status": status})
    free = shutil.disk_usage(bundle if runtime else data).free
    return {"model": model, "profile": profile, "target": f"{kind}:{PROFILES[profile][0]}", "installed": runtime, "files": files,
            "free": free, "needed": needed, "conflict": any(item["status"] == "conflict" for item in files)}


def check_safetensors(path):
    with path.open("rb") as stream:
        length = int.from_bytes(stream.read(8), "little")
        if not 2 <= length <= min(16 * 1024 ** 2, path.stat().st_size - 8):
            raise ValueError("無法辨識 Safetensors 標頭。")
        header = json.loads(stream.read(length))
    if not isinstance(header, dict) or not (header.keys() - {"__metadata__"}):
        raise ValueError("Safetensors 缺少張量資料。")


def install_weights(data, kind, profile, cancel, update):
    plan = install_plan(data, kind, profile)
    if not plan["installed"]:
        raise ValueError("請先安裝所選的 ComfyUI 便攜版。")
    if plan["conflict"]:
        raise ValueError("有同名檔案與固定版本不符。請確認並自行移開檔案後重試。")
    if plan["needed"] > plan["free"]:
        raise OSError("可用磁碟空間不足，請釋出空間後再試。")
    data = data.resolve()
    bundle = install_directory(data / "comfyui", profile)
    cache = data / ".media-downloads" / PROFILES[profile][0]
    total = sum(weight["bytes"] for weight in plan["files"])
    done = 0

    def check_cancel():
        if cancel.is_set():
            raise InterruptedError("已取消模型安裝。")

    for weight in plan["files"]:
        check_cancel()
        path = bundle / weight["path"]
        name = weight["filename"]
        size = weight["bytes"]
        if not owned(path):
            raise ValueError("模型權重目錄不安全。")
        if weight["status"] == "present":
            update(message=f"正在驗證既有權重 · {name}", received=done, total=total)
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 ** 2):
                    check_cancel()
                    digest.update(chunk)
            if digest.hexdigest() != weight["sha256"]:
                raise ValueError(f"既有權重 SHA-256 不符 · {name}。請確認並自行移開後再試。")
        else:
            def validate(staging):
                update(message=f"正在驗證 SHA-256 · {name}", received=done + size, total=total)
                check_safetensors(staging)

            def before_publish(_staging, _digest):
                if not owned(path):
                    raise ValueError("模型權重目錄不安全。")

            download_file(weight["url"], path, 4, cancel,
                          lambda received, _, count: update(message=f"下載中 · {name} · {count} 個執行緒",
                                                            received=done + received, total=total),
                          validate=validate, expected_size=size, expected_sha=weight["sha256"],
                          recovery=cache, before_publish=before_publish)
        done += size
        update(received=done, total=total)
    return {"message": "模型權重已通過 SHA-256 驗證。"}

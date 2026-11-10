"""Shared limits and allow-list for paired ComfyUI image generation."""
from hashlib import sha256
import os
import re
from time import monotonic

from download_recovery import exclusive, owned
from media import FORMATS, MODELS, workflow_options
from registries import work_file

IMAGE_WORKFLOWS = ("sd15", "sd15-preview")
REMOTE_IMAGE_LIMIT = 32 * 1024**2
CHUNK = 256 * 1024


def image_input(data):
    workflow, prompt = data.get("workflow"), data.get("prompt")
    if (set(data) - {"request","kind","workflow","prompt","options"} or workflow not in IMAGE_WORKFLOWS
            or not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000):
        raise ValueError("只允許內建 Stable Diffusion 1.5 流程及提示詞。")
    return {"kind":"image", "workflow":workflow, "prompt":prompt.strip(),
            "options":workflow_options("image",workflow,data.get("options"))}


def checksum(path, cancel):
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(CHUNK):
            if cancel.is_set():
                raise InterruptedError("作品驗證已取消。")
            digest.update(block)
    return digest.hexdigest()


def descriptor(path, workflow, options, created, cancel):
    size = path.stat().st_size
    if not 24 <= size <= REMOTE_IMAGE_LIMIT:
        raise ValueError("遠端圖片超出可傳輸的大小。")
    return {"id":path.name, "bytes":size, "sha256":checksum(path,cancel), "kind":"image",
            "model":MODELS["image"][1], "workflow":workflow, "options":options, "created":created}


def validate_artifact(value):
    if (not isinstance(value, dict) or value.get("kind") != "image"
            or not re.fullmatch(r"[a-f0-9]{12}\.png", str(value.get("id","")))
            or not re.fullmatch(r"[a-f0-9]{64}", str(value.get("sha256","")))
            or type(value.get("bytes")) is not int or not 24 <= value["bytes"] <= REMOTE_IMAGE_LIMIT
            or value.get("workflow") not in IMAGE_WORKFLOWS):
        raise ValueError("遠端作品資訊無效。")
    return {key:value[key] for key in ("id","bytes","sha256","kind","workflow")} | {
        "model":MODELS["image"][1], "options":workflow_options("image",value["workflow"],value.get("options"))}


def fetch_image(client, request, artifact, output, staging, cancel, update):
    artifact = validate_artifact(artifact)
    key = sha256(f"{client.id}:{request}".encode()).hexdigest()
    output.mkdir(parents=True,exist_ok=True)
    staging.mkdir(parents=True,exist_ok=True)
    if not owned(output) or not owned(staging):
        raise ValueError("作品下載目錄不安全。")
    target = output / f"{key[:12]}.png"
    part = staging / f"{key[:32]}-{artifact['sha256'][:24]}.part"
    size, expected = artifact["bytes"], artifact["sha256"]
    with exclusive(staging / f"{key[:32]}.lock"):
        if target.exists():
            path = work_file(output,target.name)
            if path.stat().st_size == size and checksum(path,cancel) == expected:
                return path
            raise ValueError("本機同名作品與遠端結果不一致。")
        if not owned(part) or part.exists() and (not part.is_file() or part.stat().st_nlink != 1):
            raise ValueError("作品下載暫存檔不安全。")
        offset = part.stat().st_size if part.exists() else 0
        if offset > size:
            part.unlink()
            offset = 0
        if offset < size:
            headers = {"Range":f"bytes={offset}-"} if offset else {}
            with client.request("GET", f"/v1/jobs/{request}/artifact", headers=headers) as response:
                if (response.status != (206 if offset else 200) or response.getheader("ETag") != f'"{expected}"'
                        or response.getheader("Content-Length") != str(size-offset)
                        or offset and response.getheader("Content-Range") != f"bytes {offset}-{size-1}/{size}"):
                    raise ValueError("遠端作品長度或續傳範圍不符。")
                with part.open("ab") as stream:
                    while offset < size:
                        if cancel.is_set():
                            raise InterruptedError("已停止下載，稍後可續傳。")
                        data = response.read(min(CHUNK,size-offset))
                        if not data:
                            raise ConnectionError("作品傳輸中斷。請重新查詢任務並續傳。")
                        stream.write(data)
                        offset += len(data)
                        update(message="下載遠端作品…",received=offset,total=size)
        with part.open("rb") as stream:
            header = stream.read(24)
        if not header.startswith(FORMATS["image"][1]) or header[12:16] != b"IHDR" or checksum(part,cancel) != expected:
            part.unlink(missing_ok=True)
            raise ValueError("遠端圖片內容未通過 SHA-256 或 PNG 格式驗證。")
        if cancel.is_set():
            raise InterruptedError("已取消發布作品。")
        if os.name == "nt":
            part.rename(target)
        else:
            os.link(part,target)
            part.unlink()
        return target


def await_image(client, request, cancel, update):
    deadline = monotonic() + 900
    while not cancel.wait(0.45) and monotonic() < deadline:
        job = client.job(request)
        if job["state"] == "completed":
            return validate_artifact(job.get("artifact"))
        if job["state"] not in ("queued","running"):
            raise RuntimeError(str(job.get("message") or "遠端圖片任務已中止。")[:300])
        update(message=job.get("message") or "等待遠端主機…")
    if cancel.is_set():
        try:
            client.json("POST",f"/v1/jobs/{request}/cancel")
        except (OSError,ValueError):
            pass
        raise InterruptedError("已取消遠端圖片任務。")
    raise TimeoutError(f"等待遠端圖片逾時。請以任務識別碼 {request} 查詢。")

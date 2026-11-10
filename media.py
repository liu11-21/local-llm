"""Submit built-in media workflows to the local ComfyUI server."""
import http.client
import json
from pathlib import Path
import secrets
from tempfile import NamedTemporaryFile
import time
from urllib.parse import quote, urlencode
from uuid import uuid4

IMAGE_MODEL = "v1-5-pruned-emaonly-fp16.safetensors"
VIDEO_MODEL = "wan2.1_t2v_1.3B_fp16.safetensors"
VIDEO_TEXT = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VIDEO_VAE = "wan_2.1_vae.safetensors"
MUSIC_MODEL = "ace_step_v1_3.5b.safetensors"
MODELS = {
    "image": ("圖片", "Stable Diffusion 1.5", (("CheckpointLoaderSimple", "ckpt_name", IMAGE_MODEL),)),
    "video": ("短片", "Wan 2.1 T2V 1.3B", (
        ("UNETLoader", "unet_name", VIDEO_MODEL), ("CLIPLoader", "clip_name", VIDEO_TEXT),
        ("VAELoader", "vae_name", VIDEO_VAE),
    )),
    "music": ("音樂", "ACE-Step v1", (("CheckpointLoaderSimple", "ckpt_name", MUSIC_MODEL),)),
}
FORMATS = {"image": (".png", b"\x89PNG\r\n\x1a\n"), "video": (".webm", b"\x1aE\xdf\xa3"),
           "music": (".flac", b"fLaC")}
RESULT_LIMIT = 512 * 1024 ** 2
JSON_LIMIT = 8 * 1024 ** 2


PARAMETERS = {
    "width": ("寬度", 256, 1024, 16, "4", "width"),
    "height": ("高度", 256, 1024, 16, "4", "height"),
    "frames": ("影格數", 9, 65, 4, "4", "length"),
    "fps": ("每秒影格", 8, 30, 1, "9", "fps"),
    "seconds": ("秒數", 5, 60, 1, "4", "seconds"),
    "steps": ("取樣步數", 1, 80, 1, "7", "steps"),
    "cfg": ("提示詞強度", 1, 20, 1, "7", "cfg"),
    "seed": ("種子（留白為隨機）", 0, 2**53 - 1, 1, "7", "seed"),
    "negative": ("排除提示詞", 0, 2000, 1, "3", "text"),
}

WORKFLOWS = {
    "sd15": ("image", "Stable Diffusion 1.5", {"width":512, "height":512, "steps":24, "cfg":7, "seed":None, "negative":""}),
    "sd15-preview": ("image", "Stable Diffusion 1.5 · 快速預覽", {"width":384, "height":384, "steps":10, "cfg":7, "seed":None, "negative":""}),
    "wan21": ("video", "Wan 2.1 T2V 1.3B", {"width":480, "height":272, "frames":33, "fps":16, "steps":24, "cfg":5, "seed":None, "negative":""}),
    "ace-step": ("music", "ACE-Step v1", {"seconds":20, "steps":30, "cfg":4, "seed":None}),
}
DEFAULT_WORKFLOWS = {"image": "sd15", "video": "wan21", "music": "ace-step"}


def workflow_spec(kind, workflow_id=None):
    spec = WORKFLOWS.get(workflow_id or DEFAULT_WORKFLOWS.get(kind))
    if spec is None or spec[0] != kind:
        raise ValueError("此工作流程與創作類型不相容。")
    return spec


def workflow_manifest():
    return [{"id": key, "kind": kind, "label": label, "engine": "comfyui",
             "models": [file for _, _, file in MODELS[kind][2]], "output": FORMATS[kind][0],
             "parameters": [{"key": param, "label": PARAMETERS[param][0], "default": default,
                             "basic": param in {"width", "height", "frames", "seconds"},
                             "min": PARAMETERS[param][1], "max": PARAMETERS[param][2], "step": PARAMETERS[param][3],
                             "type": "text" if param == "negative" else "integer"}
                            for param, default in defaults.items()]}
            for key, (kind, label, defaults) in WORKFLOWS.items()]


def workflow_options(kind, workflow_id, options):
    _, _, defaults = workflow_spec(kind, workflow_id)
    if options is None:
        options = {}
    if not isinstance(options, dict) or options.keys() - defaults.keys():
        raise ValueError("包含此工作流程不支援的參數。")
    settings = {**defaults, **options}
    for key, value in settings.items():
        label, minimum, maximum, step, _, _ = PARAMETERS[key]
        if key == "negative" and isinstance(value, str) and len(value) <= maximum:
            continue
        if key == "seed" and value is None:
            continue
        if key == "negative" or type(value) is not int or not minimum <= value <= maximum or (value - minimum) % step:
            raise ValueError(f"{label}超出此工作流程支援的範圍。")
    return settings


def workflow(kind, prompt, lyrics="", seed=None, *, workflow_id=None, options=None):
    settings = workflow_options(kind, workflow_id, options)
    graph = {}

    def node(number, class_type, **inputs):
        graph[str(number)] = {"class_type": class_type, "inputs": inputs}

    seed = seed if seed is not None else settings["seed"]
    settings["seed"] = secrets.randbits(53) if seed is None else seed
    prefix = f"LocalLLM/{kind}"
    if kind == "image":
        node(1, "CheckpointLoaderSimple", ckpt_name=IMAGE_MODEL)
        node(2, "CLIPTextEncode", clip=["1", 1], text=prompt)
        node(3, "CLIPTextEncode", clip=["1", 1], text="")
        node(4, "EmptyLatentImage", width=512, height=512, batch_size=1)
        model, vae, steps, cfg, scheduler = ["1", 0], ["1", 2], 24, 7, "normal"
    elif kind == "video":
        node(1, "UNETLoader", unet_name=VIDEO_MODEL, weight_dtype="default")
        node(5, "CLIPLoader", clip_name=VIDEO_TEXT, type="wan", device="default")
        node(6, "VAELoader", vae_name=VIDEO_VAE)
        node(2, "CLIPTextEncode", clip=["5", 0], text=prompt)
        node(3, "CLIPTextEncode", clip=["5", 0], text="")
        node(4, "EmptyHunyuanLatentVideo", width=480, height=272, length=33, batch_size=1)
        node(10, "ModelSamplingSD3", model=["1", 0], shift=8.0)
        model, vae, steps, cfg, scheduler = ["10", 0], ["6", 0], 24, 5, "simple"
    elif kind == "music":
        node(1, "CheckpointLoaderSimple", ckpt_name=MUSIC_MODEL)
        node(2, "TextEncodeAceStepAudio", clip=["1", 1], tags=prompt,
             lyrics=lyrics or "[instrumental]", lyrics_strength=1.0)
        node(3, "ConditioningZeroOut", conditioning=["2", 0])
        node(4, "EmptyAceStepLatentAudio", seconds=20.0, batch_size=1)
        node(10, "ModelSamplingSD3", model=["1", 0], shift=3.0)
        model, vae, steps, cfg, scheduler = ["10", 0], ["1", 2], 30, 4, "simple"
    else:
        raise ValueError("不支援的生成類型。")

    node(7, "KSampler", model=model, positive=["2", 0], negative=["3", 0],
         latent_image=["4", 0], seed=seed, steps=steps, cfg=cfg,
         sampler_name="euler", scheduler=scheduler, denoise=1.0)
    node(8, "VAEDecodeAudio" if kind == "music" else "VAEDecode", samples=["7", 0], vae=vae)
    if kind == "music":
        node(9, "SaveAudio", audio=["8", 0], filename_prefix=prefix)
    elif kind == "video":
        node(9, "SaveWEBM", images=["8", 0], filename_prefix=prefix, codec="vp9", fps=16.0, crf=32.0)
    else:
        node(9, "SaveImage", images=["8", 0], filename_prefix=prefix)
    for key, value in settings.items():
        _, _, _, _, node_id, argument = PARAMETERS[key]
        graph[node_id]["inputs"][argument] = value
    return graph


class ComfyClient:
    def __init__(self, port=8188, timeout=15):
        if not 1 <= port <= 65535:
            raise ValueError("ComfyUI 連接埠須介於 1 和 65535。")
        self.port = port
        self.timeout = timeout

    def json(self, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout)
        try:
            if payload is None:
                connection.request("GET", path)
            else:
                connection.request("POST", path, json.dumps(payload).encode("utf-8"),
                                   {"Content-Type": "application/json"})
            with connection.getresponse() as response:
                raw = response.read(JSON_LIMIT + 1)
                if response.status != 200:
                    raise RuntimeError(f"ComfyUI HTTP {response.status}：{raw[:1400].decode('utf-8', 'replace')}")
            if len(raw) > JSON_LIMIT:
                raise ValueError("ComfyUI 回應過大。")
            return json.loads(raw)
        except OSError as error:
            raise ConnectionError(f"無法連線到本機 ComfyUI（127.0.0.1:{self.port}）。") from error
        finally:
            connection.close()

    def missing_models(self, kind):
        missing = []
        for loader, argument, filename in MODELS[kind][2]:
            info = self.json("/object_info/" + loader).get(loader, {})
            values = info.get("input", {}).get("required", {}).get(argument, [])
            choices = values[0] if values and isinstance(values[0], list) else []
            if filename not in choices:
                missing.append(filename)
        return missing

    def check_models(self, kind):
        missing = self.missing_models(kind)
        if missing:
            raise ValueError("請先在 ComfyUI 安裝模型：" + "、".join(missing))

    def cancel_prompt(self, prompt_id):
        try:
            result = self.json("/api/jobs/" + quote(prompt_id, safe="") + "/cancel", {})
        except (OSError, RuntimeError, ValueError):
            return False
        return isinstance(result, dict) and result.get("cancelled") is True

    def generate(self, kind, prompt, lyrics, output_dir, cancel, report, *, workflow_id=None, options=None, on_source=None):
        graph = workflow(kind, prompt, lyrics, workflow_id=workflow_id, options=options)
        self.check_models(kind)
        if cancel.is_set():
            raise InterruptedError("已停止等待生成。")
        job = self.json("/prompt", {"prompt": graph, "client_id": str(uuid4())})
        prompt_id = job.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise RuntimeError("ComfyUI 沒有傳回生成任務編號。")
        report("已排入 ComfyUI，正在等待生成…")
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            if cancel.wait(1):
                if self.cancel_prompt(prompt_id):
                    raise InterruptedError("已取消本次 ComfyUI 生成。")
                raise InterruptedError("已停止等待。ComfyUI 未確認取消，請在 ComfyUI 檢查任務。")
            result = self.json("/history/" + quote(prompt_id, safe="")).get(prompt_id)
            if not result:
                continue
            status = result.get("status", {})
            if status.get("status_str") == "error":
                for event in status.get("messages", []):
                    if len(event) == 2 and event[0] == "execution_error":
                        raise RuntimeError(str(event[1].get("exception_message", "ComfyUI 生成失敗。"))[:700])
                raise RuntimeError("ComfyUI 生成失敗，請查看 ComfyUI 日誌。")
            outputs = result.get("outputs", {}).get("9", {})
            suffix, magic = FORMATS[kind]
            for items in outputs.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or item.get("type") != "output":
                        continue
                    name = item.get("filename")
                    if isinstance(name, str) and name.lower().endswith(suffix):
                        path = self.save_output(name, item.get("subfolder", ""), suffix, magic, output_dir, cancel)
                        if on_source:
                            on_source({"engine": "ComfyUI", "job": prompt_id[:160], "original": name[:300]})
                        return path
            raise RuntimeError("ComfyUI 完成任務，但找不到可儲存的輸出。")
        raise TimeoutError("等待 ComfyUI 生成逾時，請在 ComfyUI 查看任務狀態。")

    def save_output(self, name, folder, suffix, magic, output_dir, cancel):
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / (uuid4().hex[:12] + suffix)
        query = urlencode({"filename": name, "subfolder": folder, "type": "output"})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        temporary = None
        try:
            connection.request("GET", "/view?" + query)
            with connection.getresponse() as response:
                if response.status != 200 or response.read(len(magic)) != magic:
                    raise ValueError("ComfyUI 傳回的媒體格式不符。")
                size = response.length
                expected = size + len(magic) if size is not None else None
                with NamedTemporaryFile(dir=output_dir, suffix=".part", delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(magic)
                    while block := response.read(256 * 1024):
                        if cancel.is_set():
                            raise InterruptedError("已停止儲存媒體。")
                        if stream.tell() + len(block) > RESULT_LIMIT:
                            raise ValueError("生成檔案超過 512 MiB。")
                        stream.write(block)
                    if stream.tell() <= len(magic) or (expected is not None and stream.tell() != expected):
                        raise ValueError("ComfyUI 傳回的媒體不完整，請重新生成。")
            if cancel.is_set():
                raise InterruptedError("已停止儲存媒體。")
            temporary.rename(target)
            return target
        finally:
            connection.close()
            if temporary is not None:
                temporary.unlink(missing_ok=True)

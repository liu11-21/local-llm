"""Run the web workspace and its native tools on the user's loopback interface."""
import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
from threading import Lock
from urllib.parse import parse_qs, unquote, urlsplit
import webbrowser

from catalog import RECOMMENDED, model_files, recommended_file, search_models
from comfy_runtime import PROFILES, ManagedComfy, check_port, install, install_directory, installed
from downloads import download_model, model_filename
from hardware import FIT_LABELS, detect_hardware, model_fit
from load_plan import plan_load
from media import FORMATS, MODELS, ComfyClient
from model_team import Member, ask_local, cloud_member, run_team
from task_manager import TaskManager

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "docs"
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
          "/logo.png": ("logo.png", "image/png"), "/style.css": ("style.css", "text/css"),
          **{f"/{name}.mjs": (f"{name}.mjs", "text/javascript")
             for name in ("chat", "engine", "workspace", "web-models")}}
MEDIA_TYPES = {".png": "image/png", ".webm": "video/webm", ".flac": "audio/flac"}
MAX_BODY = 64 * 1024


def engine_path(data):
    for folder in (data / "engine-vulkan", ROOT / "engine-vulkan", ROOT / "engine",
                   data.parent / "Programs" / "Local LLM" / "_internal" / "engine-vulkan"):
        candidate = folder / "llama-server.exe"
        if candidate.is_file():
            return candidate
    command = shutil.which("llama-server")
    return Path(command) if command else None


def field(data, key, limit, *, optional=False):
    if not isinstance(data, dict):
        raise ValueError(f"欄位格式不符：{key}")
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > limit or (not optional and not value.strip()):
        raise ValueError(f"欄位格式不符：{key}")
    return value.strip()


class Workspace:
    def __init__(self, data):
        self.data = data.resolve()
        self.data.mkdir(parents=True, exist_ok=True)
        self.models = self.data / "models"
        self.outputs = self.data / "outputs"
        self.comfy = ManagedComfy()
        self.lock = Lock()
        self.scheduler = TaskManager(self.perform)

    def model(self, name):
        if name != Path(name).name or not name.lower().endswith(".gguf"):
            raise ValueError("請選擇模型資料夾內的 GGUF 檔案。")
        path = self.models / name
        if not path.is_file() or path.resolve().parent != self.models.resolve():
            raise ValueError("找不到這個 GGUF。請更新本機模型清單。")
        return path

    def engine(self):
        executable = engine_path(self.data)
        if not executable:
            raise ValueError("找不到 llama-server。請安裝桌面版，或將官方引擎解壓到 engine-vulkan。")
        return executable

    def info(self):
        hardware = detect_hardware(self.models)
        recommendations = []
        for repo, (description, *_rest) in RECOMMENDED.items():
            name, size, url = recommended_file(repo)
            present = (self.models / name).is_file()
            fit = model_fit(hardware, size, installed=present)
            recommendations.append((fit, size, {"repo": repo, "description": description, "name": name,
                                                 "size": size, "url": url, "fit": FIT_LABELS[fit]}))
        recommendations.sort(key=lambda row: row[:2])
        return {"models": sorted(p.name for p in self.models.glob("*.gguf") if p.is_file()),
                "model_folder": str(self.models), "hardware": asdict(hardware),
                "engine": engine_path(self.data) is not None, "comfy_running": self.comfy.running(),
                "comfy_port": self.comfy.port if self.comfy.running() else None,
                "profiles": list(PROFILES), "recommended": [row[2] for row in recommendations]}

    def launch(self, action, data):
        return self.scheduler.submit(action, data)

    def snapshot(self, job_id, cancel=False):
        job = self.scheduler.snapshot(job_id, cancel)
        job["state"] = {"queued": "running", "completed": "done", "failed": "error"}.get(job["state"], job["state"])
        return job

    def perform(self, action, data, cancel, update):
        def report(message):
            update(message=message)

        if action == "download":
            url = field(data, "url", 1400)
            parts = urlsplit(url)
            if parts.scheme != "https" or parts.netloc != "huggingface.co" or parts.query or parts.fragment:
                raise ValueError("請使用公開的 Hugging Face GGUF 下載網址。")
            model_filename(url)
            workers = data.get("workers")
            if type(workers) is not int:
                raise ValueError("下載執行緒數量無效。")
            def progress(received, total, count):
                update(received=received, total=total, message=f"下載中 · {count} 個執行緒")
            path = download_model(url, self.models, workers, cancel, progress)
            return {"name": path.name, "message": f"已下載 {path.name}"}

        if action == "chat":
            path = self.model(field(data, "model", 180))
            prompt = field(data, "prompt", 6000)
            history = data.get("history", [])
            if not isinstance(history, list) or len(history) > 8 or len(history) % 2:
                raise ValueError("對話紀錄格式不符。")
            history = [{"role": "user" if index % 2 == 0 else "assistant",
                        "content": field(message, "content", 6000)} for index, message in enumerate(history)]
            executable = self.engine()
            report("正在估算記憶體並載入 GGUF…")
            plan = plan_load(executable, path)
            answer = ask_local(Member(path.name, path=path), executable, plan, prompt, [], cancel, report,
                               history=history)
            return {"answer": answer, "plan": asdict(plan), "message": "回答完成。"}

        if action == "team":
            entries, lead = data.get("members"), data.get("lead")
            if not isinstance(entries, list) or not 2 <= len(entries) <= 6 or type(lead) is not int:
                raise ValueError("請加入 2–6 個成員並指定主模型。")
            members = []
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError("模型成員格式不符。")
                if entry.get("kind") == "local":
                    path = self.model(field(entry, "model", 180))
                    members.append(Member(path.name, path=path))
                elif entry.get("kind") == "cloud":
                    members.append(cloud_member(field(entry, "label", 60, optional=True),
                        field(entry, "url", 500), field(entry, "model", 200), field(entry, "key", 1000)))
                else:
                    raise ValueError("模型成員類型不符。")
            executable = self.engine() if any(member.path for member in members) else None
            states = ["排隊中"] * len(members)
            def row(index, state):
                states[index] = state
                update(members=states.copy())
            result = run_team(members, lead, field(data, "prompt", 12000), executable,
                              self.outputs / "teams", cancel, report, row, serial=data.get("serial") is True)
            drafts = [{"name": member.label, "text": path.read_text(encoding="utf-8")}
                      for index, member in enumerate(members, 1)
                      if (path := result.directory / f"member-{index:02d}.md").is_file()]
            return {"answer": result.answer, "drafts": drafts, "folder": str(result.directory), "message": result.status}

        if action == "comfy-start":
            profile = field(data, "profile", 40)
            if profile not in PROFILES:
                raise ValueError("請選擇有效的 ComfyUI 便攜版。")
            if self.comfy.running():
                raise ValueError("ComfyUI 已啟動，請先停止再更換版本。")
            port = data.get("port")
            if type(port) is not int:
                raise ValueError("請填寫 ComfyUI 連接埠。")
            ComfyClient(port)
            check_port(port)
            path = install_directory(self.data / "comfyui", profile)
            if not installed(path):
                path = install(self.data / "comfyui", profile, cancel, report,
                               lambda received, total: update(received=received, total=total))
            update(received=None, total=None, message="正在啟動 ComfyUI…")
            self.comfy.start(path, profile, port, cancel)
            return {"port": port, "folder": str(path / "ComfyUI" / "models"), "message": "ComfyUI 已就緒。"}

        if action == "comfy-stop":
            self.comfy.stop()
            return {"message": "已停止由工作台啟動的 ComfyUI。"}

        if action == "media":
            kind = field(data, "kind", 12)
            if kind not in MODELS:
                raise ValueError("請選擇圖片、短片或音樂。")
            port = self.comfy.port if self.comfy.running() else data.get("port")
            if type(port) is not int:
                raise ValueError("請填寫 ComfyUI 連接埠。")
            path = ComfyClient(port).generate(kind, field(data, "prompt", 12000),
                                              field(data, "lyrics", 12000, optional=True), self.outputs, cancel, report,
                                              workflow_id=field(data, "workflow", 40, optional=True),
                                              options=data.get("options"))
            return {"file": f"/output/{path.name}", "message": f"已保存 {path.name}"}
        raise ValueError("這個本機功能不存在。")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, value):
        self.payload(status, json.dumps(value, ensure_ascii=False).encode(), "application/json")

    def payload(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def allowed_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.allowed_host():
            return self.respond(403, {"error": "請使用工作台顯示的本機網址。"})
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        workspace = self.server.workspace
        try:
            if url.path in STATIC:
                name, content_type = STATIC[url.path]
                return self.payload(200, (WEB / name).read_bytes(), content_type)
            if url.path == "/api/info":
                return self.respond(200, workspace.info())
            if url.path == "/api/search":
                return self.respond(200, search_models(query.get("q", [""])[0][:120]))
            if url.path == "/api/files":
                return self.respond(200, model_files(query.get("repo", [""])[0][:150]))
            if url.path == "/api/plan":
                return self.respond(200, asdict(plan_load(workspace.engine(), workspace.model(query.get("model", [""])[0]))))
            if url.path.startswith("/api/job/"):
                return self.respond(200, workspace.snapshot(url.path.rsplit("/", 1)[-1]))
            if url.path.startswith("/output/"):
                name = unquote(url.path.removeprefix("/output/"))
                if re.fullmatch(r"[a-f0-9]{12}\.(png|webm|flac)", name):
                    path = workspace.outputs / name
                    with path.open("rb") as stream:
                        self.send_response(200)
                        self.send_header("Content-Type", MEDIA_TYPES[path.suffix])
                        self.send_header("Content-Length", str(path.stat().st_size))
                        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                        self.end_headers()
                        try:
                            shutil.copyfileobj(stream, self.wfile, length=256 * 1024)
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                    return
            self.respond(404, {"error": "找不到頁面或作品。"})
        except (ValueError, OSError) as error:
            self.respond(400, {"error": str(error)[:1500]})

    def do_POST(self):
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if not self.allowed_host() or self.headers.get("Origin") != origin:
            return self.respond(403, {"error": "本機操作只能從這個工作台發出。"})
        if self.headers.get_content_type() != "application/json":
            return self.respond(415, {"error": "需要 JSON 請求。"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 2 <= length <= MAX_BODY:
                raise ValueError("請求大小不符。")
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("請求格式不符。")
            if self.path.startswith("/api/cancel/"):
                return self.respond(200, self.server.workspace.snapshot(self.path.rsplit("/", 1)[-1], cancel=True))
            action = self.path.removeprefix("/api/run/")
            if self.path != f"/api/run/{action}" or action not in {"chat", "download", "team", "media", "comfy-start", "comfy-stop"}:
                return self.respond(404, {"error": "找不到本機操作。"})
            self.respond(202, self.server.workspace.launch(action, data))
        except (ValueError, OSError) as error:
            self.respond(400, {"error": str(error)[:1500]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "LocalLLM")
    parser.add_argument("--no-browser", action="store_true")
    options = parser.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", options.port), Handler) as server:
        workspace = server.workspace = Workspace(options.data_dir)
        url = f"http://127.0.0.1:{server.server_port}/"
        print(f"Local LLM 網頁工作台：{url}", flush=True)
        if not options.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            workspace.scheduler.close()
            workspace.comfy.stop()


if __name__ == "__main__":
    main()

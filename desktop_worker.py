"""Local desktop worker: one line of JSON in, one line out, no HTTP listener."""
import argparse
from contextlib import closing, contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.request import urlopen
from uuid import uuid4
import hashlib
import hmac
import shutil
import tempfile
import zipfile

from catalog import model_files, search_models
from engine import LocalEngine
from hardware import detect_hardware, estimate_ram
from load_plan import allocate, engine_devices, plan_load
from media import MODELS
from runtime_provider import Providers, route
from web_bridge import Workspace, engine_path, field

ENGINE_VERSION = "b11810"
ENGINE_FILE = f"llama-{ENGINE_VERSION}-bin-win-vulkan-x64.zip"
ENGINE_HASH = "96a04cf289479b3404a559eab0db7dba9877080a61f5f5fdba9d85eb6ca0f324"
ENGINE_BYTES = 36868097
ENGINE_LICENSE_HASH = "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d"
MAX_LINE = 256 * 1024
ACTIONS = {"chat", "download", "team", "comfy-start", "comfy-stop", "media", "engine-start",
           "engine-stop", "engine-install"}


def install_engine(root, cancel, update):
    if os.name != "nt":
        raise ValueError("這個引擎套件僅支援 Windows x64。")
    with tempfile.TemporaryDirectory(prefix="engine-", dir=root) as scratch:
        staging = Path(scratch)
        archive = staging / "engine.zip"
        files = staging / "payload"
        files.mkdir()
        digest, received = hashlib.sha256(), 0
        url = f"https://github.com/ggml-org/llama.cpp/releases/download/{ENGINE_VERSION}/{ENGINE_FILE}"
        with urlopen(url, timeout=20) as source, archive.open("wb") as dest:
            while data := source.read(256 * 1024):
                received += len(data)
                if received > ENGINE_BYTES or cancel.is_set():
                    raise ValueError("下載大小不符，或已取消。")
                dest.write(data)
                digest.update(data)
                update(received=received, total=ENGINE_BYTES, message="正在下載官方 llama.cpp")
        if received != ENGINE_BYTES or not hmac.compare_digest(digest.hexdigest(), ENGINE_HASH):
            raise ValueError("引擎校驗失敗，未安裝任何檔案。")
        update(message="已通過 SHA-256 驗證，正在安裝引擎")
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                name = item.filename
                if item.is_dir() or "/" in name or "\\" in name or ":" in name:
                    continue
                if name.endswith(".dll") or name == "llama-server.exe" or name.startswith("LICENSE"):
                    with bundle.open(item) as source, (files / name).open("xb") as dest:
                        shutil.copyfileobj(source, dest)
        if not (files / "llama-server.exe").is_file() or not (files / "LICENSE-LLVM-OpenMP").is_file():
            raise ValueError("引擎套件缺少執行檔或授權文件。")
        license_text = (Path(__file__).resolve().parent / "third_party" / "llama.cpp-b11810-LICENSE").read_bytes()
        if not hmac.compare_digest(hashlib.sha256(license_text).hexdigest(), ENGINE_LICENSE_HASH):
            raise ValueError("引擎授權文件校驗失敗，未安裝任何檔案。")
        (files / "LICENSE-llama.cpp").write_bytes(license_text)
        if cancel.is_set():
            raise ValueError("已取消安裝。")
        files.rename(root / "engine-vulkan")


class Desktop(Workspace):
    def __init__(self, data):
        super().__init__(data)
        self.local = LocalEngine()
        self.active = None
        self.providers = Providers()
        self.database = self.data / "desktop.sqlite3"
        self.hardware_cache = None
        with self.connect() as db:
            db.executescript("""
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, title TEXT, touched TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS messages(chat TEXT, role TEXT, text TEXT);
              CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, action TEXT, state TEXT, message TEXT,
                                              touched TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
            """)
            db.execute("UPDATE tasks SET state='interrupted' WHERE state='running'")

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as db, db:
            yield db

    def history(self, chat):
        with self.connect() as db:
            return [{"role": role, "content": value} for role, value in db.execute(
                "SELECT role,text FROM messages WHERE chat=? ORDER BY rowid", (chat,))]

    def prepare(self, data, cancel, update):
        name = field(data, "model", 180)
        mode = data.get("mode", "auto")
        context = data.get("context", 2048)
        if mode not in ("auto", "cpu") or context not in (2048, 4096, 8192):
            raise ValueError("請選擇有效的運算模式與上下文長度。")
        if self.comfy.running():
            raise ValueError("請先停止 ComfyUI，釋放記憶體後再載入文字模型。")
        path, executable = self.model(name), self.engine()
        if self.active and self.active[:3] == (name, mode, context) and self.local.running():
            return self.active[-1]
        self.local.stop()
        self.active = None
        update(message="正在估算系統記憶體與 GPU 分層…")
        plan = plan_load(executable, path)
        if mode == "cpu":
            plan = allocate(path.stat().st_size, plan.total_layers, [], mmap_args=plan.mmap_args)
        ram = detect_hardware(self.models).ram_available
        if ram is not None and plan.ram > ram:
            raise ValueError("可用記憶體可能不足。請關閉其他程式、改用更小的模型，或手動選擇其他運算環境。")
        update(message="正在載入模型…", plan=asdict(plan))
        try:
            self.local.start(executable, path, cancel, plan, context=context)
        except RuntimeError as error:
            if plan.layers and not cancel.is_set() and (ram is None or estimate_ram(path.stat().st_size) <= ram):
                plan = allocate(path.stat().st_size, plan.total_layers, [], mmap_args=plan.mmap_args)
                update(message="GPU 載入失敗，正在改用 CPU…", plan=asdict(plan))
                self.local.start(executable, path, cancel, plan, context=context)
            else:
                raise error
        self.active = (name, mode, context, asdict(plan))
        return asdict(plan)

    def perform(self, action, data, cancel, update):
        if action == "engine-install":
            if not engine_path(self.data):
                install_engine(self.data, cancel, update)
            self.hardware_cache = None
            return {"message": "llama.cpp 已就緒。"}
        if action == "engine-stop":
            self.local.stop()
            self.active = None
            return {"message": "文字引擎已停止。"}
        if action == "engine-start":
            return {"plan": self.prepare(data, cancel, update), "message": "文字引擎已就緒。"}
        if action == "chat":
            prompt = field(data, "prompt", 12000)
            chat = field(data, "chat", 32)
            if len(chat) != 32 or any(c not in "0123456789abcdef" for c in chat):
                raise ValueError("對話識別碼無效。")
            model = field(data, "model", 200)
            budget, temperature = data.get("max_tokens", 512), data.get("temperature", 0.4)
            if type(budget) is not int or not 64 <= budget <= 2048 or type(temperature) not in (int, float) or not 0 <= temperature <= 2:
                raise ValueError("生成參數超出範圍。")
            chosen = route(data.get("policy", "auto"), data.get("runtime", "local"), data.get("consent") is True)
            if chosen != "local":
                provider = self.providers.get(chosen)
                plan = None
            else:
                plan = self.prepare(data, cancel, update)
            old = self.history(chat)[-12:]
            messages = old + [{"role": "user", "content": prompt}]
            if chosen == "local":
                while self.local.prompt_tokens(messages) + budget > self.active[2]:
                    if len(messages) < 3:
                        raise ValueError("提示詞和回答長度超過上下文限制。請縮短輸入或提高上下文長度。")
                    messages = messages[2:]
            update(message="正在生成回答…", answer="")
            answer = ""
            stream = (self.local.stream(messages, max_tokens=budget, temperature=temperature, cancel=cancel)
                      if chosen == "local" else provider.stream(model, messages, budget, temperature, cancel))
            with closing(stream):
                for token in stream:
                    if cancel.is_set():
                        return None
                    answer += token
                    if chosen == "local":
                        update(answer=answer)
                    else:
                        update(answer=answer.replace(provider.token, "[已遮蔽金鑰]"))
            if cancel.is_set():
                return None
            if chosen != "local":
                answer = answer.replace(provider.token, "[已遮蔽金鑰]")
            if not answer.strip():
                raise RuntimeError("模型沒有傳回可顯示的文字。")
            with self.connect() as db:
                db.execute("INSERT OR IGNORE INTO chats(id,title) VALUES(?,?)", (chat, prompt[:42]))
                db.execute("UPDATE chats SET touched=CURRENT_TIMESTAMP WHERE id=?", (chat,))
                db.executemany("INSERT INTO messages VALUES(?,?,?)",
                               [(chat, "user", prompt), (chat, "assistant", answer)])
                db.execute("INSERT OR REPLACE INTO settings VALUES('recent_model',?)", (model,))
            return {"answer": answer, "plan": plan, "message": "回答已儲存。"}
        if action in ("comfy-start", "team", "media"):
            self.local.stop()
            self.active = None
        if action == "team":
            if self.comfy.running():
                raise ValueError("請先停止 ComfyUI，再執行模型團隊。")
            members = data.get("members")
            if not isinstance(members, list) or not 2 <= len(members) <= 6:
                raise ValueError("請選擇 2–6 個團隊成員。")
            entries = []
            for item in members:
                runtime = field(item, "runtime", 32)
                model = field(item, "model", 200)
                selected = route(data.get("policy", "auto"), runtime, data.get("consent") is True)
                entries.append({"kind": "local", "model": model} if selected == "local" else
                               self.providers.get(selected).team_entry(model))
            data = {**data, "members": entries}
        return super().perform(action, data, cancel, update)

    def rpc(self, op, data):
        if op == "info":
            info = self.info()
            if self.hardware_cache is None:
                executable = engine_path(self.data)
                self.hardware_cache = engine_devices(executable) if executable else []
            info.update(devices=self.hardware_cache, active=self.active if self.local.running() else None,
                        media=MODELS, output_folder=str(self.outputs), providers=self.providers.list())
            with self.connect() as db:
                recent = db.execute("SELECT value FROM settings WHERE key='recent_model'").fetchone()
                info["recent_model"] = recent[0] if recent else None
            return info
        if op == "search":
            return search_models(field(data, "query", 180, optional=True))
        if op == "files":
            return model_files(field(data, "repo", 180))
        if op == "plan":
            path = self.model(field(data, "model", 180))
            return asdict(plan_load(self.engine(), path))
        if op == "run":
            action = field(data, "action", 30)
            if action not in ACTIONS:
                raise ValueError("未支援的工作。")
            response = self.launch(action, data)
            with self.connect() as db:
                db.execute("INSERT INTO tasks(id,action,state,message) VALUES(?,?,?,?)",
                           (response["id"], action, "running", "正在準備…"))
            return response
        if op in ("job", "cancel"):
            job = self.snapshot(field(data, "id", 32), cancel=op == "cancel")
            if job["state"] != "running":
                with self.connect() as db:
                    db.execute("UPDATE tasks SET state=?,message=? WHERE id=?",
                               (job["state"], job["state"], job["id"]))
            return job
        if op == "history":
            return self.history(field(data, "chat", 32))
        if op == "chats":
            with self.connect() as db:
                return db.execute("SELECT id,title FROM chats ORDER BY touched DESC,rowid DESC LIMIT 100").fetchall()
        if op == "tasks":
            with self.connect() as db:
                return db.execute("SELECT action,state,touched FROM tasks ORDER BY rowid DESC LIMIT 12").fetchall()
        if op == "provider-connect":
            return self.providers.connect(data)
        if op == "provider-remove":
            self.providers.remove(field(data, "id", 32))
            return self.providers.list()
        if op == "colab":
            return self.providers.colab.capabilities()
        raise ValueError("未支援的操作。")

    def close(self):
        with self.lock:
            if self.cancel:
                self.cancel.set()
        self.local.stop()
        self.comfy.stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LocalLLM")
    args = parser.parse_args()
    worker = Desktop(args.data)
    try:
        while raw := sys.stdin.buffer.readline(MAX_LINE + 1):
            if len(raw) > MAX_LINE:
                break
            try:
                request = json.loads(raw)
                if not isinstance(request, dict) or not isinstance(request.get("data"), dict):
                    raise ValueError("工作資料格式不正確。")
                result = {"ok": True, "value": worker.rpc(request.get("op"), request["data"])}
            except Exception as error:
                result = {"ok": False, "error": str(error).strip()[:1500] or "工作無法完成。"}
            sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()
    finally:
        worker.close()


if __name__ == "__main__":
    main()

"""Local desktop worker: one line of JSON in, one line out, no HTTP listener."""
import argparse
from contextlib import closing, contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys
from urllib.request import urlopen
from uuid import uuid4
import hashlib
import hmac
import shutil
import tempfile
from threading import Thread
import zipfile

from app_update import check_workspace_update, download_update
from catalog import model_files, model_source, pinned_model, search_models
from colab_runtime import ColabAdapter
from comfy_runtime import PROFILES, install, install_directory, installed
from desktop_agent import create_plan, messages_for_plan
from download_recovery import recover_downloads
from downloads import check_gguf, download_model
from engine import LocalEngine
from engine_health import EngineHealth
from hardware import detect_hardware, estimate_ram
from load_plan import allocate, engine_devices, plan_load
from media import DEFAULT_WORKFLOWS, MODELS, workflow_options, workflow_spec
from registries import model_identity, recent_works, workspace_registry
from runtime_provider import Providers, route
from task_manager import TaskManager, timestamp
from web_bridge import Workspace, engine_path, field

ENGINE_VERSION = "b11810"
ENGINE_FILE = f"llama-{ENGINE_VERSION}-bin-win-vulkan-x64.zip"
ENGINE_HASH = "96a04cf289479b3404a559eab0db7dba9877080a61f5f5fdba9d85eb6ca0f324"
ENGINE_BYTES = 36868097
ENGINE_LICENSE_HASH = "94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d"
MAX_LINE = 256 * 1024
WORKSPACE_VERSION = "0.6.2"
ACTIONS = {"chat", "download", "team", "comfy-start", "comfy-stop", "media", "engine-start",
           "engine-stop", "engine-install", "comfy-install", "agent", "update-download"}


def chat_id(data):
    value = field(data, "chat", 32)
    if not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("對話識別碼無效。")
    return value


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
        self.llama_health = EngineHealth(self.local.running, self.local.health_probe)
        self.comfy_health = EngineHealth(self.comfy.running, self.comfy.health_probe)
        self.active = None
        self.providers = Providers()
        self.database = self.data / "desktop.sqlite3"
        self.download_cache = self.models / ".localllm-downloads"
        self.hardware_cache = None
        self.agent_plan = None
        self.update_candidate = None
        self.update_state = {"state": "idle"}
        with self.connect() as db:
            db.executescript("""
              PRAGMA journal_mode=WAL;
              CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY, title TEXT, touched TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS messages(chat TEXT, role TEXT, text TEXT);
              CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY, action TEXT, state TEXT, message TEXT,
                                              touched TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
              CREATE TABLE IF NOT EXISTS agent_reports(id TEXT PRIMARY KEY, role TEXT, model TEXT,
                  prompt TEXT, answer TEXT, steps TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
              CREATE TABLE IF NOT EXISTS task_metadata(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS creations(name TEXT PRIMARY KEY, details TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS model_sources(name TEXT PRIMARY KEY COLLATE NOCASE, details TEXT NOT NULL);
            """)
            db.execute("UPDATE tasks SET state='interrupted', message='工作台已關閉。' WHERE state IN ('running','queued')")
            db.execute("""UPDATE task_metadata SET snapshot=json_set(snapshot, '$.state', 'interrupted',
                          '$.finished', ?, '$.message', '工作台已關閉。')
                          WHERE json_extract(snapshot,'$.state') IN ('queued','running')""", (timestamp(),))
            db.execute("CREATE INDEX IF NOT EXISTS messages_chat ON messages(chat)")
            if db.execute("PRAGMA user_version").fetchone()[0] < 2:
                db.execute("PRAGMA user_version=2")
        recover_downloads(self.download_cache, self.models, pinned_model, clean=True)
        self.scheduler = TaskManager(self.perform, self.save_task)

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.database, timeout=5)) as db, db:
            yield db

    def history(self, chat):
        with self.connect() as db:
            return [{"role": role, "content": value} for role, value in db.execute(
                "SELECT role,text FROM messages WHERE chat=? ORDER BY rowid", (chat,))]

    def save_task(self, record):
        with self.connect() as db:
            db.execute("""INSERT INTO tasks(id,action,state,message) VALUES(?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET state=excluded.state,message=excluded.message""",
                       (record["id"], record["action"], record["state"], record["message"]))
            db.execute("INSERT OR REPLACE INTO task_metadata VALUES(?,?)", (record["id"], json.dumps(record)))

    def save_model_source(self, name, path, source):
        record = {**source, "identity": model_identity(path)}
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO model_sources VALUES(?,?)", (name, json.dumps(record)))

    def download(self, data, cancel, update):
        url = field(data, "url", 1400)
        source = pinned_model(url)
        if not source:
            raise ValueError("請在模型中心選擇固定提交版本的 Hugging Face GGUF。")
        workers = data.get("workers")
        if type(workers) is not int or not 1 <= workers <= 16:
            raise ValueError("下載執行緒須介於 1 到 16。")
        name = source["file"].rsplit("/", 1)[-1]
        update(message="正在查詢固定版本的來源與校驗資訊…")
        source = model_source(url)
        expected = source.get("expected_sha256")

        def save(path, sha):
            self.save_model_source(name, path, {**source, "sha256": sha, "downloaded": timestamp(),
                                   "verification": "verified" if expected else "known"})

        path = download_model(url, self.models, workers, cancel,
                              lambda received, total, count: update(received=received, total=total,
                                                                   message=f"下載中 · {count} 個執行緒"),
                              recovery=self.download_cache, expected_size=source.get("size"),
                              expected_sha=expected, before_publish=save)
        return {"name": path.name, "message": f"已下載 {path.name}"}

    def task_list(self):
        live = {job["id"]: job for job in self.scheduler.list()}
        with self.connect() as db:
            saved = db.execute("""SELECT tasks.id,action,state,message,touched,snapshot FROM tasks
                                LEFT JOIN task_metadata USING(id) ORDER BY tasks.rowid DESC LIMIT 60""").fetchall()
        for task_id, action, state, message, created, snapshot in saved:
            if task_id in live:
                continue
            record = json.loads(snapshot) if snapshot else {"id": task_id, "action": action,
                       "kind": action, "state": {"done":"completed", "error":"failed"}.get(state, state),
                       "message": message, "created": created.replace(" ", "T") + "Z"}
            live[task_id] = {**record, "retryable": False}
        return sorted(live.values(), key=lambda job: job["created"], reverse=True)[:60]

    def prepare(self, data, cancel, update):
        name = field(data, "model", 180)
        mode = data.get("mode", "auto")
        context = data.get("context", 2048)
        if mode not in ("auto", "cpu") or context not in (2048, 4096, 8192):
            raise ValueError("請選擇有效的運算模式與上下文長度。")
        if self.comfy.running():
            raise ValueError("請先停止 ComfyUI，釋放記憶體後再載入文字模型。")
        path, executable = self.model(name), self.engine()
        if self.active and self.active[:3] == (name, mode, context) and self.llama_health.usable():
            return self.active[-1]
        with self.llama_health.transition(True, cancel):
            plan = self.load_model(path, executable, mode, context, cancel, update)
        self.active = (name, mode, context, plan)
        return plan

    def load_model(self, path, executable, mode, context, cancel, update):
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
        return asdict(plan)

    def stop_local(self):
        with self.llama_health.transition(False):
            self.local.stop()
            self.active = None

    def engine_health(self):
        active = [task for task in self.scheduler.list() if task["state"] == "running"]
        llama_busy = any(task["action"] in ("chat", "agent") and task["runtime"] == "local" for task in active)
        comfy_busy = any(task["action"] == "media" for task in active)
        comfy_installed = any(installed(install_directory(self.data / "comfyui", profile)) for profile in PROFILES)
        return {"llama": self.llama_health.snapshot(engine_path(self.data) is not None, llama_busy),
                "comfyui": self.comfy_health.snapshot(comfy_installed, comfy_busy)}

    def start_update_check(self):
        with self.lock:
            if self.update_state["state"] == "checking":
                return
            self.update_state = {"state": "checking"}
            self.update_candidate = None

        def check():
            try:
                candidate = check_workspace_update(WORKSPACE_VERSION)
            except Exception:
                status = {"state": "error", "message": "無法讀取 GitHub 的工作台版本。請檢查網路後重試。"}
            else:
                status = ({"state": "available", "tag": candidate.tag, "bytes": candidate.size} if candidate
                          else {"state": "current"})
                with self.lock:
                    self.update_candidate = candidate
            with self.lock:
                self.update_state = status

        Thread(target=check, daemon=True).start()

    def execute_agent(self, plan, cancel, update):
        steps = []

        def report(step):
            steps.append(step)
            update(steps=steps.copy(), message=step)

        prepared = messages_for_plan(plan, self.models, cancel, report)
        if prepared is None or cancel.is_set():
            return None
        messages, evidence = prepared
        self.prepare({"model": plan["model"], "context": 4096}, cancel, update)
        budget = 320
        if self.local.prompt_tokens(messages) + budget > 4096:
            raise ValueError("代理人任務超出模型上下文長度，請縮短描述或減少工具。")
        report(plan["steps"][-1])
        answer = ""
        with closing(self.local.stream(messages, max_tokens=budget, temperature=0.2, cancel=cancel)) as stream:
            for fragment in stream:
                if cancel.is_set():
                    return None
                answer += fragment
                update(answer=answer)
        if cancel.is_set():
            return None
        if not answer.strip():
            raise RuntimeError("本機模型未傳回回答。")
        with self.connect() as db:
            db.execute("INSERT INTO agent_reports(id,role,model,prompt,answer,steps) VALUES(?,?,?,?,?,?)",
                       (plan["id"], plan["role"], plan["model"], plan["prompt"], answer,
                        json.dumps({"steps": steps, "evidence": evidence}, ensure_ascii=False)))
        return {"answer": answer, "message": "代理人報告已儲存。"}

    def perform(self, action, data, cancel, update):
        if action == "download":
            return self.download(data, cancel, update)
        if action in ("comfy-start", "comfy-install"):
            profile = field(data, "profile", 40)
            if profile not in PROFILES:
                raise ValueError("請選擇有效的 ComfyUI 便攜版。")
            if action == "comfy-install":
                root = self.data / "comfyui"
                if not installed(install_directory(root, profile)):
                    install(root, profile, cancel, lambda message: update(message=message),
                            lambda received, total: update(received=received, total=total))
                return {"message": "ComfyUI 已安裝，可以啟動服務。"}
            if not installed(install_directory(self.data / "comfyui", profile)):
                raise ValueError("請先安裝這個 ComfyUI 便攜版。")
        if action == "agent":
            return self.execute_agent(data, cancel, update)
        if action == "update-download":
            candidate = self.update_candidate
            if not candidate or field(data, "tag", 50) != candidate.tag:
                raise ValueError("更新版本已變更。請重新檢查。")
            path = download_update(candidate, self.data / "updates" / "workspace", cancel,
                                   lambda received, total: update(received=received, total=total,
                                                                  message="正在下載並驗證更新…"))
            return {"folder": str(path.parent), "name": path.name, "message": "更新已下載並通過 SHA-256 驗證。"}
        if action == "engine-install":
            if not engine_path(self.data):
                install_engine(self.data, cancel, update)
            self.hardware_cache = None
            return {"message": "llama.cpp 已就緒。"}
        if action == "engine-stop":
            self.stop_local()
            return {"message": "文字引擎已停止。"}
        if action == "engine-start":
            return {"plan": self.prepare(data, cancel, update), "message": "文字引擎已就緒。"}
        if action == "chat":
            chat = chat_id(data)
            replace = data.get("regenerate") is True
            old = self.history(chat)[-12:]
            if replace:
                if len(old) < 2 or [row["role"] for row in old[-2:]] != ["user", "assistant"]:
                    raise ValueError("這個對話尚無可重新生成的回答。")
                prompt = old[-2]["content"]
                old = old[:-2]
            else:
                prompt = field(data, "prompt", 12000)
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
            messages = old + [{"role": "user", "content": prompt}]
            usage = None
            if chosen == "local":
                original = len(messages)
                while (input_tokens := self.local.prompt_tokens(messages)) + budget > self.active[2]:
                    if len(messages) < 3:
                        raise ValueError("提示詞和回答長度超過上下文限制。請縮短輸入或提高上下文長度。")
                    messages = messages[2:]
                usage = {"input": input_tokens, "context": self.active[2], "max_output": budget,
                         "omitted_turns": (original - len(messages)) // 2}
            update(message="正在生成回答…", answer="", usage=usage)
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
                if replace:
                    updated = db.execute("""UPDATE messages SET text=? WHERE role='assistant' AND rowid=
                              (SELECT MAX(rowid) FROM messages WHERE chat=?)""", (answer, chat))
                    if updated.rowcount != 1:
                        raise ValueError("原回答已不存在。")
                else:
                    db.executemany("INSERT INTO messages VALUES(?,?,?)",
                                   [(chat, "user", prompt), (chat, "assistant", answer)])
                db.execute("INSERT OR REPLACE INTO settings VALUES('recent_model',?)", (model,))
            return {"answer": answer, "plan": plan, "usage": usage, "message": "回答已儲存。"}
        if action == "media":
            kind = field(data, "kind", 12)
            selected = field(data, "workflow", 40, optional=True) or DEFAULT_WORKFLOWS.get(kind)
            settings = workflow_options(kind, selected, data.get("options"))
            if settings["seed"] is None:
                settings["seed"] = secrets.randbits(53)
            data = {**data, "workflow":selected, "options":settings}
        if action in ("comfy-start", "team", "media") and (self.local.running() or self.active):
            self.stop_local()
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
        if action in ("comfy-start", "comfy-stop"):
            if action == "comfy-start" and self.comfy.running():
                raise ValueError("請先停止已啟動的 ComfyUI，再更換版本。")
            with self.comfy_health.transition(action == "comfy-start", cancel):
                return super().perform(action, data, cancel, update)
        result = super().perform(action, data, cancel, update)
        if action == "media" and result and result.get("file"):
            kind = field(data, "kind", 12)
            selected = field(data, "workflow", 40, optional=True) or DEFAULT_WORKFLOWS[kind]
            details = {"workflow":selected, "model":workflow_spec(kind, selected)[1],
                       "prompt":field(data, "prompt", 12000), "lyrics":field(data, "lyrics", 12000, optional=True),
                       "options":workflow_options(kind, selected, data.get("options"))}
            with self.connect() as db:
                db.execute("INSERT INTO creations VALUES(?,?)", (result["file"].rsplit("/", 1)[-1], json.dumps(details)))
        return result

    def rpc(self, op, data):
        if op == "engine-health":
            return self.engine_health()
        if op == "agent-plan":
            plan = create_plan(data)
            self.model(plan["model"])
            self.agent_plan = plan
            return {**plan, "tools": plan["tools"].copy(), "steps": plan["steps"].copy()}
        if op == "agent-reports":
            with self.connect() as db:
                return db.execute("SELECT id,role,model,prompt,answer,steps,created "
                                  "FROM agent_reports ORDER BY rowid DESC LIMIT 12").fetchall()
        if op == "update-check":
            self.start_update_check()
        if op in ("update-check", "update-status"):
            with self.lock:
                return {"version": WORKSPACE_VERSION, **self.update_state}
        if op == "update-folder":
            directory = self.data / "updates" / "workspace"
            if os.name != "nt" or not directory.is_dir():
                raise ValueError("找不到已下載的 Windows 更新資料夾。")
            os.startfile(directory)
            return None
        if op == "info":
            info = self.info()
            if self.hardware_cache is None:
                executable = engine_path(self.data)
                self.hardware_cache = engine_devices(executable) if executable else []
            info.update(devices=self.hardware_cache, active=self.active if self.local.running() else None,
                        media=MODELS, output_folder=str(self.outputs), providers=self.providers.list())
            info["comfy_profiles_installed"] = [name for name in PROFILES if installed(install_directory(self.data / "comfyui", name))]
            info["comfy_installed"] = bool(info["comfy_profiles_installed"])
            info["colab_ready"] = self.providers.colab.capabilities()["available"]
            with self.connect() as db:
                recent = db.execute("SELECT value FROM settings WHERE key='recent_model'").fetchone()
                sources = {name.casefold(): json.loads(details) for name, details in db.execute("SELECT * FROM model_sources")}
            info["registry"] = workspace_registry(info, self.models, ENGINE_VERSION, sources)
            info["recoverable_downloads"] = recover_downloads(self.download_cache, self.models, pinned_model)
            info["recent_model"] = recent[0] if recent else None
            return info
        if op == "model-imported":
            path = self.model(field(data, "model", 180))
            check_gguf(path)
            with self.connect() as db:
                existing = db.execute("SELECT details FROM model_sources WHERE name=?", (path.name,)).fetchone()
            if existing and json.loads(existing[0]).get("identity") == model_identity(path):
                raise ValueError("這個檔案已有來源紀錄。")
            self.save_model_source(path.name, path, {"verification": "imported"})
            return None
        if op == "works":
            records = recent_works(self.outputs)
            with self.connect() as db:
                for item in records:
                    row = db.execute("SELECT details FROM creations WHERE name=?", (item["name"],)).fetchone()
                    if row:
                        item.update(json.loads(row[0]))
            return records
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
            if action == "agent":
                if data.get("confirmed") is not True or not self.agent_plan or self.agent_plan["id"] != data.get("id"):
                    raise ValueError("請先預覽並確認代理人計畫。")
                response = self.launch(action, self.agent_plan)
                self.agent_plan = None
            else:
                response = self.launch(action, data)
            return response
        if op in ("job", "cancel"):
            return self.scheduler.snapshot(field(data, "id", 32), cancel=op == "cancel")
        if op == "task-list":
            return self.task_list()
        if op == "task-retry":
            return self.scheduler.retry(field(data, "id", 32))
        if op == "history":
            return self.history(chat_id(data))
        if op in ("chat-rename", "chat-delete"):
            chat = chat_id(data)
            if self.scheduler.has_chat(chat):
                raise ValueError("請等這個對話的任務結束。")
            with self.connect() as db:
                if op == "chat-rename":
                    db.execute("UPDATE chats SET title=? WHERE id=?", (field(data, "title", 80), chat))
                else:
                    if data.get("confirmed") is not True:
                        raise ValueError("請先確認刪除此對話。")
                    db.execute("DELETE FROM messages WHERE chat=?", (chat,))
                    db.execute("DELETE FROM chats WHERE id=?", (chat,))
            return None
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
        if op == "colab-connect":
            return self.providers.colab.connect(field(data, "project", 30), field(data, "region", 32),
                                                field(data, "token", 4096))
        if op == "colab-disconnect":
            self.providers.colab = ColabAdapter()
            return self.providers.colab.capabilities()
        if op == "colab-jobs":
            return self.providers.colab.list_jobs()
        if op == "colab-submit":
            route(data.get("policy", "auto"), "colab", data.get("confirmed") is True)
            return self.providers.colab.submit(field(data, "template", 250), field(data, "source", 900),
                                               field(data, "output", 80), field(data, "account", 180),
                                               data.get("confirmed"))
        raise ValueError("未支援的操作。")

    def close(self):
        self.scheduler.close()
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

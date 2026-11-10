"""Bounded workspace queues. Only one task owns the local compute engine at a time."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from uuid import uuid4
from sqlite3 import Error as DatabaseError
from time import monotonic

from comfy_runtime import PROFILES
from downloads import model_filename

ACTIVE = {"queued", "running", "paused"}
RETRYABLE = {"download", "engine-install", "comfy-install", "media-install", "update-download"}
CAPACITY = {"compute": 1, "network": 2, "remote": 2}
RESOURCES = {"compute": ["local-compute"], "network": ["network", "disk"], "remote": ["network", "external-runtime"]}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def classify(action, data):
    if action in RETRYABLE:
        if action == "download":
            url = data.get("url")
            if not isinstance(url, str):
                raise ValueError("請輸入模型下載網址。")
            target = model_filename(url)
        elif action in ("comfy-install", "media-install"):
            profile = data.get("profile")
            if not isinstance(profile, str) or profile not in PROFILES:
                raise ValueError("請選擇有效的 ComfyUI 便攜版。")
            bundle = PROFILES[profile][0]
            if action == "media-install":
                kind = data.get("kind")
                if kind not in ("image", "video", "music") or data.get("confirmed") is not True:
                    raise ValueError("請確認創作模型的安裝摘要。")
                return "network", "local", f"network:{bundle}", f"{kind}:{bundle}"
            target = bundle
        else:
            target = action
        return "network", "local", f"network:{target.casefold()}", target
    if action == "chat":
        runtime = data.get("runtime", "local")
        runtime = runtime if isinstance(runtime, str) else "local"
        chat = data.get("chat")
        return ("compute" if runtime == "local" else "remote", runtime,
                f"chat:{chat}" if isinstance(chat, str) else None, "")
    return "compute", "local", None, data.get("kind", "") if action == "media" else ""


@dataclass
class Task:
    public: dict
    payload: dict
    key: str | None
    stop: Event = field(default_factory=Event)
    thread: Thread | None = None
    on_snapshot: object = None
    saved_at: float = 0


class PauseTask(Exception):
    """Release the lane while the user decides whether to continue the same task."""


class TaskManager:
    def __init__(self, execute, save=None):
        self.execute = execute
        self.save = save
        self.lock = Lock()
        self.tasks = {}
        self.closed = False

    def submit(self, action, payload, *, plan_id=None, plan_version=None, team_run_id=None, on_snapshot=None):
        lane, runtime, key, target = classify(action, payload)
        with self.lock:
            if self.closed:
                raise ValueError("工作台正在關閉。")
            active = [task for task in self.tasks.values() if task.public["state"] in ACTIVE]
            if len(active) >= 32:
                raise ValueError("任務佇列已滿，請先等候或取消其他任務。")
            if key and any(task.key == key for task in active):
                raise ValueError("相同目標已有執行中或排隊的任務。")
            task_id = uuid4().hex
            task = Task({"id": task_id, "action": action, "kind": target if action == "media" else action,
                         "title": target if action == "download" else "", "lane": lane, "runtime": runtime,
                         "resources": RESOURCES[lane],
                         "state": "queued", "created": timestamp(), "message": "等候可用資源…",
                         "started": None, "finished": None, "error": None}, payload, key)
            if action == "media-install":
                task.public.update(media_target=target)
            if plan_id is not None:
                task.public.update(plan_id=plan_id, plan_version=plan_version)
            if team_run_id is not None:
                task.public["team_run_id"] = team_run_id
            if self.save:
                self.save(self._summary(task))
            if on_snapshot:
                on_snapshot(dict(task.public))
                task.on_snapshot = on_snapshot
            self.tasks[task_id] = task
            self._dispatch()
            return {"id": task_id}

    def _persist(self, task):
        try:
            if task.on_snapshot:
                task.on_snapshot(dict(task.public))
                task.saved_at = monotonic()
            if self.save:
                self.save(self._summary(task))
        except (OSError, DatabaseError):
            task.public["history_warning"] = "任務狀態無法寫入本機歷史。"
        else:
            task.public.pop("history_warning", None)

    def _dispatch(self):
        if self.closed:
            return
        for lane, limit in CAPACITY.items():
            running = sum(task.public["lane"] == lane and task.public["state"] == "running" for task in self.tasks.values())
            for task in self.tasks.values():
                if running >= limit:
                    break
                if task.public["lane"] != lane or task.public["state"] != "queued":
                    continue
                task.public.update(state="running", started=task.public["started"] or timestamp(), message="正在準備…")
                self._persist(task)
                task.thread = Thread(target=self._run, args=(task,), daemon=True)
                task.thread.start()
                running += 1

    def _run(self, task):
        def progress(**values):
            with self.lock:
                if task.public["state"] == "running" and not task.stop.is_set():
                    task.public.update(values)
                    if task.on_snapshot and monotonic() - task.saved_at >= 1:
                        self._persist(task)

        result = None
        failure = None
        try:
            result = self.execute(task.public["action"], task.payload, task.stop, progress)
        except Exception as error:
            failure = error
        with self.lock:
            detail = (str(failure).strip()[:1500] or "本機工作失敗。") if failure else None
            if task.stop.is_set():
                state = "interrupted" if self.closed else "cancelled"
                message = detail if isinstance(failure, InterruptedError) else "已停止任務。"
            elif isinstance(failure, PauseTask):
                state, message = "paused", detail
            elif failure:
                state, message = "failed", detail
            else:
                state, message = "completed", (result or {}).get("message") or "已完成。"
            task.public.update(state=state, finished=None if state == "paused" else timestamp(), message=message, result=result,
                               error=detail if state == "failed" else None)
            if state != "paused" and (task.public["action"] not in RETRYABLE or state == "completed"):
                task.payload = {}
            self._persist(task)
            self._dispatch()
            self._trim()

    def _trim(self):
        finished = [task_id for task_id, task in self.tasks.items() if task.public["state"] not in ACTIVE]
        for task_id in finished[:-100]:
            del self.tasks[task_id]

    def _summary(self, task):
        fields = {key: value for key, value in task.public.items()
                  if key not in {"result", "answer", "plan", "steps", "members", "history_warning"}}
        return {**fields, "retryable": bool(task.payload) and fields["action"] in RETRYABLE
                and fields["state"] in {"failed", "cancelled"}}

    def list(self):
        with self.lock:
            return [{**self._summary(task), "history_warning": task.public.get("history_warning")}
                    for task in reversed(self.tasks.values())]

    def snapshot(self, task_id, cancel=False):
        with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError("找不到這筆工作。")
            if cancel and task.public["state"] in ACTIVE:
                task.stop.set()
                if task.public["state"] in {"queued", "paused"}:
                    task.public.update(state="cancelled", finished=timestamp(), message="已取消任務。")
                    self._persist(task)
                    self._trim()
                else:
                    task.public.update(message="正在取消…")
            return dict(task.public)

    def resume(self, task_id, record_decision):
        with self.lock:
            task = self.tasks.get(task_id)
            if self.closed or task is None or task.public["state"] != "paused":
                raise ValueError("任務目前未在等待核准。")
            record_decision()
            task.public.update(state="queued", message="已記錄決策，等候可用資源…")
            self.tasks[task_id] = self.tasks.pop(task_id)
            self._persist(task)
            self._dispatch()

    def expire_pause(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if task is None or task.public["state"] != "paused":
                return
            message = "AGENT_TIME_LIMIT · 工具核准等待已逾時。"
            task.public.update(state="failed", message=message, error=message, finished=timestamp())
            task.payload = {}
            self._persist(task)
            self._trim()

    def retry(self, task_id):
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or not self._summary(task)["retryable"]:
                raise ValueError("這筆任務不能直接重試。請回原頁面重新提交。")
            action, payload = task.public["action"], task.payload
        return self.submit(action, payload)

    def has_chat(self, chat):
        with self.lock:
            return any(task.key == f"chat:{chat}" and task.public["state"] in ACTIVE for task in self.tasks.values())

    def close(self):
        with self.lock:
            self.closed = True
            for task in self.tasks.values():
                if task.public["state"] in ACTIVE:
                    task.stop.set()
                    if task.public["state"] in {"queued", "paused"}:
                        task.public.update(state="interrupted", finished=timestamp(), message="工作台已關閉。")
                        self._persist(task)

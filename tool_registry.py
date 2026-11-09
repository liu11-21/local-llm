"""Trusted local tool definitions and their execution boundary."""
from dataclasses import asdict, dataclass
from queue import Empty, Queue
import re
from threading import BoundedSemaphore, Event, Thread
from time import monotonic
from typing import Callable

from hardware import detect_hardware

PERMISSIONS = frozenset({"read-only", "network-read", "file-write", "system-action", "paid-external"})
ERRORS = {
    "TOOL_UNKNOWN": "工具不存在。",
    "TOOL_FORBIDDEN": "本次任務沒有使用此工具的權限。",
    "TOOL_APPROVAL_REQUIRED": "此工具調用需要逐次核准。",
    "TOOL_REJECTED": "使用者拒絕這次工具調用。",
    "TOOL_PARAMETERS": "工具參數不符合 Schema。",
    "TOOL_OUTPUT": "工具輸出不符合 Schema。",
    "TOOL_TIMEOUT": "工具執行逾時。",
    "TOOL_CANCELLED": "工具執行已取消。",
    "TOOL_UNAVAILABLE": "工具資料目前無法取得。",
}


class ToolError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"{code} · {ERRORS[code]}")


def obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def string(length, pattern=None):
    return {"type": "string", "maxLength": length, **({"pattern": pattern} if pattern else {})}


def array(items, size):
    return {"type": "array", "items": items, "maxItems": size}


def conforms(schema, value):
    kind = schema["type"]
    if isinstance(kind, list):
        return any(conforms({**schema, "type": item}, value) for item in kind)
    if kind == "object":
        return isinstance(value, dict) and all(key in value for key in schema["required"]) and all(
            key in schema["properties"] and conforms(schema["properties"][key], item) for key, item in value.items())
    if kind == "array":
        return isinstance(value, list) and len(value) <= schema["maxItems"] and all(
            conforms(schema["items"], item) for item in value)
    if kind == "string":
        return isinstance(value, str) and len(value) <= schema["maxLength"] and (
            "pattern" not in schema or re.fullmatch(schema["pattern"], value) is not None)
    if kind == "integer":
        return type(value) is int
    return kind == "null" and value is None


@dataclass(frozen=True)
class Tool:
    id: str
    name: str
    description: str
    version: str
    input_schema: dict
    output_schema: dict
    permission: str = "read-only"
    timeout: float = 4
    cancellable: bool = True
    network: bool = False
    modifies_state: bool = False
    source: str = "Local LLM"
    trusted: bool = True


class ToolRegistry:
    def __init__(self):
        self.entries = {}
        self.slots = BoundedSemaphore(2)

    def register(self, tool: Tool, handler: Callable):
        if tool.id in self.entries:
            raise ValueError("工具 ID 重複。")
        if (not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", tool.id) or tool.permission not in PERMISSIONS
                or not 0 < tool.timeout <= 15):
            raise ValueError("無效的工具契約。")
        self.entries[tool.id] = tool, handler

    def manifests(self):
        return [{**asdict(tool), "error_codes": list(ERRORS)} for tool, _ in self.entries.values()]

    def authorize(self, key, args, allowed, granted=True):
        entry = self.entries.get(key)
        if entry is None:
            raise ToolError("TOOL_UNKNOWN")
        tool, handler = entry
        if (key not in allowed or not tool.trusted or tool.permission != "read-only"
                or tool.network or tool.modifies_state):
            raise ToolError("TOOL_FORBIDDEN")
        if not conforms(tool.input_schema, args):
            raise ToolError("TOOL_PARAMETERS")
        if not granted:
            raise ToolError("TOOL_APPROVAL_REQUIRED")
        return tool, handler

    def execute(self, key, args, allowed, cancel, *, granted=True, timeout=None):
        tool, handler = self.authorize(key, args, allowed, granted)
        if cancel.is_set():
            raise ToolError("TOOL_CANCELLED")
        if not self.slots.acquire(blocking=False):
            raise ToolError("TOOL_UNAVAILABLE")
        completed = Queue(maxsize=1)
        stopped = Event()

        def work():
            try:
                output = handler(args, stopped)
                completed.put((True, output))
            except Exception:
                completed.put((False, None))
            finally:
                self.slots.release()

        try:
            Thread(target=work, daemon=True).start()
        except BaseException:
            self.slots.release()
            raise
        end = monotonic() + (tool.timeout if timeout is None else min(tool.timeout, timeout))
        try:
            while True:
                if cancel.is_set():
                    raise ToolError("TOOL_CANCELLED")
                remaining = end - monotonic()
                if remaining <= 0:
                    raise ToolError("TOOL_TIMEOUT")
                try:
                    ok, output = completed.get(timeout=min(.05, remaining))
                    break
                except Empty:
                    pass
            if cancel.is_set():
                raise ToolError("TOOL_CANCELLED")
            if not ok:
                raise ToolError("TOOL_UNAVAILABLE")
            if not conforms(tool.output_schema, output):
                raise ToolError("TOOL_OUTPUT")
            return output
        finally:
            stopped.set()


def builtins(desktop):
    registry = ToolRegistry()
    integer = {"type": ["integer", "null"]}
    registry.register(Tool("hardware", "本機硬體摘要", "讀取 CPU、RAM 與可用磁碟空間", "1.0", obj(),
                           obj(cpu_threads=integer, ram_total=integer, ram_available=integer, disk_available=integer)),
                      lambda _args, _stop: asdict(detect_hardware(desktop.models)))
    registry.register(Tool("models", "已安裝模型清單", "列出工作台的 GGUF 檔名", "1.0", obj(), array(string(180), 20)),
                      lambda _args, _stop: [p.name for p in sorted(desktop.models.glob("*.gguf"))
                                             if p.is_file() and p.resolve().parent == desktop.models.resolve()
                                             and len(p.name) <= 180][:20])
    registry.register(Tool("engines", "引擎健康狀態", "查詢 llama.cpp 與 ComfyUI 的狀態", "1.0", obj(),
                           obj(llama=string(32), comfyui=string(32))),
                      lambda _args, _stop: {key: value["state"] for key, value in desktop.engine_health().items()})
    registry.register(Tool("tasks", "工作台任務狀態", "查詢最近任務的類型與狀態", "1.0", obj(),
                           array(obj(action=string(32), state=string(32)), 12)),
                      lambda _args, _stop: [{key: item[key] for key in ("action", "state")}
                                             for item in desktop.task_list()[:12]])
    return registry

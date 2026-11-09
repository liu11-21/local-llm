"""Track a managed engine's lifecycle and rate-limit asynchronous health probes."""
from contextlib import contextmanager
from threading import Lock, Thread
from time import monotonic

from task_manager import timestamp


class EngineHealth:
    def __init__(self, running, probe):
        self.running = running
        self.probe = probe
        self.lock = Lock()
        self.status = None
        self.generation = 0
        self.next_probe = 0
        self.probing = False

    def change(self, state, code=None, hint=None):
        self.status = {"state": state, "code": code, "hint": hint, "checked_at": timestamp()}

    @contextmanager
    def transition(self, start, cancel=None):
        with self.lock:
            self.generation += 1
            self.change("starting" if start else "stopping")
        try:
            yield
        except Exception as error:
            with self.lock:
                if cancel and cancel.is_set():
                    self.change("stopped")
                elif isinstance(error, TimeoutError):
                    self.change("failed", "ENGINE_TIMEOUT", "請檢查記憶體、驅動程式及服務日誌，再手動啟動。")
                elif getattr(error, "winerror", None) == 4551:
                    self.change("failed", "ENGINE_POLICY_BLOCKED", "Windows 應用程式控制已封鎖引擎。請查看系統原則與事件紀錄。")
                else:
                    self.change("failed", "ENGINE_START_FAILED" if start else "ENGINE_STOP_FAILED",
                                "請查看任務中心的錯誤，確認模型、硬體後端與連接埠，再手動重試。")
            raise
        else:
            with self.lock:
                self.next_probe = monotonic() + 5
                self.change("ready" if start else "stopped")

    def usable(self):
        with self.lock:
            return self.running() and (self.status is None or self.status["state"] == "ready")

    def snapshot(self, installed, busy=False):
        with self.lock:
            if self.status is None:
                return {"state": "installed" if installed else "not_installed"}
            state = self.status["state"]
            if state in ("ready", "unhealthy") and not self.running():
                self.change("failed", "ENGINE_PROCESS_EXIT", "引擎程序已退出。請在運算環境手動重新啟動。")
            elif state in ("ready", "unhealthy") and not busy and not self.probing and monotonic() >= self.next_probe:
                self.probing = True
                Thread(target=self.check, args=(self.generation,), daemon=True).start()
            return {**self.status, "state": "busy" if busy and self.status["state"] == "ready" else self.status["state"]}

    def check(self, generation):
        try:
            reachable = self.probe()
        except (OSError, ValueError, RuntimeError):
            reachable = False
        finally:
            with self.lock:
                self.probing = False
                self.next_probe = monotonic() + 5
        with self.lock:
            if generation != self.generation or self.status["state"] not in ("ready", "unhealthy"):
                return
            if not self.running():
                self.change("failed", "ENGINE_PROCESS_EXIT", "引擎程序已退出。請在運算環境手動重新啟動。")
            elif reachable:
                self.change("ready")
            else:
                self.change("unhealthy", "ENGINE_API_UNAVAILABLE", "引擎程序仍在，但 API 未回應。可先停止服務再重新啟動。")

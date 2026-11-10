"""Runtime contracts for the desktop; external inference always requires consent."""
from dataclasses import dataclass, field
import http.client
import json
import socket
from threading import Event, Thread
from time import time
from urllib.parse import urlsplit
from uuid import uuid4
from colab_runtime import ColabAdapter

POLICIES = {"auto", "local", "performance", "cost", "privacy", "manual"}


def route(policy, selected, consent=False, *, paired=False):
    if not isinstance(policy, str) or policy not in POLICIES or not isinstance(selected, str):
        raise ValueError("運算路由設定無效。")
    if selected == "local":
        return "local"
    if policy in ("local", "privacy"):
        raise ValueError("目前的運算政策只允許本機推理。")
    if not consent or (policy != "manual" and not paired):
        raise ValueError("請手動選擇運算環境，並同意將本輪及相關歷史傳到該端點。")
    return selected


def endpoint(value):
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("請輸入有效的 HTTPS 端點。")
    url = urlsplit(value.strip())
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or any(c.isspace() for c in value.strip())):
        raise ValueError("端點必須是 HTTPS，且不得包含登入資訊、查詢參數或片段。")
    try:
        port = url.port
        if port == 0:
            raise ValueError
    except ValueError:
        raise ValueError("端點的連接埠無效。") from None
    return url.hostname, port or 443, url.path.rstrip("/") or "/v1"


@dataclass
class OpenAIProvider:
    id: str
    kind: str
    label: str
    host: str
    port: int
    prefix: str
    token: str = field(repr=False)
    models: list = field(default_factory=list)
    connected: bool = False
    checked_at: int = 0

    def summary(self):
        return {"id": self.id, "kind": self.kind, "label": self.label, "host": self.host, "port": self.port,
                "models": self.models, "connected": self.connected, "tasks": ["chat"], "checked_at": self.checked_at}

    def team_entry(self, model):
        if model not in self.models:
            raise ValueError("請從已連線端點的模型清單選擇團隊模型。")
        host = f"[{self.host}]" if ":" in self.host else self.host
        return {"kind": "cloud", "label": self.label, "url": f"https://{host}:{self.port}{self.prefix}",
                "model": model, "key": self.token}

    def request(self, method, path, body=None):
        connection = http.client.HTTPSConnection(self.host, self.port, timeout=20)
        try:
            connection.request(method, self.prefix + path, body, {
                "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError(f"端點回傳 HTTP {response.status}。請檢查 API 路徑、金鑰與服務額度。")
            self.connected = True
            return connection, response
        except Exception:
            self.connected = False
            self.checked_at = int(time())
            connection.close()
            raise

    def discover(self):
        connection, response = self.request("GET", "/models")
        try:
            payload = json.loads(response.read(2 * 1024 * 1024))
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("端點未提供 OpenAI-compatible 模型清單。")
            self.models = [item["id"] for item in payload["data"] if isinstance(item, dict)
                           and isinstance(item.get("id"), str) and 0 < len(item["id"]) <= 200][:250]
            if not self.models:
                raise ValueError("這個端點沒有可選模型。")
            self.checked_at = int(time())
        except Exception:
            self.connected = False
            self.checked_at = int(time())
            raise
        finally:
            response.close()
            connection.close()

    def stream(self, model, messages, max_tokens, temperature, cancel):
        if model not in self.models:
            raise ValueError("請從已連線端點的模型清單選擇模型。")
        limit = "max_completion_tokens" if self.host == "api.openai.com" else "max_tokens"
        body = json.dumps(dict(model=model, messages=messages, temperature=temperature,
                               stream=True, **{limit: max_tokens})).encode()
        if cancel.is_set():
            return
        connection, response = self.request("POST", "/chat/completions", body)
        done = Event()
        sock = connection.sock

        def interrupt():
            while not done.wait(0.1):
                if cancel.is_set() and sock is not None:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return

        Thread(target=interrupt, daemon=True).start()
        try:
            if "text/event-stream" not in response.getheader("Content-Type", ""):
                raise ValueError("端點不支援 OpenAI-compatible SSE 串流。")
            while line := response.readline(1024 * 1024):
                if cancel.is_set():
                    return
                if line.startswith(b"data:"):
                    data = line[5:].strip()
                    if data == b"[DONE]":
                        return
                    for choice in json.loads(data).get("choices", []):
                        part = choice.get("delta", {}).get("content")
                        if isinstance(part, str) and part:
                            yield part
            if not cancel.is_set():
                raise ConnectionError("串流中斷，請檢查網路及端點後重試。")
        except Exception:
            if not cancel.is_set():
                self.connected = False
            raise
        finally:
            done.set()
            response.close()
            connection.close()


class Providers:
    def __init__(self):
        self.items = {}
        self.colab = ColabAdapter()

    def connect(self, data):
        kind = data.get("kind")
        label, key = data.get("label"), data.get("key")
        if kind not in ("remote", "cloud") or not isinstance(label, str) or not 0 < len(label.strip()) <= 50:
            raise ValueError("請選擇環境類型並填寫名稱。")
        if not isinstance(key, str) or not 0 < len(key) <= 4096 or not all(32 < ord(c) < 127 for c in key):
            raise ValueError("請填寫有效的 API 金鑰。")
        if len(self.items) >= 12:
            raise ValueError("最多可連接 12 個端點。")
        provider = OpenAIProvider(uuid4().hex, kind, label.strip(), *endpoint(data.get("url")), key)
        provider.discover()
        self.items[provider.id] = provider
        return provider.summary()

    def get(self, key):
        if key not in self.items:
            raise ValueError("端點未連線，請先到運算環境新增連線。")
        return self.items[key]

    def remove(self, key):
        self.items.pop(key, None)

    def list(self):
        return [p.summary() for p in self.items.values()]

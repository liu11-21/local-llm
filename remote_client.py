"""Private Host client. Credentials are protected by the current Windows user."""
import base64
from contextlib import contextmanager
import ctypes
from dataclasses import dataclass, field
from http.client import HTTPException, HTTPSConnection
import json
import os
import re
from secrets import compare_digest
import ssl
from time import time
from uuid import uuid4

from remote_host import ANSWER_LIMIT, BODY_LIMIT, PROTOCOL, TOKEN, ProtocolError, private_ip
from runtime_contract import capability, validate

ID = re.compile(r"[a-f0-9]{32}")
REPLY_LIMIT = 6 * ANSWER_LIMIT + 4096


def protect(data, decrypt=False):
    if os.name != "nt":
        raise ValueError("持久配對需要 Windows 使用者憑證保護。")

    class Blob(ctypes.Structure):
        _fields_ = [("size", ctypes.c_uint32), ("data", ctypes.c_void_p)]

    source = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(source, ctypes.c_void_p))
    outgoing = Blob()
    api = ctypes.WinDLL("crypt32", use_last_error=True)
    function = api.CryptUnprotectData if decrypt else api.CryptProtectData
    function.argtypes = (ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(Blob))
    function.restype = ctypes.c_int
    release = ctypes.WinDLL("kernel32").LocalFree
    release.argtypes = (ctypes.c_void_p,)
    release.restype = ctypes.c_void_p
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ValueError("無法使用目前的 Windows 帳戶讀寫配對憑證。")
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.memset(outgoing.data, 0, outgoing.size)
        release(outgoing.data)
        ctypes.memset(source, 0, len(source))


def parse_invite(value):
    try:
        if not isinstance(value, str) or len(value) > 24576:
            raise ValueError()
        data = json.loads(base64.b64decode(value.strip(), altchars=b"-_", validate=True))
        if not isinstance(data, dict):
            raise ValueError()
        if type(data.get("version")) is not int or data["version"] != PROTOCOL:
            raise ProtocolError(426, "配對邀請的協定版本不相容。")
        if (not ID.fullmatch(data.get("id", "")) or not TOKEN.fullmatch(data.get("code", ""))
                or type(data.get("port")) is not int or not 1024 <= data["port"] <= 65535
                or not isinstance(data.get("certificate"), str) or len(data["certificate"]) > 16384):
            raise ValueError()
        private_ip(data.get("host"))
        return data
    except ProtocolError:
        raise
    except (ValueError, TypeError, RecursionError):
        raise ValueError("配對邀請無效。請從主機重新複製完整邀請。") from None


@dataclass
class RemoteClient:
    id: str
    host: str
    port: int
    label: str
    certificate: str = field(repr=False)
    token: str = field(default="", repr=False)
    record: dict | None = None
    error: str | None = None

    def __post_init__(self):
        private_ip(self.host)
        try:
            self.cert_der = ssl.PEM_cert_to_DER_cert(self.certificate)
            self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self.context.minimum_version = ssl.TLSVersion.TLSv1_2
            self.context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
            self.context.load_verify_locations(cadata=self.certificate)
        except (ssl.SSLError, ValueError):
            raise ValueError("主機公開憑證無效。請重新取得配對邀請。") from None

    @contextmanager
    def request(self, method, path, body=None, *, headers=None):
        headers = {"X-LocalLLM-Protocol": str(PROTOCOL), "Content-Type": "application/json", **(headers or {})}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if body is not None:
            body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            if len(body) > BODY_LIMIT:
                raise ValueError("這次對話資料過大。請開新對話或縮短訊息。")
        connection = HTTPSConnection(self.host, self.port, context=self.context, timeout=5)
        try:
            connection.connect()
            if not compare_digest(connection.sock.getpeercert(binary_form=True), self.cert_der):
                raise ssl.SSLCertVerificationError("unexpected certificate")
            connection.request(method, path, body, headers)
            with connection.getresponse() as response:
                if response.status not in (200, 202, 206):
                    errors = {
                        401: "配對已撤銷或失效。請在主機重新配對。",
                        403: "配對邀請無效或已使用。請在主機取得新邀請。",
                        404: "主機找不到模型或任務。請刷新模型清單或檢查主機是否重啟。",
                        409: "配對或任務發生衝突。請在主機檢查配對狀態。",
                        426: "遠端協定版本不相容。請確認兩台電腦的 Local LLM 版本。",
                        429: "主機佇列已滿。請等候其他工作完成。",
                        503: "主機引擎目前不可用。請在主機檢查模型、資源與引擎。",
                    }
                    message = errors.get(response.status, "主機拒絕這次請求。")
                    if response.status in (401, 426):
                        self.error = message
                    raise ProtocolError(response.status, message)
                yield response
        except ssl.SSLError:
            self.error = "TLS 驗證失敗。請確認主機位址和憑證，並重新取得邀請。"
            raise ValueError(self.error) from None
        except (OSError, HTTPException):
            raise ConnectionError("無法連線到運算主機。請檢查私人網路和主機服務。") from None
        finally:
            connection.close()

    def json(self, method, path, body=None):
        with self.request(method, path, body) as response:
            raw = response.read(REPLY_LIMIT + 1)
            if len(raw) > REPLY_LIMIT:
                raise ValueError("主機回傳資料過大。")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError("主機回應格式無效。")
            return result

    def discover(self):
        try:
            item = validate(self.json("GET", "/v1/capabilities"))
            if item["id"] != self.id or item["kind"] != "remote-host":
                raise ValueError("運算主機身分不符。請重新配對。")
            self.label, self.error, self.record = item["label"], None, {**item, "checked_at": int(time())}
        except (OSError, ValueError) as error:
            self.error = str(error)
            raise
        return self.summary()

    def capability(self):
        if self.record:
            return {**self.record, "connected": not self.error,
                    "health": "offline" if self.error else self.record["health"], "error": self.error or self.record["error"]}
        return capability(self.id, self.label, "remote-host", "Local LLM", connected=False, health="offline",
                          tasks=["chat"], formats=["GGUF"], network=True, destination=self.host, auth="paired-token-tls",
                          cost="no-api-fee", source="saved-pairing", checked_at=0, error=self.error)

    def summary(self):
        record = self.capability()
        return {"id": self.id, "kind": "paired", "label": self.label, "host": self.host, "port": self.port,
                "models": record["models"], "connected": record["connected"], "tasks": record["tasks"],
                "checked_at": record["checked_at"], "capability": record}

    def job(self, request):
        if not isinstance(request, str) or not ID.fullmatch(request):
            raise ValueError("遠端任務識別碼無效。")
        return self.json("GET", "/v1/jobs/" + request)

    def stream(self, model, messages, max_tokens, temperature, cancel, progress=lambda **_: None):
        request = uuid4().hex
        path = "/v1/jobs/" + request
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens,
                   "temperature": temperature, "request": request}
        delivered = ""
        progress(remote_request=request, message="正在送出主機任務…")
        try:
            for attempt in range(3):
                if cancel.is_set():
                    return
                try:
                    result = self.json("POST", "/v1/jobs", payload)
                    if result.get("id") != request:
                        raise ValueError("主機任務識別碼不符。")
                    with self.request("GET", path + "/events") as response:
                        if response.getheader("Content-Type") != "text/event-stream":
                            raise ValueError("主機未提供 SSE 串流。")
                        current = ""
                        while line := response.readline(REPLY_LIMIT + 1):
                            if cancel.is_set():
                                return
                            if not line.startswith(b"data: "):
                                continue
                            if len(line) > REPLY_LIMIT:
                                raise ValueError("主機串流資料過大。")
                            event = json.loads(line[6:])
                            state, delta = event.get("state"), event.get("delta", "")
                            if state not in {"queued", "running", "completed", "failed", "cancelled", "interrupted"} or not isinstance(delta, str):
                                raise ValueError("主機串流狀態無效。")
                            current += delta
                            if len(current) > ANSWER_LIMIT or not (delivered.startswith(current) or current.startswith(delivered)):
                                raise ValueError("重連後的主機回答與既有資料不符。")
                            if len(current) > len(delivered):
                                extra, delivered = current[len(delivered):], current
                                yield extra
                            if state == "completed":
                                if current != delivered:
                                    raise ValueError("主機傳回的結果不完整。")
                                self.error = None
                                return
                            if state not in ("queued", "running"):
                                raise ValueError(str(event.get("message") or "遠端任務已中斷。")[:350])
                            progress(message="在主機等候資源…" if state == "queued" else "主機正在生成回答…")
                    raise ConnectionError("遠端串流中斷。")
                except ConnectionError:
                    if attempt == 2:
                        self.error = "連線中斷。"
                        raise ConnectionError(f"遠端串流中斷。可在運算環境查詢任務 {request}。") from None
                    if cancel.wait(0.5):
                        return
        finally:
            if cancel.is_set():
                try:
                    self.json("POST", path + "/cancel")
                except (OSError, ValueError):
                    pass


class RemoteClients:
    def __init__(self, connect):
        self.connect = connect
        self.items = {}
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS remote_client_hosts(
                          id TEXT PRIMARY KEY, host TEXT, port INTEGER, label TEXT, certificate TEXT)""")
            db.execute("CREATE TABLE IF NOT EXISTS remote_client_secrets(id TEXT PRIMARY KEY, protected BLOB NOT NULL)")
            for row in db.execute("SELECT id,host,port,label,certificate,protected FROM remote_client_hosts JOIN remote_client_secrets USING(id)"):
                try:
                    token = protect(row[5], decrypt=True).decode("ascii")
                    if TOKEN.fullmatch(token):
                        self.items[row[0]] = RemoteClient(*row[:5], token)
                except (ValueError, UnicodeError):
                    continue

    def pair(self, value, label):
        data = parse_invite(value)
        if data["id"] not in self.items and len(self.items) >= 12:
            raise ValueError("配對已達上限。請先移除不使用的主機。")
        client = RemoteClient(data["id"], data["host"], data["port"], "已配對主機", data["certificate"])
        grant = client.json("POST", "/v1/pair", {"code": data["code"], "label": label})
        if grant.get("id") != client.id or not isinstance(grant.get("token"), str) or not TOKEN.fullmatch(grant["token"]):
            raise ValueError("主機配對回應無效。")
        client.token = grant["token"]
        client.discover()
        protected = protect(client.token.encode("ascii"))
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO remote_client_hosts VALUES(?,?,?,?,?)",
                       (client.id, client.host, client.port, client.label, client.certificate))
            db.execute("INSERT OR REPLACE INTO remote_client_secrets VALUES(?,?)", (client.id, protected))
        self.items[client.id] = client
        return client.summary()

    def get(self, id):
        if id not in self.items:
            raise ValueError("找不到這台已配對主機。")
        return self.items[id]

    def remove(self, id):
        client = self.get(id)
        revoked = False
        try:
            client.json("POST", "/v1/unpair")
            revoked = True
        except (OSError, ValueError):
            pass
        with self.connect() as db:
            db.execute("DELETE FROM remote_client_hosts WHERE id=?", (id,))
            db.execute("DELETE FROM remote_client_secrets WHERE id=?", (id,))
        self.items.pop(id, None)
        return {"revoked": revoked}

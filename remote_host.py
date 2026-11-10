"""Opt-in HTTPS inference service. Host management is available only over desktop IPC."""
import base64
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address, IPv4Network
import json
from pathlib import Path
import re
from secrets import compare_digest, token_urlsafe
import ssl
from threading import BoundedSemaphore, Lock, Thread, Timer
from time import monotonic, sleep
from uuid import uuid4

from runtime_contract import capability
from task_manager import ACTIVE

PROTOCOL = 1
BODY_LIMIT = 192 * 1024
ANSWER_LIMIT = 64 * 1024
PRIVATE = tuple(IPv4Network(network) for network in
                ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "127.0.0.0/8"))
JOB_PATH = re.compile(r"/v1/jobs/([a-f0-9]{32})(?:/(events|cancel))?")
TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


class ProtocolError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def private_ip(value):
    try:
        ip = IPv4Address(value)
        if isinstance(value, str) and any(ip in network for network in PRIVATE):
            return str(ip)
    except ValueError:
        pass
    raise ValueError("請輸入此電腦的私人 IPv4 位址。")


def digest(token):
    return sha256(token.encode("ascii")).hexdigest()


def invitation(data):
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).decode()


def inference_input(data):
    model, messages = data.get("model"), data.get("messages")
    budget, temperature = data.get("max_tokens"), data.get("temperature")
    if (not isinstance(model, str) or not 0 < len(model) <= 180 or not isinstance(messages, list)
            or not 1 <= len(messages) <= 13 or type(budget) is not int or not 64 <= budget <= 2048
            or type(temperature) not in (float, int) or not 0 <= temperature <= 2):
        raise ProtocolError(400, "模型或生成參數格式無效。")
    clean = []
    for item in messages:
        if (not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str) or not 0 < len(item["content"]) <= 12000):
            raise ProtocolError(400, "訊息格式無效。")
        clean.append({"role": item["role"], "content": item["content"]})
    if clean[-1]["role"] != "user":
        raise ProtocolError(400, "最後一則訊息須為使用者輸入。")
    return {"model": model, "messages": clean, "max_tokens": budget, "temperature": temperature}


class Host:
    def __init__(self, connect, scheduler, model_names, engine_status, resources):
        self.connect, self.scheduler = connect, scheduler
        self.model_names, self.engine_status, self.resources = model_names, engine_status, resources
        self.lock = Lock()
        self.server = None
        self.state = "stopped"
        self.error = None
        self.code = None
        self.jobs = {}

    @staticmethod
    def initialize(db):
        db.execute("CREATE TABLE IF NOT EXISTS remote_host_identity(id TEXT PRIMARY KEY)")
        db.execute("""CREATE TABLE IF NOT EXISTS remote_host_grants(
                      id TEXT PRIMARY KEY, label TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL)""")
        if not db.execute("SELECT 1 FROM remote_host_identity").fetchone():
            db.execute("INSERT INTO remote_host_identity VALUES(?)", (uuid4().hex,))

    def start(self, bind, port, label, cert, key):
        bind = private_ip(bind)
        if type(port) is not int or not 1024 <= port <= 65535 or not 0 < len(label.strip()) <= 100:
            raise ValueError("請輸入主機名稱及有效的 HTTPS 連接埠。")
        with self.lock:
            if self.server or self.state in ("starting", "stopping"):
                raise ValueError("請先停止目前的運算主機。")
            self.state, self.error = "starting", None
            try:
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                with Path(cert).open("r", encoding="ascii") as stream:
                    pem = stream.read(16385)
                if len(pem) > 16384 or "PRIVATE KEY" in pem:
                    raise ValueError("憑證須為獨立的公開 PEM 憑證檔。")
                leaf = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", pem, re.S)
                if not leaf:
                    raise ValueError("找不到 TLS 憑證。")
                self.certificate = leaf.group()
                ssl.PEM_cert_to_DER_cert(self.certificate)
                # Disallow OpenSSL's interactive password prompt in the IPC worker.
                context.load_cert_chain(cert, key, password=lambda: b"")
                with self.connect() as db:
                    self.id = db.execute("SELECT id FROM remote_host_identity").fetchone()[0]
                self.server = HostServer((bind, port), context, self)
            except (OSError, ValueError):
                self.state, self.error = "failed", "無法啟用 Host。請檢查私人位址、連接埠、PEM 憑證及私鑰。"
                raise ValueError(self.error) from None
            self.label, self.address, self.port = label.strip(), bind, port
            self.state = "ready"
            Thread(target=self.serve, args=(self.server,), daemon=True).start()
        return self.status()

    def serve(self, server):
        try:
            server.serve_forever(poll_interval=0.2)
        except OSError:
            with self.lock:
                if self.server is server:
                    self.state, self.error = "failed", "運算主機服務已中斷。請停止後重新啟用。"

    def stop(self):
        with self.lock:
            if not self.server:
                self.state, self.error = "stopped", None
                return
            server, self.code = self.server, None
            self.state = "stopping"
            for _, task, timer, _ in self.jobs.values():
                timer.cancel()
                self.cancel(task)
            self.jobs.clear()
        server.shutdown()
        server.server_close()
        with self.lock:
            self.server = None
            self.state, self.error = "stopped", None

    def status(self):
        with self.lock, self.connect() as db:
            peers = [{"id": key, "label": label} for key, label in
                     db.execute("SELECT id,label FROM remote_host_grants ORDER BY rowid")]
            active = self.state == "ready"
            result = {"state": self.state, "error": self.error, "peers": peers}
            if active:
                engines = self.engine_status()
                result.update(label=self.label, address=self.address, port=self.port, engine=engines,
                              models=self.model_names(), state="busy" if engines["busy"] else "ready")
            return result

    def issue(self):
        with self.lock:
            if self.state != "ready":
                raise ValueError("請先啟用運算主機。")
            code = token_urlsafe(32)
            self.code = (digest(code), monotonic() + 300)
            return invitation({"version": PROTOCOL, "host": self.address, "port": self.port, "id": self.id,
                               "certificate": self.certificate, "code": code})

    def pair(self, data):
        code, label = data.get("code"), data.get("label")
        if not isinstance(code, str) or not TOKEN.fullmatch(code) or not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise ProtocolError(403, "配對邀請無效或已失效。")
        with self.lock, self.connect() as db:
            if (self.state != "ready" or not self.code or monotonic() > self.code[1]
                    or not compare_digest(self.code[0], digest(code))):
                raise ProtocolError(403, "配對邀請無效或已失效。")
            if db.execute("SELECT count(*) FROM remote_host_grants").fetchone()[0] >= 12:
                raise ProtocolError(409, "主機配對數已達上限。請先撤銷不用的裝置。")
            peer, token = uuid4().hex, token_urlsafe(32)
            db.execute("INSERT INTO remote_host_grants VALUES(?,?,?)", (peer, label.strip(), digest(token)))
            self.code = None
            return {"token": token, "peer": peer, "id": self.id}

    def authenticate(self, authorization):
        token = authorization.removeprefix("Bearer ")
        if token == authorization or not TOKEN.fullmatch(token):
            raise ProtocolError(401, "請先配對這台運算主機。")
        with self.connect() as db:
            row = db.execute("SELECT id FROM remote_host_grants WHERE token_hash=?", (digest(token),)).fetchone()
        if not row:
            raise ProtocolError(401, "配對已撤銷或失效。")
        return row[0]

    def revoke(self, peer):
        with self.lock, self.connect() as db:
            db.execute("DELETE FROM remote_host_grants WHERE id=?", (peer,))
            for key in [key for key in self.jobs if key[0] == peer]:
                _, task, timer, _ = self.jobs.pop(key)
                timer.cancel()
                self.cancel(task)

    def capabilities(self):
        state = self.engine_status()
        return capability(self.id, self.label, "remote-host", "Local LLM", version=str(PROTOCOL), connected=True,
                          health="unhealthy" if not state["accepting"] else "busy" if state["busy"] else "ready",
                          tasks=["chat"], formats=["GGUF"], engines=["llama.cpp"] if state["installed"] else [],
                          models=self.model_names(), resources=self.resources(), network=True, destination=self.address,
                          auth="paired-token-tls", cost="no-api-fee", source="remote-host",
                          error=state["error"], features={"stream": True, "cancel": True, "load": False,
                                                         "unload": False, "download": False})

    def submit(self, peer, data):
        request = data.get("request")
        if not isinstance(request, str) or not re.fullmatch(r"[a-f0-9]{32}", request):
            raise ProtocolError(400, "缺少有效的任務識別碼。")
        payload = inference_input(data)
        signature = sha256(json.dumps(payload, sort_keys=True).encode()).digest()
        with self.lock, self.connect() as db:
            if self.state != "ready" or not db.execute("SELECT 1 FROM remote_host_grants WHERE id=?", (peer,)).fetchone():
                raise ProtocolError(401, "配對已撤銷或服務已停止。")
            expired = [key for key, entry in self.jobs.items() if monotonic() - entry[0] > 600]
            for key in expired:
                del self.jobs[key]
            previous = self.jobs.get((peer, request))
            if previous:
                if signature != previous[3]:
                    raise ProtocolError(409, "任務識別碼已被其他輸入使用。")
                return {"id": request}
            if not self.engine_status()["accepting"]:
                raise ProtocolError(503, "主機引擎目前不可用。請在主機檢查引擎和資源。")
            if payload["model"] not in self.model_names():
                raise ProtocolError(404, "主機沒有這個模型。請重新整理模型清單。")
            if len(self.jobs) >= 64 or sum(self.job_active(entry[1]) for entry in self.jobs.values()) >= 4:
                raise ProtocolError(429, "主機佇列已滿，請稍後重試。")
            try:
                task = self.scheduler.submit("remote-host-chat", payload)["id"]
            except ValueError:
                raise ProtocolError(429, "主機暫時無法接收新任務。") from None
            timer = Timer(240, self.cancel, (task,))
            timer.daemon = True
            self.jobs[(peer, request)] = (monotonic(), task, timer, signature)
            timer.start()
            return {"id": request}

    def cancel(self, task):
        try:
            self.scheduler.snapshot(task, cancel=True)
        except ValueError:
            pass

    def job_active(self, task):
        try:
            return self.scheduler.snapshot(task)["state"] in ACTIVE
        except ValueError:
            return False

    def job(self, peer, request, cancel=False):
        with self.lock:
            entry = self.jobs.get((peer, request))
            if not entry or monotonic() - entry[0] > 600:
                raise ProtocolError(404, "找不到可恢復的主機任務。")
            try:
                value = self.scheduler.snapshot(entry[1], cancel=cancel)
            except ValueError:
                raise ProtocolError(404, "找不到可恢復的主機任務。") from None
            if value["state"] not in ACTIVE:
                entry[2].cancel()
            return {key: value[key] for key in ("state", "answer", "message") if key in value}


class HostServer(ThreadingHTTPServer):
    request_queue_size = 8
    allow_reuse_address = False

    def __init__(self, address, context, host):
        self.context, self.host = context, host
        self.slots = BoundedSemaphore(12)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        try:
            private_ip(address[0])
        except ValueError:
            request.close()
            return
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            request.settimeout(8)
            with self.context.wrap_socket(request, server_side=True) as secure:
                self.finish_request(secure, address)
        except (OSError, ValueError):
            pass
        finally:
            request.close()
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_error(self, code, message=None, explain=None):
        self.reply({"error": "無效的 HTTP 請求。"}, code)

    def reply(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def body(self):
        size = self.headers.get("Content-Length", "")
        if (not re.fullmatch(r"[0-9]{1,7}", size) or not 0 < int(size) <= BODY_LIMIT
                or self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1):
            raise ProtocolError(413, "遠端請求過大或格式無效。")
        try:
            result = json.loads(self.rfile.read(int(size)))
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (ValueError, RecursionError):
            raise ProtocolError(400, "遠端請求格式無效。") from None

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        host = self.server.host
        try:
            if self.headers.get("X-LocalLLM-Protocol") != str(PROTOCOL):
                raise ProtocolError(426, "遠端協定版本不相容。")
            if self.command == "POST" and self.path == "/v1/pair":
                self.reply(host.pair(self.body()))
                return
            peer = host.authenticate(self.headers.get("Authorization", ""))
            if self.command == "GET" and self.path == "/v1/capabilities":
                self.reply(host.capabilities())
            elif self.command == "POST" and self.path == "/v1/unpair":
                host.revoke(peer)
                self.reply({"revoked": True})
            elif self.command == "POST" and self.path == "/v1/jobs":
                self.reply(host.submit(peer, self.body()), 202)
            elif match := JOB_PATH.fullmatch(self.path):
                request, action = match.groups()
                if self.command == "GET" and action == "events":
                    self.events(host, peer, request)
                elif (self.command, action) in (("GET", None), ("POST", "cancel")):
                    self.reply(host.job(peer, request, cancel=action == "cancel"))
                else:
                    raise ProtocolError(404, "找不到遠端服務。")
            else:
                raise ProtocolError(404, "找不到遠端服務。")
        except ProtocolError as error:
            self.reply({"error": str(error)}, error.status)
        except (ValueError, OSError):
            self.reply({"error": "主機服務暫時無法完成請求。"}, 503)

    def events(self, host, peer, request):
        state = host.job(peer, request)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        offset = 0
        while True:
            answer = state.pop("answer", "")
            state["delta"] = answer[offset:]
            offset = len(answer)
            raw = json.dumps(state, ensure_ascii=False).encode()
            try:
                self.wfile.write(b"data: " + raw + b"\n\n")
                if state["state"] not in ACTIVE:
                    return
                sleep(0.3)
                state = host.job(peer, request)
            except (OSError, ProtocolError):
                return

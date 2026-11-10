"""Development test worker with a controlled loopback llama.cpp protocol fixture."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from base64 import b64decode
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
from threading import Thread
from time import sleep
from time import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import desktop_worker
from runtime_provider import OpenAIProvider
from runtime_contract import capability
from test_remote_host import free_port, make_certificate
from test_remote_media import Response


class ModelProtocol(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, value, status=200):
        encoded = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self):
        size = int(self.headers["Content-Length"])
        if size > 1024 ** 2:
            self.send_json({"error": "fixture request too large"}, 413)
            return
        data = json.loads(self.rfile.read(size))
        if self.path == "/apply-template":
            self.send_json({"prompt": json.dumps(data["messages"])})
        elif self.path == "/tokenize":
            self.send_json({"tokens": list(range(64))})
        elif self.path == "/v1/chat/completions":
            if self.headers.get("Authorization") != "Bearer isolated-test-key":
                self.send_json({"error": "fixture authorization failed"}, 401)
                return
            self.completion(data)
        else:
            self.send_json({"error": "unknown fixture endpoint"}, 404)

    def completion(self, data):
        messages = data["messages"]
        user = json.loads(messages[1]["content"])
        if "common_task" in user:
            if user["role"] == "reviewer" and user["common_task"].startswith("FAIL"):
                self.send_json({"error": "controlled reviewer failure"}, 503)
                return
            if user["role"] == "reviewer":
                if not user["dependencies"]:
                    self.send_json({"error": "review missing draft"}, 422)
                    return
                if user["common_task"].startswith("CANCEL"):
                    sleep(1.5)
                output = "測試審查：補上可驗證依據，並說明尚存限制。"
            elif user["dependencies"]:
                output = "測試整合：已保留初稿與依賴資料，並整理下一步。"
            else:
                output = "測試初稿：先列出需求、風險及驗收步驟。"
            events = [{"content": output}]
        elif user["task"].startswith("FAIL"):
            events = [{"content": "Controlled invalid output"}]
        elif data.get("tools"):
            if messages[-1]["role"] == "tool":
                events = [{"content": "原生協定測試已取得本機工具資料。"}]
            else:
                events = [{"tool_calls": [{"index": 0, "id": "call_models", "type": "function",
                           "function": {"name": "models", "arguments": "{"}}]},
                          {"tool_calls": [{"index": 0, "function": {"arguments": "}"}}]}]
        elif not user["observations"]:
            events = [{"content": '{"type":"tool","tool":"models","arguments":{}}'}]
        else:
            events = [{"content": '{"type":"final","answer":"協定測試完成，已讀取並保存模型清單。"}'}]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for delta in events:
                raw = json.dumps({"choices": [{"index": 0, "delta": delta}]}, ensure_ascii=False)
                self.wfile.write(f"data: {raw}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
        except OSError:
            pass


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 0), ModelProtocol) as server:
        Thread(target=server.serve_forever, daemon=True).start()

        class FixtureDesktop(desktop_worker.Desktop):
            def __init__(self, data):
                super().__init__(data)
                self.local.endpoint = lambda: (server.server_port, "isolated-test-key")
                self.first_use = None

            def add_sample_work(self):
                name = "a12345678901.png"
                self.outputs.mkdir(exist_ok=True)
                actual = os.environ.get("LOCALLLM_BATCH3_REAL_IMAGE")
                if actual:
                    shutil.copyfile(actual, self.outputs / name)
                else:
                    (self.outputs / name).write_bytes(b64decode(
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh2sAAAAASUVORK5CYII="))
                with self.connect() as db:
                    db.execute("INSERT INTO creations VALUES(?,?)", (name, json.dumps({
                        "model": "Stable Diffusion 1.5", "workflow": "sd15-preview", "prompt": "雪中的雪松",
                        "options": {"seed": 417, "width": 256, "height": 256, "steps": 1},
                        "runtime": "local-comfyui", "status": "completed", "schema": 1,
                    })))

            def prepare(self, data, _cancel, _update):
                if self.first_use is not None:
                    self.active = (data["model"],"cpu",2048,{})
                return {}

            def perform(self, action, data, cancel, update):
                if self.first_use is not None:
                    if action == "engine-install":
                        self.first_use["engine"] = True
                        return {"message":"受控文字引擎已安裝"}
                    if action == "download":
                        if not self.first_use["retry"]:
                            self.first_use["retry"] = True
                            raise OSError("受控下載中斷")
                        self.first_use["model"] = desktop_worker.pinned_model(data["url"])["file"]
                        (self.models / self.first_use["model"]).touch()
                        return {"message":"受控模型已下載"}
                return super().perform(action,data,cancel,update)

            def rpc(self, op, data):
                if op == "fixture-remote-image":
                    id = "5"*32
                    image = {"installed":True,"state":"ready","workflows":["sd15"],"formats":["png"]}
                    record = capability(id,"受控圖片主機","remote-host","Local LLM",connected=True,health="ready",
                                        tasks=["chat","image"],formats=["GGUF","safetensors"],media={"image":image},
                                        destination="127.0.0.1",cost="no-api-fee")
                    png = b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jh2sAAAAASUVORK5CYII=")
                    digest = sha256(png).hexdigest()
                    submitted = {}

                    def accept(method, path, data):
                        assert method=="POST" and path=="/v1/jobs"
                        submitted[data["request"]] = data
                        return {"id":data["request"]}

                    def job(request):
                        return {"state":"completed","artifact":{"id":"a12345678901.png","kind":"image","workflow":"sd15",
                                "bytes":len(png),"sha256":digest,"options":{**submitted[request]["options"],"seed":417}}}

                    @contextmanager
                    def transfer(_method,_path,headers):
                        yield Response(png,200,{"ETag":f'"{digest}"',"Content-Length":str(len(png))})

                    self.remote_clients.items[id] = SimpleNamespace(
                        id=id,host="127.0.0.1",port=9443,label=record["label"],capability=lambda:record,
                        discover=lambda:None,job=job,json=accept,request=transfer,
                        summary=lambda:{"id":id,"label":record["label"],"kind":"paired","host":"127.0.0.1","port":9443,
                                        "models":[],"tasks":record["tasks"],"capability":record,"connected":True})
                    return id
                if op == "fixture-first-use":
                    self.first_use = {"engine":False,"model":None,"retry":False}
                    self.local.stream = lambda *_, **__: (part for part in ("首次對話已保存。",))
                    return True
                if op == "fixture-cloud":
                    provider = OpenAIProvider("7"*32, "cloud", "測試運算環境", "fixture.example", 443, "/v1",
                                              "fixture-not-a-secret", ["test-text"], True, int(time()))
                    provider.stream = lambda *_: (part for part in ("受控測試回答",))
                    provider.discover = lambda: None
                    self.providers.items[provider.id] = provider
                    return provider.id
                if op == "remote-host-networks":
                    return {**super().rpc(op, data), "addresses":["127.0.0.1"]}
                if op == "remote-host-start-auto":
                    return super().rpc(op, {**data, "port":free_port()})
                if op == "fixture-host-credentials":
                    certificate, key = make_certificate(self.data)
                    return {"certificate": str(certificate), "key": str(key), "port": free_port()}
                if op == "fixture-create-work":
                    self.add_sample_work()
                    return True
                result = super().rpc(op, data)
                if op == "info":
                    result["engine"] = True
                    if self.first_use is not None:
                        model = self.first_use["model"]
                        result["engine"] = self.first_use["engine"]
                        result["models"] = [model] if model else []
                        result["registry"]["models"] = [item for item in result["registry"]["models"] if item["id"]==model]
                return result

        desktop_worker.Desktop = FixtureDesktop
        try:
            desktop_worker.main()
        finally:
            server.shutdown()

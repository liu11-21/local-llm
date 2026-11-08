"""Own a local llama-server process and consume its OpenAI-style SSE stream."""
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
from tempfile import TemporaryFile
from threading import Event, Lock
import time

from downloads import check_gguf


class LocalEngine:
    def __init__(self):
        self.process = None
        self.log = None
        self.model = None
        self.port = None
        self.key = None
        self.lock = Lock()

    def running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    def start(self, executable, model, cancel=None):
        cancel = cancel or Event()
        executable = Path(executable).resolve(strict=True)
        model = Path(model).resolve(strict=True)
        check_gguf(model)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        key = secrets.token_urlsafe(24)
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith("LLAMA_")}
        env["LLAMA_API_KEY"] = key
        with self.lock:
            if cancel.is_set():
                raise RuntimeError("模型啟動已取消。")
            if self.process is not None:
                raise RuntimeError("請先停止目前的模型。")
            log = TemporaryFile()
            try:
                process = subprocess.Popen(
                    [str(executable), "--model", str(model), "--alias", "local-model",
                     "--host", "127.0.0.1", "--port", str(port), "--ctx-size", "2048",
                     "--parallel", "1", "--n-gpu-layers", "0"],
                    cwd=executable.parent, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                log.close()
                raise
            self.process, self.log = process, log
            self.port, self.key, self.model = port, key, model

        try:
            self.wait_until_ready(process, port, key, cancel)
        except Exception:
            self.stop()
            raise

    def wait_until_ready(self, process, port, key, cancel):
        deadline = time.monotonic() + 180
        while not cancel.is_set() and time.monotonic() < deadline:
            with self.lock:
                if self.process is not process:
                    raise RuntimeError("模型啟動已取消。")
                if process.poll() is not None:
                    self.log.seek(0, os.SEEK_END)
                    self.log.seek(max(0, self.log.tell() - 4096))
                    detail = self.log.read().decode("utf-8", errors="replace").strip()
                    raise RuntimeError(f"llama-server 結束（代碼 {process.returncode}）。\n{detail[-1800:]}")
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("GET", "/health")
                with connection.getresponse() as response:
                    ready = response.status == 200 and json.loads(response.read()).get("status") == "ok"
                if ready:
                    connection.request("GET", "/v1/models", headers={"Authorization": f"Bearer {key}"})
                    with connection.getresponse() as response:
                        if response.status == 200 and any(
                            model.get("id") == "local-model"
                            for model in json.loads(response.read()).get("data", [])
                        ):
                            return
            except (OSError, http.client.HTTPException, ValueError):
                pass
            finally:
                connection.close()
            cancel.wait(0.25)
        if cancel.is_set():
            raise RuntimeError("模型啟動已取消。")
        raise TimeoutError("模型在 180 秒內未就緒。")

    def stop(self):
        with self.lock:
            if self.process is None:
                return
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=3)
            finally:
                self.log.close()
                self.process = self.log = self.model = self.port = self.key = None

    def stream(self, messages):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError("請先啟動模型。")
            port, key = self.port, self.key
        body = json.dumps({
            "model": "local-model",
            "messages": messages,
            "stream": True,
            "max_tokens": 512,
            "temperature": 0.4,
        }, ensure_ascii=False).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
        try:
            connection.request("POST", "/v1/chat/completions", body, {
                "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            })
            with connection.getresponse() as response:
                if response.status != 200:
                    detail = response.read(2048).decode("utf-8", errors="replace")
                    raise RuntimeError(f"模型回應 HTTP {response.status}：{detail}")
                for line in response:
                    if not line.startswith(b"data:"):
                        continue
                    data = line[5:].strip()
                    if data == b"[DONE]":
                        return
                    event = json.loads(data)
                    if event.get("error"):
                        raise RuntimeError(str(event["error"]))
                    for choice in event.get("choices", []):
                        token = choice.get("delta", {}).get("content")
                        if isinstance(token, str) and token:
                            yield token
            raise ConnectionError("模型串流提前結束。")
        finally:
            connection.close()

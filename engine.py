"""Own a local llama-server process and consume its OpenAI-style SSE stream."""
from contextlib import closing
import http.client
import json
import os
from pathlib import Path
import secrets
import re
import socket
import subprocess
from tempfile import TemporaryFile
from threading import Event, Lock, Thread
import time

from downloads import check_gguf
from load_plan import engine_environment


class LocalEngine:
    def __init__(self):
        self.process = None
        self.log = None
        self.model = None
        self.port = None
        self.key = None
        self.lock = Lock()
        self.executable = None
        self.last_generation = {}
        self.thinking = False

    def running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    def safe_error(self,value):
        text=str(value.get('message','Runtime error') if isinstance(value,dict) else value)
        for source,replacement in ((self.key,'[已遮蔽金鑰]'),(str(self.model) if self.model else None,'[模型]'),(str(self.executable) if self.executable else None,'[Runtime]')):
            if source:text=text.replace(source,replacement)
        text=re.sub(r"[A-Za-z]:[\\/][^\s\"']+",'[檔案]',text)
        text=re.sub(r"Bearer\s+[^\s\"']+",'Bearer [已遮蔽金鑰]',text,flags=re.I)
        return text[:600]

    def resolve_model(self, model):
        model = Path(model).resolve(strict=True)
        check_gguf(model)
        return model

    def command(self, executable, args):
        return [str(executable), *args]

    def request_options(self, thinking, max_tokens):
        if thinking:
            raise ValueError("THINKING_UNSUPPORTED · 此引擎尚未驗證 Thinking 能力。")
        return {}

    def start(self, executable, model, cancel=None, plan=None, *, context=2048, native_tools=False, on_process=None, threads=None):
        cancel = cancel or Event()
        executable = Path(executable).resolve(strict=True)
        model = self.resolve_model(model)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        key = secrets.token_urlsafe(24)
        env = engine_environment()
        env["LLAMA_API_KEY"] = key
        placement = ["--n-gpu-layers", str(plan.layers if plan else 0)]
        if plan:
            placement.extend(plan.mmap_args)
            if plan.device:
                placement.extend(("--device", plan.device, "--split-mode", "none"))
        with self.lock:
            if cancel.is_set():
                raise RuntimeError("模型啟動已取消。")
            if self.process is not None:
                raise RuntimeError("請先停止目前的模型。")
            log = TemporaryFile()
            try:
                process = subprocess.Popen(
                    self.command(executable, ["--model", str(model), "--alias", "local-model",
                     "--host", "127.0.0.1", "--port", str(port), "--ctx-size", str(context),
                     "--parallel", "1", *(["--threads",str(threads)] if threads else []), *(["--jinja"] if native_tools else []), *placement]),
                    cwd=executable.parent, env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                log.close()
                raise
            self.process, self.log = process, log
            self.port, self.key, self.model = port, key, model
            self.executable = executable

        try:
            if on_process:
                on_process(process)
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
                    detail = self.log.read().decode("utf-8", errors="replace").replace(key, "[已遮蔽金鑰]").replace(str(self.model), "[模型]").replace(str(self.executable), "[Runtime]").strip()
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
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    else:
                        self.process.terminate()
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait(timeout=3)
            finally:
                self.log.close()
                self.process = self.log = self.model = self.port = self.key = None

    def endpoint(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                raise RuntimeError("請先啟動模型。")
            return self.port, self.key

    def health_probe(self):
        port, key = self.endpoint()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("GET", "/health")
            with connection.getresponse() as response:
                if response.status != 200 or json.loads(response.read(64 * 1024)).get("status") != "ok":
                    return False
            connection.request("GET", "/v1/models", headers={"Authorization": f"Bearer {key}"})
            with connection.getresponse() as response:
                return response.status == 200 and any(item.get("id") == "local-model"
                    for item in json.loads(response.read(64 * 1024)).get("data", []))
        except (http.client.HTTPException, TypeError, AttributeError):
            return False
        finally:
            connection.close()

    def template_options(self):
        return {}

    def prompt_tokens(self, messages, *, tools=None):
        port, key = self.endpoint()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            def request(path, data):
                connection.request("POST", path, json.dumps(data).encode(), headers)
                with connection.getresponse() as response:
                    body = response.read()
                    if response.status != 200:
                        raise RuntimeError(f"本機模型無法檢查輸入長度（HTTP {response.status}）。")
                    return json.loads(body)
            prompt = request("/apply-template", {"messages": messages, **self.template_options(), **({"tools": tools} if tools else {})})["prompt"]
            return len(request("/tokenize", {"content": prompt, "add_special": True})["tokens"])
        finally:
            connection.close()

    def stream(self, messages, *, max_tokens=512, temperature=0.4, cancel=None, thinking=None, on_event=None):
        self.last_generation = {"reasoning": "", "usage": {}, "timings": {}}
        answer = ""
        with closing(self.completion_events(messages, max_tokens=max_tokens, temperature=temperature,
                                           cancel=cancel, thinking=thinking)) as events:
            for event in events:
                if event.get("usage"): self.last_generation["usage"] = event["usage"]
                if event.get("timings"): self.last_generation["timings"] = event["timings"]
                for choice in event.get("choices", []):
                    delta = choice.get("delta", {})
                    thought = delta.get("reasoning_content")
                    if isinstance(thought, str): self.last_generation["reasoning"] += thought
                    token = delta.get("content")
                    if isinstance(token, str) and token:
                        answer += token
                        yield token
                    if choice.get("finish_reason"): self.last_generation["finish_reason"] = choice["finish_reason"]
                if on_event: on_event(self.last_generation)
        if not (cancel and cancel.is_set()) and not answer.strip():
            raise RuntimeError("EMPTY_ANSWER · 模型只有思考或沒有正式回答，請關閉 Thinking 或提高回答預算。")

    def completion_events(self, messages, *, max_tokens=512, temperature=0.4, cancel=None, tools=None, benchmark=False, thinking=None):
        port, key = self.endpoint()
        body = json.dumps({
            "model": "local-model",
            "messages": messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **self.request_options(self.thinking if thinking is None else thinking, max_tokens),
            "stream_options": {"include_usage": True},
            **({"cache_prompt":False,"ignore_eos":True,"seed":0,"stream_options":{"include_usage":True}} if benchmark else {}),
            **({"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False} if tools else {}),
        }, ensure_ascii=False).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=180)
        finished = Event()
        def interrupt():
            while not finished.wait(0.1):
                if cancel.is_set():
                    sock = connection.sock
                    if sock is not None:
                        try:
                            sock.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                        return
        if cancel is not None:
            Thread(target=interrupt, daemon=True).start()
        try:
            connection.request("POST", "/v1/chat/completions", body, {
                "Authorization": f"Bearer {key}", "Content-Type": "application/json",
            })
            with connection.getresponse() as response:
                if response.status != 200:
                    detail = response.read(2048).decode("utf-8", errors="replace")
                    try: parsed=json.loads(detail);detail=parsed.get('error',parsed)
                    except ValueError:pass
                    raise RuntimeError(f"模型回應 HTTP {response.status}：{self.safe_error(detail)}")
                for line in response:
                    if cancel is not None and cancel.is_set():
                        return
                    if len(line) > 1024 * 1024:
                        raise ValueError("Runtime SSE event exceeds limit")
                    if not line.startswith(b"data:"):
                        continue
                    data = line[5:].strip()
                    if data == b"[DONE]":
                        return
                    event = json.loads(data)
                    if event.get("error"):
                        raise RuntimeError(self.safe_error(event["error"]))
                    yield event
            raise ConnectionError("模型串流提前結束。")
        finally:
            finished.set()
            connection.close()

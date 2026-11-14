"""llama.app dispatcher adapter; keeps the legacy server adapter independent."""
from functools import lru_cache
import re
import subprocess
from pathlib import Path
import http.client
import json
from engine import LocalEngine
from load_plan import engine_environment, DEVICE_LINE


@lru_cache(maxsize=8)
def profile(path, stamp):
    env=engine_environment();flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
    def run(args):
        result=subprocess.run([str(path),*args],capture_output=True,timeout=15,env=env,creationflags=flags)
        if result.returncode:raise ValueError("RUNTIME_CLI · llama.app CLI 探測失敗。")
        return (result.stdout+result.stderr).decode("utf-8",errors="replace")
    version=run(["version"]);help_text=run(["serve","--help"])
    required=("--host","--port","--model","--alias","--cors-origins")
    if any(flag not in help_text for flag in required):raise ValueError("RUNTIME_CAPABILITY · 此版本尚未驗證必要的安全啟動參數。")
    try:devices_text=run(["serve","--list-devices"])
    except (ValueError,subprocess.TimeoutExpired):devices_text=''
    devices=[{'id':name,'name':adapter,'reported_total_mib':int(total.replace(',','')),
              'reported_free_mib':int(free.replace(',','')),'backend':'Vulkan' if name.startswith('Vulkan') else 'CUDA',
              'available':name.startswith('Vulkan'),'memory_type':'shared-or-unified' if any(part in adapter.lower() for part in ('iris','uhd','intel graphics','intel(r) graphics')) else 'needs-physical-mapping'}
             for name,adapter,total,free in DEVICE_LINE.findall(devices_text)]
    return {"version":version[:500],"help":help_text,"supports_cors":True,"devices":devices}


def engine_profile(path):
    path=Path(path);return profile(str(path),path.stat().st_mtime_ns)


class LlamaAppEngine(LocalEngine):
    def __init__(self):
        super().__init__();self.supports_thinking=False;self.properties={}

    def resolve_model(self,model):
        if isinstance(model,str) and model.startswith("hf://"):
            if not re.fullmatch(r"hf://[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?",model):
                raise ValueError("HF_SOURCE · 請使用 owner/repository:quantization。")
            return model
        return super().resolve_model(model)

    def command(self,executable,args):
        caps=engine_profile(executable);self.supports_thinking=False
        if str(args[1]).startswith("hf://"):args=["-hf",str(args[1])[5:],*args[2:]]
        security=["--cors-origins","localhost"]
        for flag in ("--no-cors-credentials","--no-webui","--no-agent"):
            if flag in caps["help"]:security.append(flag)
        return [str(executable),"serve",*args,*security]

    def wait_until_ready(self,process,port,key,cancel):
        super().wait_until_ready(process,port,key,cancel)
        connection=http.client.HTTPConnection("127.0.0.1",port,timeout=3)
        try:
            connection.request("GET","/props",headers={"Authorization":"Bearer "+key})
            with connection.getresponse() as response:
                if response.status==200:
                    self.properties=json.loads(response.read(1024*1024))
                    template=str(self.properties.get("chat_template",""))
                    caps=self.properties.get("chat_template_caps") or {}
                    self.supports_thinking=self.supports_thinking or caps.get("supports_thinking") is True or "enable_thinking" in template
        except (OSError,ValueError,http.client.HTTPException):pass
        finally:connection.close()

    def template_options(self):
        return {"chat_template_kwargs":{"enable_thinking":bool(self.thinking)}} if self.supports_thinking else {}

    def request_options(self,thinking,max_tokens):
        if thinking and not self.supports_thinking:raise ValueError("THINKING_UNSUPPORTED · 模型範本未宣告 Thinking，未套用 reasoning_effort。")
        if not self.supports_thinking:return {}
        options={"chat_template_kwargs":{"enable_thinking":bool(thinking)},"reasoning_format":"deepseek"}
        if not thinking:options['reasoning_effort']='none'
        else:
            # Pinned b12360 server-common.cpp consumes reasoning_budget_tokens, not reasoning_budget.
            options['reasoning_budget_tokens']=min(256,max_tokens//3)
            caps=self.properties.get('chat_template_caps') or {}
            levels=caps.get('reasoning_effort_levels') or []
            if caps.get('supports_reasoning_effort') and levels:
                options['reasoning_effort']=levels[min(1,len(levels)-1)]
        return options


def engine_for(executable):
    return LlamaAppEngine() if Path(executable).name.lower() in ("llama.exe","llama") else LocalEngine()

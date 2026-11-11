"""Bound text interface for Agent/Team; grants remain at their existing boundaries."""
from contextlib import closing


class TextBackend:
    def __init__(self,app,runtime,model,device="CPU",target=None,update=lambda **_:None):
        self.app,self.runtime,self.model,self.device,self.target,self.update=app,runtime,model,device,target,update
        self.context_limit=1024 if runtime=="openvino" else 4096

    def prompt_tokens(self,messages,**_):
        # A conservative byte bound for admission only, never a token metric.
        return sum(len(item.get("content","").encode("utf-8")) for item in messages)+(64 if self.runtime=="openvino" else 256)

    def stream(self,messages,*,max_tokens=384,temperature=.2,cancel=None,**_):
        if self.prompt_tokens(messages)+max_tokens>self.context_limit:
            raise ValueError("CONTEXT_LIMIT · 遠端或 OpenVINO 上下文採保守位元組上界，請縮短任務或工具資料。")
        if self.runtime=="openvino":
            fragments=[]
            self.app.openvino.infer(self.model,self.device,cancel,lambda event:fragments.append(event["text"]) if event.get("event")=="token" else None,
                messages=messages,max_tokens=min(max_tokens,512),
                **({"threads":self.target.threads,"memory":self.target.memory} if self.target else {}))
            yield from fragments
        else:
            client=self.app.remote_clients.items.get(self.runtime)
            provider=client or self.app.providers.get(self.runtime)
            stream=client.stream(self.model,messages,max_tokens,temperature,cancel,self.update) if client else provider.stream(self.model,messages,max_tokens,temperature,cancel)
            with closing(stream):
                for fragment in stream:
                    yield fragment.replace(getattr(provider,"token","\0"),"[已遮蔽金鑰]")

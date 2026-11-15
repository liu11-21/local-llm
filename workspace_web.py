"""Same-origin loopback ASGI transport for the shared Workspace core.

No framework model validation/native extensions are needed: the core validates RPC
contracts. Uvicorn is deliberately run with asyncio+h11, no standard/native extras.
"""
import argparse
import asyncio
from http.cookies import SimpleCookie
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import socket
import time
from urllib.parse import unquote
import webbrowser

from workspace_core import WorkspaceApplication
from workspace_version import build_info
from download_recovery import exclusive,owned

ROOT=Path(__file__).resolve().parent
BODY_LIMIT=256*1024
COOKIE='localllm_web_session'
ACTIVE={'running','queued','paused'}
JOB=re.compile(r'[a-f0-9]{32}')
CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"


class HTTPError(Exception):
    def __init__(self,status,message):self.status=status;self.message=message


class WebWorkspace:
    def __init__(self,application,port,static=None,*,idle_seconds=1800):
        self.application=application;self.port=port;self.origin=f'http://127.0.0.1:{port}'
        self.static=Path(static or ROOT/'desktop/dist').resolve()
        self.bootstrap=secrets.token_urlsafe(32);self.sessions={};self.stopping=False
        self.last_seen=time.monotonic();self.idle_seconds=idle_seconds;self.stop_callback=lambda:None
        self.capacity=asyncio.Semaphore(32);self.streams=0
        self.assets={('/'+p.relative_to(self.static).as_posix()):p for p in self.static.rglob('*')
                     if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(self.static)}
        self.assets['/']=self.static/'index.html'

    def headers(self,scope):
        pairs=scope.get('headers',[]);result={}
        for raw_key,raw_value in pairs:
            key=raw_key.decode('latin1').lower()
            if key in result and key in ('host','origin','content-length','cookie','x-workspace-csrf','x-workspace-bootstrap'):
                raise HTTPError(400,'重複的安全標頭。')
            result[key]=raw_value.decode('latin1')
        if result.get('host')!=f'127.0.0.1:{self.port}':raise HTTPError(403,'Host 不符。')
        if scope.get('client',('127.0.0.1',0))[0]!='127.0.0.1':raise HTTPError(403,'僅允許本機。')
        if result.get('origin') not in (None,self.origin):raise HTTPError(403,'Origin 不符。')
        if result.get('sec-fetch-site') not in (None,'same-origin','none'):raise HTTPError(403,'拒絕跨來源請求。')
        if scope.get('method') not in ('GET','HEAD') and result.get('origin')!=self.origin:
            raise HTTPError(403,'寫入操作需要同源 Origin。')
        return result

    def session(self,headers,*,mutating=False):
        cookies=SimpleCookie()
        try:cookies.load(headers.get('cookie',''))
        except Exception:raise HTTPError(401,'請從啟動器重新開啟工作台。') from None
        token=cookies.get(COOKIE);value=self.sessions.get(token.value if token else '')
        if not value or value['expires']<time.monotonic():raise HTTPError(401,'工作階段已過期，請從啟動器重新開啟。')
        if mutating and not hmac.compare_digest(headers.get('x-workspace-csrf',''),value['csrf']):raise HTTPError(403,'CSRF 驗證失敗。')
        self.last_seen=time.monotonic()
        return value

    async def body(self,scope,receive,limit=BODY_LIMIT):
        chunks=[];size=0
        while True:
            message=await asyncio.wait_for(receive(),30)
            if message['type']=='http.disconnect':raise HTTPError(400,'連線已中斷。')
            block=message.get('body',b'');size+=len(block)
            if size>limit:raise HTTPError(413,'請求超過限制。')
            chunks.append(block)
            if not message.get('more_body'):return b''.join(chunks)

    async def json_body(self,scope,receive,headers):
        if headers.get('content-type','').split(';')[0].strip()!='application/json':raise HTTPError(415,'需要 JSON。')
        try:value=json.loads(await self.body(scope,receive))
        except (ValueError,UnicodeError,RecursionError):raise HTTPError(400,'JSON 格式無效。') from None
        if not isinstance(value,dict):raise HTTPError(400,'需要 JSON 物件。')
        return value

    async def send(self,send,status,value,*,content_type='application/json; charset=utf-8',extra=()):
        body=json.dumps(value,ensure_ascii=False).encode() if content_type.startswith('application/json') else value
        headers=[(b'content-type',content_type.encode()),(b'content-length',str(len(body)).encode()),
            (b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer'),
            (b'cross-origin-resource-policy',b'same-origin'),(b'content-security-policy',CSP.encode()),*extra]
        await send({'type':'http.response.start','status':status,'headers':headers})
        await send({'type':'http.response.body','body':body})

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return
        try:
            headers=self.headers(scope)
            async with self.capacity:await self.route(scope,receive,send,headers)
        except HTTPError as error:await self.send(send,error.status,{'ok':False,'error':error.message})
        except (TimeoutError,asyncio.TimeoutError):await self.send(send,408,{'ok':False,'error':'請求逾時；未自動重送工作。'})
        except (BrokenPipeError,ConnectionError,asyncio.CancelledError):return
        except Exception:
            # Neither credentials nor arbitrary exception text reaches HTTP/access logs.
            await self.send(send,500,{'ok':False,'error':'本機服務發生錯誤；請查看診斷，不要重複提交工作。'})

    async def route(self,scope,receive,send,headers):
        path=scope['path'];method=scope['method']
        if '%' in path or '\\' in path or '\x00' in path or '..' in path.split('/'):raise HTTPError(404,'找不到項目。')
        if path=='/api/session' and method=='POST':
            if not hmac.compare_digest(headers.get('x-workspace-bootstrap',''),self.bootstrap):raise HTTPError(401,'請使用啟動器開啟工作台。')
            await self.json_body(scope,receive,headers)
            now=time.monotonic();self.sessions={k:v for k,v in self.sessions.items() if v['expires']>now}
            if len(self.sessions)>=64:raise HTTPError(429,'工作階段過多。')
            token=secrets.token_urlsafe(32);session={'csrf':secrets.token_urlsafe(32),'expires':now+8*3600}
            self.sessions[token]=session;self.last_seen=now
            await self.send(send,200,{'ok':True,'value':{'csrf':session['csrf'],'build':build_info()}},
                extra=[(b'set-cookie',f'{COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'.encode())]);return
        if path.startswith('/api/'):
            session=self.session(headers,mutating=method not in ('GET','HEAD'))
            if path=='/api/session' and method=='GET':
                await self.send(send,200,{'ok':True,'value':{'csrf':session['csrf'],'build':build_info(),
                    'idle_seconds':self.idle_seconds,'state':'stopping' if self.stopping else 'ready'}});return
            if path=='/api/rpc' and method=='POST':
                body=await self.json_body(scope,receive,headers)
                op=body.get('op');data=body.get('data')
                if not isinstance(op,str) or len(op)>64 or not isinstance(data,dict):raise HTTPError(400,'RPC 格式無效。')
                result=await asyncio.to_thread(self.application.response,op,data)
                await self.send(send,200,result);return
            if path=='/api/shutdown' and method=='POST':
                body=await self.json_body(scope,receive,headers)
                if body.get('confirmed') is not True:raise HTTPError(400,'需要確認停止服務。')
                self.stopping=True;await self.send(send,200,{'ok':True,'value':None});self.stop_callback();return
            match=re.fullmatch(r'/api/jobs/([a-f0-9]{32})/events',path)
            if match and method=='GET':
                await self.events(match[1],session,receive,send);return
            if path.startswith('/api/works/') and method in ('GET','HEAD'):
                from registries import work_file
                try:file=work_file(self.application.service.outputs,path.removeprefix('/api/works/'))
                except (ValueError,OSError):raise HTTPError(404,'找不到作品。') from None
                await self.file(file,scope,send,headers);return
            raise HTTPError(404,'未支援的 API。')
        if method not in ('GET','HEAD'):raise HTTPError(405,'不支援此方法。')
        file=self.assets.get(path)
        if not file or not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(self.static):raise HTTPError(404,'找不到前端檔案，請使用完整 Web ZIP。')
        data=await asyncio.to_thread(file.read_bytes)
        await self.send(send,200,b'' if method=='HEAD' else data,content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream')

    async def file(self,file,scope,send,headers):
        if not owned(file):raise HTTPError(404,'檔案路徑無效。')
        size=file.stat().st_size;start=0;end=size-1;status=200
        if headers.get('range'):
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',headers['range'])
            if not match:raise HTTPError(416,'不支援的範圍。')
            start=int(match[1]);end=min(int(match[2]) if match[2] else end,end)
            if start>end:raise HTTPError(416,'範圍無效。')
            status=206
        response=[(b'content-type',(mimetypes.guess_type(file.name)[0] or 'application/octet-stream').encode()),
            (b'content-length',str(end-start+1).encode()),(b'cache-control',b'no-store'),(b'accept-ranges',b'bytes'),
            (b'x-content-type-options',b'nosniff'),(b'cross-origin-resource-policy',b'same-origin')]
        if status==206:response.append((b'content-range',f'bytes {start}-{end}/{size}'.encode()))
        await send({'type':'http.response.start','status':status,'headers':response})
        with file.open('rb') as stream:
            stream.seek(start);remaining=end-start+1 if scope['method']!='HEAD' else 0
            while remaining:
                chunk=await asyncio.to_thread(stream.read,min(256*1024,remaining));remaining-=len(chunk)
                if not chunk:break
                await send({'type':'http.response.body','body':chunk,'more_body':True})
        await send({'type':'http.response.body','body':b''})

    async def events(self,job,session,receive,send):
        if self.streams>=16:raise HTTPError(429,'串流連線過多。')
        initial=await asyncio.to_thread(self.application.response,'job',{'id':job})
        if not initial['ok']:raise HTTPError(404,'找不到工作。')
        self.streams+=1
        await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'text/event-stream'),
            (b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),(b'cross-origin-resource-policy',b'same-origin')]})
        async def disconnected():
            while (await receive())['type']!='http.disconnect':pass
        disconnect=asyncio.create_task(disconnected());deadline=time.monotonic()+900;last=None
        try:
            while time.monotonic()<min(deadline,session['expires']) and not self.stopping:
                if disconnect.done():break
                self.last_seen=time.monotonic()
                snapshot=await asyncio.to_thread(self.application.response,'job',{'id':job})
                encoded=json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))
                if encoded!=last:
                    await send({'type':'http.response.body','body':('event: snapshot\ndata: '+encoded+'\n\n').encode(),'more_body':True});last=encoded
                else:await send({'type':'http.response.body','body':b': keepalive\n\n','more_body':True})
                if not snapshot['ok'] or snapshot['value']['state'] not in ACTIVE:break
                await asyncio.sleep(.2)
        finally:
            disconnect.cancel();self.streams-=1
        await send({'type':'http.response.body','body':b''})

    async def monitor(self):
        while not self.stopping:
            await asyncio.sleep(2)
            idle=time.monotonic()-self.last_seen
            if idle>self.idle_seconds:
                self.stopping=True;self.stop_callback();return
            if idle>90:
                with self.application.lock:
                    service=self.application.service
                    if not any(t['state'] in ACTIVE for t in service.scheduler.list()):
                        await asyncio.to_thread(service.stop_local)
                        await asyncio.to_thread(service.comfy.stop)


async def serve(directory,port=8766,static=None,*,browser=True,idle_seconds=1800,on_ready=None):
    import uvicorn
    application=WorkspaceApplication(directory,web=True)
    app=WebWorkspace(application,port,static,idle_seconds=idle_seconds)
    config=uvicorn.Config(app,host='127.0.0.1',port=port,loop='asyncio',http='h11',ws='none',lifespan='off',
        access_log=False,log_level='warning',proxy_headers=False,server_header=False,timeout_keep_alive=5,
        timeout_graceful_shutdown=8,limit_concurrency=48,h11_max_incomplete_event_size=16384)
    server=uvicorn.Server(config);app.stop_callback=lambda:setattr(server,'should_exit',True)
    monitor=asyncio.create_task(app.monitor())
    async def ready():
        while not server.started and not server.should_exit:await asyncio.sleep(.05)
        if not server.started:return
        url=app.origin+'/#bootstrap='+app.bootstrap
        if on_ready:on_ready(app,url)
        if browser:await asyncio.to_thread(webbrowser.open,url)
    opener=asyncio.create_task(ready())
    try:await server.serve()
    finally:
        app.stopping=True;opener.cancel();monitor.cancel()
        await asyncio.to_thread(application.close)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'LocalLLM')
    parser.add_argument('--port',type=int,default=8766);parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('連接埠無效。')
    args.data.mkdir(parents=True,exist_ok=True)
    with exclusive(args.data/'.workspace.lock'):
        asyncio.run(serve(args.data.resolve(),args.port,browser=not args.no_browser))


if __name__=='__main__':main()

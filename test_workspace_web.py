import asyncio
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workspace_core import WorkspaceApplication
from workspace_web import WebWorkspace,COOKIE


class WebBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.core=WorkspaceApplication(self.root,web=True)
        static=self.root/'ui';static.mkdir();(static/'index.html').write_text('<html>safe</html>')
        self.app=WebWorkspace(self.core,18767,static);self.cookie='';self.csrf=''

    async def asyncTearDown(self):self.app.uploads.close();self.core.close();self.temp.cleanup()

    async def call(self,path,body=None,*,method=None,headers=None,raw=None,extra=()):
        method=method or ('GET' if body is None and raw is None else 'POST')
        head={'host':'127.0.0.1:18767','origin':self.app.origin,'content-type':'application/json',
              'cookie':self.cookie,'x-workspace-csrf':self.csrf,**(headers or {})}
        scope={'type':'http','method':method,'path':path,'headers':[(k.encode(),v.encode()) for k,v in head.items() if v is not None]+list(extra),'client':('127.0.0.1',1234)}
        payload=raw if raw is not None else json.dumps(body).encode() if body is not None else b''
        messages=[{'type':'http.request','body':payload,'more_body':False}]
        async def receive():
            if messages:return messages.pop(0)
            return {'type':'http.disconnect'}
        result=[]
        async def send(message):result.append(message)
        await self.app(scope,receive,send)
        content=b''.join(m.get('body',b'') for m in result)
        return result[0]['status'],dict(result[0]['headers']),content

    async def login(self):
        status,headers,content=await self.call('/api/session',{},headers={'x-workspace-bootstrap':self.app.bootstrap})
        self.assertEqual(status,200)
        self.cookie=headers[b'set-cookie'].decode().split(';')[0]
        self.csrf=json.loads(content)['value']['csrf']
        return headers

    async def test_bootstrap_origin_host_dns_rebinding_and_duplicate_headers(self):
        for headers in ({'origin':'https://evil.test'},{'origin':None},{'host':'evil.test:18767'},
                        {'host':'localhost:18767'},{'sec-fetch-site':'cross-site'},
                        {'host':'evil.test','x-forwarded-host':'127.0.0.1:18767'}):
            with self.subTest(headers=headers):
                status,_,_=await self.call('/api/session',{},headers={'x-workspace-bootstrap':self.app.bootstrap,**headers})
                self.assertEqual(status,403)
        status,_,_=await self.call('/api/session',{},headers={'x-workspace-bootstrap':self.app.bootstrap},extra=[(b'host',b'127.0.0.1:18767')])
        self.assertEqual(status,400)

    async def test_missing_auth_and_csrf_fail_before_business_operation(self):
        self.assertEqual((await self.call('/api/rpc',{'op':'run','data':{}}))[0],401)
        headers=await self.login()
        self.assertIn(b'HttpOnly',headers[b'set-cookie']);self.assertIn(b'SameSite=Strict',headers[b'set-cookie'])
        self.assertEqual((await self.call('/api/rpc',{'op':'run','data':{}},headers={'x-workspace-csrf':'wrong'}))[0],403)
        status,_,body=await self.call('/api/rpc',{'op':'run','data':{'action':'engine-install'}})
        self.assertEqual(status,200);self.assertFalse(json.loads(body)['ok'])
        self.assertEqual(self.core.service.scheduler.list(),[])

    async def test_size_json_content_type_and_method_limits(self):
        await self.login()
        self.assertEqual((await self.call('/api/rpc',raw=b'{'*270000))[0],413)
        self.assertEqual((await self.call('/api/rpc',raw=b'{'))[0],400)
        self.assertEqual((await self.call('/api/rpc',{},headers={'content-type':'text/plain'}))[0],415)
        self.assertEqual((await self.call('/api/rpc',method='GET'))[0],404)
        self.assertEqual((await self.call('/api/session',{},headers={'x-workspace-bootstrap':'wrong'}))[0],401)

    async def test_static_path_traversal_cors_and_frame_protection(self):
        status,headers,body=await self.call('/')
        self.assertEqual(status,200);self.assertEqual(body,b'<html>safe</html>')
        self.assertIn(b"frame-ancestors 'none'",headers[b'content-security-policy'])
        self.assertNotIn(b'access-control-allow-origin',headers)
        self.assertEqual(headers[b'cache-control'],b'no-store')
        for path in ('/../workspace.sqlite3','/%2e%2e/secret','/api/works/../secret','/file:C:/secret','/\\secret'):
            with self.subTest(path=path):self.assertIn((await self.call(path))[0],(401,404))

    async def test_real_sqlite_shared_core_and_legacy_runtime_gate(self):
        await self.login()
        status,_,body=await self.call('/api/rpc',{'op':'build-info','data':{}})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['value']['version'],'0.9.0')
        status,_,body=await self.call('/api/rpc',{'op':'runtime-select','data':{'kind':'legacy','confirmed':True}})
        self.assertFalse(json.loads(body)['ok'])
        with self.core.service.connect() as db:
            db.execute('INSERT INTO chats(id,title) VALUES(?,?)',('c'*32,'shared core'))
            self.assertEqual(db.execute('SELECT minimum_reader FROM workspace_storage').fetchone()[0],'0.8.0')
        _,_,body=await self.call('/api/rpc',{'op':'chats','data':{}})
        self.assertEqual(json.loads(body)['value'][0][1],'shared core')

    async def test_runtime_candidate_http_contract_and_validation_gate(self):
        from unittest.mock import patch
        await self.login()
        missing=str(self.root/'missing/llama.exe')
        _,_,body=await self.call('/api/rpc',{'op':'runtime-validate','data':{'path':missing}})
        result=json.loads(body);self.assertTrue(result['ok'])
        row=result['value']['candidates'][0]
        self.assertEqual(row['input_path'],missing);self.assertEqual(row['reason']['code'],'FILE_NOT_FOUND')
        self.assertFalse(row['verified']);self.assertEqual(row['state'],'failed')
        self.assertEqual(row['trace'][0]['stage'],'resolve')
        with patch('runtime_file_picker.pick_existing',return_value=None) as picker:
            _,_,body=await self.call('/api/rpc',{'op':'runtime-pick','data':{}})
            self.assertFalse(json.loads(body)['ok']);picker.assert_not_called()
            _,_,body=await self.call('/api/rpc',{'op':'runtime-pick','data':{'confirmed':True}})
            self.assertTrue(json.loads(body)['value']['cancelled']);picker.assert_called_once()
        self.assertEqual(self.core.service.runtime_manager.record['kind'],'legacy')

    async def test_upload_rejects_paths_offsets_ownership_and_never_overwrites(self):
        await self.login()
        for name in ('../evil.gguf','C:\\evil.gguf','CON.gguf','model.exe'):
            self.assertEqual((await self.call('/api/uploads/start',{'name':name,'size':24}))[0],400)
        content=b'GGUF'+(3).to_bytes(4,'little')+b'\0'*24
        _,_,body=await self.call('/api/uploads/start',{'name':'tiny.gguf','size':len(content)})
        identity=json.loads(body)['value']['id'];url='/api/uploads/'+identity
        self.assertEqual((await self.call(url,method='PUT',raw=content,headers={'content-type':'application/octet-stream','x-upload-offset':'1'}))[0],400)
        status,_,_=await self.call(url,method='PUT',raw=content,headers={'content-type':'application/octet-stream','x-upload-offset':'0'})
        self.assertEqual(status,200)
        status,_,body=await self.call(url+'/finish',{})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['value']['sha256'],hashlib.sha256(content).hexdigest())
        self.assertEqual((await self.call('/api/uploads/start',{'name':'tiny.gguf','size':24}))[0],400)
        self.assertEqual((self.core.service.models/'tiny.gguf').read_bytes(),content)
        with self.assertRaises(ValueError):self.app.uploads.get(identity,'other-session')

    async def test_work_media_range_export_and_arbitrary_file_api(self):
        await self.login();name='a'*12+'.webm';self.core.service.outputs.mkdir(exist_ok=True)
        (self.core.service.outputs/name).write_bytes(b'0123456789')
        status,headers,body=await self.call('/api/works/'+name,headers={'range':'bytes=2-5'})
        self.assertEqual(status,206);self.assertEqual(body,b'2345');self.assertEqual(headers[b'content-range'],b'bytes 2-5/10')
        self.assertEqual((await self.call('/api/works/'+name,headers={'range':'bytes=999-'}))[0],416)
        self.assertEqual((await self.call('/api/rpc',{'op':'work-open','data':{'name':name}}))[0],400)
        self.assertEqual((await self.call('/api/exports/'+('a'*32)))[0],404)

    async def test_shutdown_requires_auth_csrf_and_explicit_confirmation(self):
        await self.login();stops=[];self.app.stop_callback=lambda:stops.append(True)
        self.assertEqual((await self.call('/api/shutdown',{}))[0],400)
        self.assertEqual((await self.call('/api/shutdown',{'confirmed':True}))[0],200)
        self.assertEqual(stops,[True])
        self.assertEqual((await self.call('/api/rpc',{'op':'run','data':{}}))[0],503)


if __name__=='__main__':unittest.main()

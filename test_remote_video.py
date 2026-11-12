"""Controlled inference, real media and production Host/Client/store/scheduler paths."""
from contextlib import contextmanager
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
import json

from desktop_worker import Desktop
from remote_host import digest,ProtocolError
from remote_media import media_input
from test_remote_media import Response


class RemoteVideoTests(TestCase):
    kind='video'
    workflow='wan21'
    suffix='.webm'

    def test_managed_job_to_verified_local_work_and_owner_isolation(self):
        with TemporaryDirectory() as a,TemporaryDirectory() as b:
            hostapp,clientapp=Desktop(Path(a)),Desktop(Path(b))
            host=hostapp.remote_host
            hostapp.comfy.port=8188
            host.id,host.label,host.state,host.address,host.port='a'*32,'Controlled host','ready','127.0.0.1',4443
            peer,other='b'*32,'c'*32
            with hostapp.connect() as db:
                for identity in (peer,other):db.execute('INSERT INTO remote_host_grants VALUES(?,?,?)',(identity,identity,digest(identity)))
            host.engine_status=lambda:{'accepting':False,'installed':False,'busy':False,'error':'No text engine'}
            host.media=lambda:{self.kind:{'state':'ready','installed':True,'workflows':[self.workflow],'formats':[self.suffix[1:]],'schema':2,'weights_verified':True}}
            case=self
            class Client:
                id,label,host,port='a'*32,'Controlled host','127.0.0.1',4443
                def capability(self):return host.capabilities()
                def job(self,request):return host.job(peer,request)
                def json(self,method,path,data=None):
                    if path=='/v1/jobs':return host.submit(peer,data)
                    if path.endswith('/cancel'):return host.job(peer,path.split('/')[3],cancel=True)
                    raise AssertionError(path)
                @contextmanager
                def request(self,method,path,headers):
                    file,info=host.artifact(peer,path.split('/')[3])
                    offset=int(headers.get('Range','bytes=0-')[6:-1]);body=file.read_bytes()
                    yield Response(body[offset:],206 if offset else 200,{'ETag':'"'+info['sha256']+'"','Content-Length':str(len(body)-offset),
                        'Content-Type':info['mime'],'Content-Range':f'bytes {offset}-{len(body)-1}/{len(body)}'})
            client=Client();clientapp.remote_clients.items[host.id]=client
            def generate(_self,kind,prompt,lyrics,output,_stop,_report,**options):
                case.assertEqual(kind,'music' if case.kind=='audio' else case.kind)
                output.mkdir(parents=True,exist_ok=True);path=output/('a12345678901'+case.suffix)
                copyfile(Path(__file__).parent/'desktop/tests/media-fixtures'/('sample'+case.suffix),path)
                return path
            try:
                cap=host.capabilities()
                self.assertIn('music' if self.kind=='audio' else self.kind,cap['tasks'])
                self.assertEqual(cap['task_health']['chat'],'unhealthy')
                check=clientapp.task_preflight({'task':'music' if self.kind=='audio' else self.kind,'targets':[{'runtime':host.id,'model':self.workflow}],'policy':'manual'})
                self.assertEqual(check['state'],'ready')
                args={'kind':'music' if self.kind=='audio' else self.kind,'runtime':host.id,'workflow':self.workflow,'prompt':'controlled synthetic media','lyrics':'controlled lyrics' if self.kind=='audio' else '', 'options':{'seed':17},'policy':'manual'}
                with self.assertRaises(ValueError):clientapp.perform('media',args,Event(),lambda **_:None)
                with patch.object(hostapp.comfy,'running',return_value=True),patch('desktop_worker.ComfyClient.generate',generate):
                    result=clientapp.perform('media',{**args,'consent':True},Event(),lambda **_:None)
                name=result['file'].split('/')[-1]
                works=clientapp.rpc('works-library',{})['items']
                self.assertEqual(works[0]['name'],name);self.assertEqual(works[0]['options']['seed'],17)
                self.assertEqual(works[0]['source']['host'],host.id)
                self.assertEqual((clientapp.outputs/name).read_bytes(),(Path(__file__).parent/'desktop/tests/media-fixtures'/('sample'+self.suffix)).read_bytes())
                request=works[0]['source']['job']
                self.assertEqual(clientapp.client_media.get(host.id,request)['download_status'],'verified')
                self.assertEqual(clientapp.client_media.get(host.id,request)['lyrics'],args['lyrics'])
                with self.assertRaises(ProtocolError):host.artifact(other,request)
                body=media_input({'kind':self.kind,'workflow':self.workflow,'prompt':'queued'})
                key=uuid4().hex
                with patch.object(host.scheduler,'_dispatch'):
                    host.submit(peer,{'request':key,**body});host.submit(peer,{'request':key,**body})
                    queued_task=host.jobs[(peer,key)][0]
                    with self.assertRaises(ProtocolError):host.submit(peer,{'request':key,**body,'prompt':'changed'})
                    with hostapp.connect() as db:host.records.recover(db)
                    self.assertEqual(host.job(peer,key)['state'],'interrupted')
                host.scheduler.snapshot(queued_task,cancel=True)
            finally:
                for _,timer in host.jobs.values():timer.cancel()
                hostapp.close();clientapp.close()

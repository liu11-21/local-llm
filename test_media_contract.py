from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import patch
from remote_media import media_input,descriptor,fetch_image,validate_artifact,MEDIA_LIMITS
from test_remote_media import Response

FIXTURES=Path(__file__).parent/'desktop/tests/media-fixtures'


class MediaContractTests(TestCase):
    def test_video_audio_real_containers_resume_cancel_integrity_and_space(self):
        for kind,workflow,suffix in [('video','wan21','.webm'),('audio','ace-step','.flac')]:
            with self.subTest(kind=kind),TemporaryDirectory() as folder:
                root=Path(folder).resolve();source=root/('a12345678901'+suffix)
                copyfile(FIXTURES/('sample'+suffix),source)
                manifest=descriptor(source,workflow,{},'2026-11-12T00:00:00+00:00',Event(),owner='c'*32,host='a'*32,job='b'*32)
                body=source.read_bytes();calls=[]
                class Client:
                    id='a'*32
                    @contextmanager
                    def request(self,method,path,headers):
                        offset=int(headers.get('Range','bytes=0-')[6:-1]);calls.append(offset)
                        data=body[offset:] if len(calls)>1 else body[:31]
                        yield Response(data,206 if offset else 200,{'ETag':'"'+manifest['sha256']+'"','Content-Length':str(len(body)-offset),
                            'Content-Type':manifest['mime'],'Content-Range':f'bytes {offset}-{len(body)-1}/{len(body)}'})
                with self.assertRaises(ConnectionError):fetch_image(Client(),'b'*32,manifest,root/'out',root/'cache',Event(),lambda **_:None)
                result=fetch_image(Client(),'b'*32,manifest,root/'out',root/'cache',Event(),lambda **_:None)
                self.assertEqual(result.read_bytes(),body);self.assertEqual(calls,[0,31])
                with patch('remote_media.shutil.disk_usage',return_value=type('Disk',(),{'free':0})()),self.assertRaisesRegex(OSError,'空間'):
                    fetch_image(Client(),'b'*32,manifest,root/'other',root/'other-cache',Event(),lambda **_:None)
                with self.assertRaisesRegex(ValueError,'主機或任務'):
                    fetch_image(Client(),'d'*32,manifest,root/'out',root/'cache',Event(),lambda **_:None)
                cancelled=Event();cancelled.set()
                with self.assertRaises(InterruptedError):fetch_image(Client(),'b'*32,manifest,root/'cancel',root/'cancel-cache',cancelled,lambda **_:None)

    def test_allowlist_versions_mime_and_per_type_limits(self):
        self.assertEqual(media_input({'kind':'audio','workflow':'ace-step','prompt':'music','lyrics':'hello'})['lyrics'],'hello')
        for change in ({'workflow':'sd15'},{'schema':1},{'options':{'command':'bad'}},{'script':'bad'}):
            with self.assertRaises(ValueError):media_input({'kind':'video','workflow':'wan21','prompt':'scene',**change})
        self.assertGreater(MEDIA_LIMITS['video'],MEDIA_LIMITS['image'])
        with self.assertRaises(ValueError):validate_artifact({'schema':2,'kind':'video','id':'../../secret.webm'})

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
from remote_media import checksum,validate_content

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

    def test_large_video_streams_above_image_limit_without_loading_file_into_sqlite(self):
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();path=root/'a12345678901.webm'
            copyfile(FIXTURES/'sample.webm',path)
            padding=34*1024**2
            with path.open('r+b') as stream:
                stream.seek(0,2)
                stream.write(b'\xec'+((1<<56)|padding).to_bytes(8,'big'))
                stream.seek(padding-1,1);stream.write(b'\0')
            artifact=descriptor(path,'wan21',{},'2026-11-12T00:00:00+00:00',Event(),owner='c'*32,host='a'*32,job='b'*32)
            self.assertGreater(artifact['bytes'],MEDIA_LIMITS['image'])
            class Client:
                id='a'*32
                @contextmanager
                def request(self,method,url,headers):
                    with path.open('rb') as stream:
                        stream.status=200
                        stream.getheader=lambda key:{'ETag':'"'+artifact['sha256']+'"','Content-Length':str(artifact['bytes']),'Content-Type':'video/webm'}.get(key)
                        yield stream
            result=fetch_image(Client(),'b'*32,artifact,root/'out',root/'cache',Event(),lambda **_:None)
            self.assertEqual(checksum(result,Event()),artifact['sha256'])

    def test_new_png_rejects_corrupt_crc_and_video_cannot_be_renamed_png(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);path=root/'a12345678901.png';copyfile(FIXTURES/'sample.png',path)
            validate_content(path,'image')
            oversized=bytearray(path.read_bytes());oversized[16:20]=(2**31).to_bytes(4,'big');path.write_bytes(oversized)
            with self.assertRaisesRegex(ValueError,'尺寸'):validate_content(path,'image')
            copyfile(FIXTURES/'sample.png',path)
            body=bytearray(path.read_bytes());body[-6]^=1;path.write_bytes(body)
            with self.assertRaisesRegex(ValueError,'CRC'):validate_content(path,'image')
            copyfile(FIXTURES/'sample.webm',path)
            with self.assertRaises(ValueError):validate_content(path,'image')

from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch
import json

from remote_media import fetch_image, image_input, ClientMedia
from desktop_worker import Desktop

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" + b"\x00\x00\x00\x01"*2 + b"controlled media payload"


class Response(BytesIO):
    def __init__(self, data, status, headers):
        super().__init__(data)
        self.status = status
        self.headers = headers

    def getheader(self, key):
        return self.headers.get(key)


class RemoteMediaTests(unittest.TestCase):
    def test_migration_and_private_prompt_recovery_after_client_restart(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            worker = Desktop(root)
            host, job = "a"*32,"b"*32
            payload = image_input({"kind":"image","workflow":"sd15","prompt":"private prompt",
                                   "options":{"negative":"private exclusions","seed":417}})
            worker.client_media.submit(host,job,payload)
            worker.close()
            worker = Desktop(root)
            try:
                artifact = {"id":"a12345678901.png","kind":"image","workflow":"sd15","bytes":len(PNG),
                            "sha256":sha256(PNG).hexdigest(),"options":payload["options"]}
                class Client:
                    label = "paired host"
                    def job(self, request):
                        return {"state":"completed","artifact":artifact}
                path = worker.outputs / "a12345678901.png"
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(PNG)
                with patch.object(worker.remote_clients,"get",return_value=Client()), \
                     patch("desktop_worker.fetch_image",return_value=path):
                    worker.remote_image({"runtime":host,"request":job},Event(),lambda **_:None,fetch_only=True)
                with worker.connect() as db:
                    details = json.loads(db.execute("SELECT details FROM creations").fetchone()[0])
                    self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0],9)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM remote_jobs").fetchone()[0],0)
                self.assertEqual(details["prompt"],"private prompt")
                self.assertEqual(details["options"]["negative"],"private exclusions")
                self.assertEqual(details["options"]["seed"],417)
                self.assertTrue(details["submitted"])
                self.assertEqual(worker.client_media.get(host,job)["state"],"saved")
                self.assertIsNone(worker.client_media.get("c"*32,job))
                with worker.connect() as db:
                    ClientMedia.initialize(db)
                self.assertEqual(worker.client_media.get(host,job)["prompt"],"private prompt")
            finally:
                worker.close()

    def test_workflow_allowlist_and_range_limits(self):
        data = {"kind":"image","workflow":"sd15","prompt":"paint"}
        self.assertEqual(image_input(data)["options"]["width"],512)
        for change in ({"workflow":"wan21"},{"options":{"width":2048}},{"nodes":{"1":{}}},{"file":"secret"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                image_input({**data,**change})

    def test_range_resume_and_sha_rejection(self):
        signature = sha256(PNG).hexdigest()
        tag = signature
        requests = []

        class Client:
            id = "a"*32

            @contextmanager
            def request(self, method,path,headers):
                requests.append(headers)
                offset = 21 if "Range" in headers else 0
                first = len(requests)==1
                headers = {"ETag":f'"{tag}"',"Content-Length":str(len(PNG)-offset),
                           "Content-Range":f"bytes {offset}-{len(PNG)-1}/{len(PNG)}"}
                yield Response(PNG[:21] if first else PNG[offset:],206 if offset else 200,headers)

        manifest = {"id":"a12345678901.png","kind":"image","workflow":"sd15","bytes":len(PNG),"sha256":signature}
        with TemporaryDirectory() as directory:
            data = Path(directory).resolve()
            with self.assertRaises(ConnectionError):
                fetch_image(Client(),"b"*32,manifest,data/"out",data/"cache",Event(),lambda **_:None)
            self.assertFalse(list((data/"out").glob("*.png")))
            out = fetch_image(Client(),"b"*32,manifest,data/"out",data/"cache",Event(),lambda **_:None)
            self.assertEqual(out.read_bytes(),PNG)
            self.assertEqual(requests,[{},{"Range":"bytes=21-"}])
            tag = "9"*64
            with self.assertRaisesRegex(ValueError,"SHA-256"):
                fetch_image(Client(),"c"*32,{**manifest,"sha256":tag},data/"out",data/"cache",Event(),lambda **_:None)
            self.assertEqual(len(list((data/"out").glob("*.png"))),1)

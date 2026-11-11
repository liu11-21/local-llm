from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Timer
from time import monotonic, sleep
from unittest import TestCase
from unittest.mock import patch
import json
import subprocess
import sys
from uuid import uuid4
from io import BytesIO
from hashlib import sha256
from zipfile import ZipFile

from desktop_worker import Desktop
from openvino_adapter import OpenVINOAdapter, package_manifest
from runtime_provider import route
from task_manager import classify


class OpenVINOAdapterTests(TestCase):
    def test_unsafe_optional_directory_does_not_prevent_existing_workspace_use(self):
        directory = Path(self.folder.name)/"other-data"
        with patch("openvino_adapter.owned",return_value=False):
            adapter = OpenVINOAdapter(directory,self.worker.connect)
            self.assertFalse(adapter.status()["installed"])
            self.assertEqual(adapter.status()["models"],[])
            with self.assertRaises(ValueError):
                adapter.install(Event(),lambda **_:None)
        self.assertFalse(directory.exists())

    def test_install_uses_the_shared_range_downloader_and_retries_an_unpublished_environment(self):
        python_zip = BytesIO()
        with ZipFile(python_zip,"w") as archive:
            archive.writestr("python.exe",b"controlled-runtime")
        payloads = {"python.zip":python_zip.getvalue(),"pip.whl":b"controlled wheel payload for orchestration only"}
        manifest = {"files":[{"name":name,"version":"test","file":file,"url":"https://example.test/"+file,
                             "bytes":len(data),"sha256":sha256(data).hexdigest()}
                            for (file,data),name in zip(payloads.items(),("python-embedded","pip"))]}
        class Response(BytesIO):
            def __init__(self,url,bounds=None,etag=None):
                data = payloads[url.rsplit("/",1)[-1]]
                first,last = bounds or (0,len(data)-1)
                self.status = 206 if bounds else 200
                self.headers = {"Content-Length":str(last-first+1),"Content-Range":f"bytes {first}-{last}/{len(data)}",
                                "ETag":'"controlled"'}
                super().__init__(data[first:last+1])
        updates = []
        with patch("openvino_adapter.package_manifest",return_value=manifest), \
             patch("openvino_adapter.WindowsResponse",Response), \
             patch.object(self.adapter,"_command",side_effect=RuntimeError("controlled install failure")):
            with self.assertRaises(RuntimeError):
                self.adapter.install(Event(),lambda **value:updates.append(value))
        self.assertFalse(self.adapter.runtime.exists())
        self.assertTrue(any("received" in value for value in updates))
        with patch("openvino_adapter.package_manifest",return_value=manifest),patch.object(self.adapter,"_command"):
            self.adapter.install(Event(),lambda **_:None)
        self.assertTrue(self.adapter.installed())

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.worker = Desktop(Path(self.folder.name))
        self.addCleanup(self.worker.close)
        self.adapter = self.worker.openvino

    def model(self, text=False):
        folder = Path(self.folder.name)/"source"
        folder.mkdir(exist_ok=True)
        (folder/"openvino_model.xml").write_text('<net><layers><layer type="Relu"/></layers></net>')
        (folder/"openvino_model.bin").write_bytes(b"fixture")
        if text:
            for name in ("openvino_tokenizer","openvino_detokenizer"):
                (folder/(name+".xml")).write_text("<net/>")
                (folder/(name+".bin")).write_bytes(b"fixture")
            (folder/"config.json").write_text('{"model_type":"fixture"}')
        return self.adapter.import_model(str(folder),Event(),lambda **_:None)["model"]

    def test_optional_packages_are_fixed_and_never_force_a_model_download(self):
        plan = self.adapter.install_plan()
        self.assertFalse(plan["installed"])
        self.assertEqual(len(plan["files"]),8)
        self.assertEqual(plan["download_bytes"],sum(file["bytes"] for file in package_manifest()["files"]))
        for file in plan["files"]:
            self.assertRegex(file["sha256"],r"^[a-f0-9]{64}$")
            self.assertTrue(file["url"].startswith(("https://www.python.org/","https://files.pythonhosted.org/")))
        self.assertEqual(route("privacy","openvino"),"openvino")
        self.assertEqual(classify("chat",{"runtime":"openvino","chat":"1"})[0],"compute")

    def test_import_is_immutable_idempotent_and_rejects_changed_weights(self):
        identity = self.model()
        source = Path(self.folder.name)/"source"
        again = self.adapter.import_model(str(source),Event(),lambda **_:None)["model"]
        self.assertEqual(identity,again)
        directory,record = self.adapter.validate_model(identity)
        self.assertEqual(record["kind"],"tensor")
        self.assertFalse(record["verified_inference"])
        (directory/"openvino_model.bin").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError,"已變更"):
            self.adapter.validate_model(identity)
        with self.assertRaises(ValueError):
            self.adapter.validate_model("../outside")

    def test_missing_provider_wrong_format_and_unknown_npu_quantization(self):
        with self.assertRaisesRegex(ValueError,"Runtime"):
            self.adapter.execute({"op":"detect"},Event(),lambda _:None)
        identity = self.model(text=True)
        with self.assertRaisesRegex(ValueError,"對稱 INT4"):
            self.adapter.infer(identity,"NPU",Event(),lambda _:None,messages=[])
        with self.assertRaises(ValueError):
            self.adapter.infer(identity,"AUTO:CPU,NPU",Event(),lambda _:None,messages=[])
        source = Path(self.folder.name)/"source"
        (source/"openvino_model.xml").write_text("GGUF data")
        with self.assertRaises(Exception):
            self.adapter.import_model(str(source),Event(),lambda **_:None)

    def test_process_ipc_is_cancelled_and_resources_are_released(self):
        fixture = Path(self.folder.name)/"runner.py"
        fixture.write_text("import json,sys,time\nr=json.loads(sys.stdin.readline())\nprint(json.dumps({'event':'loaded'}),flush=True)\ntime.sleep(10)\n")
        launched = []
        def start(_command, **options):
            process = subprocess.Popen([sys.executable,"-I",str(fixture)],**options)
            launched.append(process)
            return process
        stop = Event()
        timer = Timer(.4,stop.set)
        timer.start()
        self.addCleanup(timer.cancel)
        with patch.object(self.adapter,"installed",return_value=True),patch("openvino_adapter.external_process",side_effect=start):
            with self.assertRaises(InterruptedError):
                self.adapter.execute({"op":"detect"},stop,lambda _:None)
        self.assertIsNone(self.adapter.process)
        self.assertIsNotNone(launched[0].poll())

    def test_process_failure_does_not_leak_inputs_and_a_following_call_can_run(self):
        fixture = Path(self.folder.name)/"runner.py"
        fixture.write_text("import json,sys\nr=json.loads(sys.stdin.readline())\nprint(json.dumps({'event':'error','code':'FIXTURE'}),flush=True)\n")
        def start(_command, **options):
            return subprocess.Popen([sys.executable,"-I",str(fixture)],**options)
        with patch.object(self.adapter,"installed",return_value=True),patch("openvino_adapter.external_process",side_effect=start):
            with self.assertRaises(RuntimeError) as failure:
                self.adapter.execute({"op":"infer","secret":"private prompt"},Event(),lambda _:None)
            self.assertNotIn("private prompt",str(failure.exception))
            fixture.write_text("import json,sys\nr=json.loads(sys.stdin.readline())\nprint(json.dumps({'event':'result','devices':['CPU'],'version':'controlled'}),flush=True)\n")
            self.adapter.detect(Event(),lambda **_:None)
        self.assertEqual(self.adapter.detected["devices"],["CPU"])

    def test_cpu_fallback_and_missing_device_evidence_stay_unverified(self):
        identity = self.model()
        result = {"evidence":{"requested_device":"NPU","execution_devices":["CPU"],
                              "fallback":"reported-other-device","verified_inference":False},"latency_ms":1}
        with patch.object(self.adapter,"execute",return_value=result):
            self.adapter.infer(identity,"NPU",Event(),lambda _:None,inputs=[[[1]]])
        record = self.worker.rpc("openvino-runs",{})[0]["details"]
        self.assertFalse(record["verified_inference"])
        self.assertEqual(record["fallback"],"reported-other-device")
        self.assertNotIn("inputs",record)
        with self.assertRaises(ValueError):
            self.worker.rpc("openvino-clear-runs",{})
        self.worker.rpc("openvino-clear-runs",{"confirmed":True})
        self.assertEqual(self.worker.rpc("openvino-runs",{}),[])

    def test_text_chat_uses_normal_history_without_an_external_transfer(self):
        identity = self.model(text=True)
        def infer(_identity,_device,_cancel,update,**_):
            update({"event":"token","text":"controlled reply"})
            return {"evidence":{"verified_inference":False}}
        chat = uuid4().hex
        with patch.object(self.adapter,"infer",side_effect=infer):
            result = self.worker.perform("chat",{"chat":chat,"runtime":"openvino","model":identity,
                                                "policy":"privacy","prompt":"local private prompt","max_tokens":64},
                                         Event(),lambda **_:None)
        self.assertEqual(result["answer"],"controlled reply")
        self.assertEqual(self.worker.history(chat,with_runtime=True)[-1]["provider"],"OpenVINO")

    def test_remove_preserves_models_and_requires_confirmation_at_the_entry_point(self):
        identity = self.model()
        self.adapter.runtime.mkdir()
        (self.adapter.runtime/"managed-file").write_text("runtime only")
        with self.assertRaises(ValueError):
            self.worker.perform("openvino-remove",{},Event(),lambda **_:None)
        self.worker.perform("openvino-remove",{"confirmed":True},Event(),lambda **_:None)
        self.assertTrue((self.adapter.models/identity/"MODEL.json").is_file())
        self.assertFalse(self.adapter.runtime.exists())

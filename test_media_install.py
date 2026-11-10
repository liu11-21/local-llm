from dataclasses import replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from comfy_runtime import install_directory
from desktop_worker import Desktop
from downloads import DownloadCancelled, download_file
from media import MODELS
from media_install import MODELS_FOR_INSTALL, install_plan, install_weights, manifest
from task_manager import classify
from test_downloads import RangeResponse


def range_response(payload, span):
    start, end = span
    return RangeResponse(payload[start:end + 1], start, end, len(payload))


class MediaInstallTests(unittest.TestCase):
    def setUp(self):
        root = TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.data = Path(root.name).resolve()
        self.bundle = install_directory(self.data / "comfyui", "CPU")
        header = json.dumps({"tensor": {"dtype": "U8", "shape": [400], "data_offsets": [0, 400]}}).encode()
        self.payload = len(header).to_bytes(8, "little") + header + b"\x12" * 400
        self.model = MODELS_FOR_INSTALL["image"]
        self.weight = self.model.weights[0]
        self.target = self.bundle / "ComfyUI" / "models" / self.weight.directory / self.weight.filename

    def prepare(self):
        for name in ("python_embeded/python.exe", "ComfyUI/main.py"):
            marker = self.bundle / name
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch()
        model = replace(self.model, weights=(replace(self.weight, bytes=len(self.payload),
                        sha256=hashlib.sha256(self.payload).hexdigest()),))
        mock = patch.dict(MODELS_FOR_INSTALL, {"image": model})
        mock.start()
        self.addCleanup(mock.stop)

    def transfer(self, opener, stop=None, report=lambda **_: None):
        with patch("media_install.download_file", side_effect=lambda *args, **options:
                   download_file(*args, **options, opener=opener)):
            return install_weights(self.data, "image", "CPU", stop or Event(), report)

    def test_manifest_matches_actual_graph_loaders_and_is_pinned(self):
        for kind, model in MODELS_FOR_INSTALL.items():
            entry = manifest(kind)
            self.assertRegex(entry["revision"], r"^[0-9a-f]{40}$")
            self.assertEqual({asset["filename"] for asset in entry["weights"]},
                             {filename for _, _, filename in MODELS[kind][2]})
            self.assertIn("KSampler", entry["nodes"])
            for asset in entry["weights"]:
                self.assertRegex(asset["sha256"], r"^[0-9a-f]{64}$")
                self.assertIn(f"/{model.repo}/resolve/{model.revision}/", asset["url"])
                self.assertEqual(asset["path"].split("/")[-1], asset["filename"])
                self.assertGreater(asset["bytes"], 0)

    def test_preflight_conflicts_disk_and_confirmation(self):
        self.assertFalse(install_plan(self.data, "image", "CPU")["installed"])
        self.prepare()
        self.assertEqual(install_plan(self.data, "image", "CPU")["needed"], len(self.payload))
        with patch("media_install.shutil.disk_usage") as disk:
            disk.return_value.free = 0
            with self.assertRaisesRegex(OSError, "磁碟"):
                install_weights(self.data, "image", "CPU", Event(), lambda **_: None)
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b"user data")
        self.assertTrue(install_plan(self.data, "image", "CPU")["conflict"])
        with self.assertRaisesRegex(ValueError, "同名"):
            install_weights(self.data, "image", "CPU", Event(), lambda **_: None)
        self.assertEqual(self.target.read_bytes(), b"user data")
        with self.assertRaises(ValueError):
            classify("media-install", {"profile": "CPU", "kind": "image"})
        args = {"kind": "image", "confirmed": True}
        self.assertEqual(classify("media-install", {**args, "profile": "CPU"})[2],
                         classify("media-install", {**args, "profile": "NVIDIA CUDA 12.6"})[2])
        with self.assertRaises(ValueError):
            install_plan(self.data, "image", "../../outside")

    def test_rejects_unowned_target(self):
        self.prepare()
        with patch("media_install.owned", side_effect=lambda path: path != self.target):
            with self.assertRaisesRegex(ValueError, "不安全"):
                install_plan(self.data, "image", "CPU")

    def test_cancel_and_wrong_checksum_leave_destination_untouched(self):
        self.prepare()
        stop = Event()

        def progress(**state):
            if state.get("received", 0):
                stop.set()

        with self.assertRaises(DownloadCancelled):
            self.transfer(lambda _, span, etag=None: range_response(self.payload, span), stop, progress)
        self.assertFalse(self.target.exists())
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.transfer(lambda _, span, etag=None: range_response(self.payload[:-1] + b"x", span))
        self.assertFalse(self.target.exists())

    def test_interrupted_install_resumes_and_repeat_verifies_without_transfer(self):
        self.prepare()
        spans = []

        def broken(_, span, etag=None):
            if span[0] >= 256:
                raise ConnectionError("test disconnect")
            return range_response(self.payload, span)

        def restored(_, span, etag=None):
            spans.append(span)
            return range_response(self.payload, span)

        with patch("downloads.BLOCK", 64), patch("download_recovery.BLOCK", 64), patch("media_install.BLOCK", 64):
            with self.assertRaises(ConnectionError):
                self.transfer(broken)
            plan = install_plan(self.data, "image", "CPU")
            self.assertLess(plan["needed"], len(self.payload))
            self.assertFalse(self.target.exists())
            self.transfer(restored)
            self.assertNotIn((0, 63), spans)
            self.assertEqual(self.target.read_bytes(), self.payload)
            self.assertEqual(install_plan(self.data, "image", "CPU")["files"][0]["status"], "detected")
            spans.clear()
            self.transfer(restored)
            self.assertEqual(spans, [])
            self.target.write_bytes(self.payload[:-1] + b"x")
            with self.assertRaisesRegex(ValueError, "既有權重 SHA-256"):
                self.transfer(restored)

    def test_verification_status_is_bound_to_current_file_identity(self):
        self.prepare()
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(self.payload)
        path = str(self.target.relative_to(self.data))
        worker = Desktop(self.data)
        self.addCleanup(worker.close)
        args = {"kind":"image", "profile":"CPU", "confirmed":True}
        self.assertEqual(worker.rpc("media-install-plan", args)["files"][0]["status"], "detected")
        worker.perform("media-install", args, Event(), lambda **_: None)
        self.assertTrue(worker.rpc("media-install-plan", args)["verified"])
        self.target.write_bytes(self.payload[:-1] + b"x")
        self.assertEqual(worker.rpc("media-install-plan", args)["files"][0]["status"], "detected")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            worker.perform("media-install", args, Event(), lambda **_: None)
        self.assertEqual(worker.rpc("media-install-plan", args)["files"][0]["status"], "conflict")

    def test_post_install_readiness_reports_missing_builtin_nodes(self):
        worker = Desktop(self.data)
        self.addCleanup(worker.close)
        from time import sleep
        missing_node = "SaveImage"

        def response(_, path):
            name = path.split("/")[-1]
            if name == "system_stats":
                return {"system": {}}
            return {} if name == missing_node else {name: {}}

        with patch("media.ComfyClient.json", response), patch("media.ComfyClient.missing_models", return_value=[]):
            data = {"kind": "image", "workflow": "sd15", "port": 8188}
            for _ in range(50):
                state = worker.rpc("media-readiness", data)
                if state["state"] != "checking":
                    break
                sleep(0.01)
            self.assertEqual(state["state"], "missing")
            self.assertEqual(state["missing_nodes"], ["SaveImage"])
            missing_node = ""
            worker.rpc("media-readiness", {**data, "refresh": True})
            for _ in range(50):
                state = worker.rpc("media-readiness", data)
                if state["state"] != "checking":
                    break
                sleep(0.01)
            self.assertEqual(state["state"], "ready")

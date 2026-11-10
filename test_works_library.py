import json
import os
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from desktop_worker import Desktop
from media import ComfyClient, FORMATS
from registries import media_metadata, work_file


def ebml(tag, data):
    return bytes.fromhex(tag) + bytes([0x80 | len(data)]) + data


class WorksLibraryTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.worker = Desktop(Path(directory.name))
        self.addCleanup(self.worker.close)
        self.worker.outputs.mkdir(exist_ok=True)

    def add(self, name, contents, modified, details=None):
        path = self.worker.outputs / name
        path.write_bytes(contents)
        os.utime(path, (modified, modified))
        if details is not None:
            with self.worker.connect() as db:
                db.execute("INSERT INTO creations VALUES(?,?)", (name, json.dumps(details)))
        return path

    def test_saved_media_formats_metadata_and_legacy_records(self):
        png = FORMATS["image"][1] + bytes.fromhex("0000000d49484452") + struct.pack(">II", 320, 192)
        flac_info = (44_100 << 44 | 88_200).to_bytes(8, "big")
        flac = b"fLaC\x80\0\0\x22" + b"\0" * 10 + flac_info + b"\0" * 16
        info = ebml("1549A966", ebml("4489", struct.pack(">d", 1000.0)))
        tracks = ebml("1654AE6B", ebml("AE", ebml("E0", ebml("B0", b"\xf0") + ebml("BA", b"\x90"))))
        webm = ebml("1A45DFA3", b"") + ebml("18538067", info + tracks)
        legacy = {"model": "Stable Diffusion 1.5", "workflow": "sd15", "prompt": "雪景作品", "options": {"seed": 0}}
        self.add("a12345678901.png", png, 10, legacy)
        self.add("b12345678901.flac", flac, 20, {"model": "ACE-Step v1", "lyrics": "Cedar"})
        self.add("c12345678901.webm", webm, 30)
        self.add("invalid.txt", b"unrelated", 40)
        result = self.worker.rpc("works-library", {"sort": "oldest"})
        image, music, video = result["items"]
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["models"], ["ACE-Step v1", "Stable Diffusion 1.5"])
        self.assertEqual([(item["kind"], item["dimensions"]) for item in result["items"]], [
            ("image", {"width":320, "height":192}), ("music", {"duration":2}),
            ("video", {"width":240, "height":144, "duration":1}),
        ])
        self.assertEqual(image["options"]["seed"], 0)
        self.assertEqual(self.worker.rpc("works", {})[0]["name"], video["name"])
        query = {"kind": "music", "model": "ACE-Step v1", "query": "CEDAR"}
        self.assertEqual(self.worker.rpc("works-library", query)["items"], [music])
        self.assertEqual(self.worker.rpc("works-library", {**query, "offset": 24})["items"], [])
        self.assertEqual(self.worker.rpc("works-library", {"query": "雪景"})["total"], 1)

    def test_original_opens_only_a_present_safe_media_filename(self):
        path = self.add("a12345678901.png", b"test", 10)
        if os.name == "nt":
            with patch("desktop_worker.os.startfile") as open_file:
                self.worker.rpc("work-open", {"name": path.name})
                open_file.assert_called_once_with(path)
        for name in ("../a12345678901.png", "b12345678901.png", "a12345678901.exe"):
            with self.assertRaises(ValueError):
                self.worker.rpc("work-open", {"name": name})
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaises(ValueError):
                work_file(self.worker.outputs, path.name)

    def test_generation_preserves_seed_and_records_runtime_and_comfy_job(self):
        def generate(_client, _kind, _prompt, _lyrics, _out, _stop, _report, **options):
            options["on_source"]({"engine": "ComfyUI", "job": "one-job", "original": "image.png"})
            return self.add("a12345678901.png", b"generated fixture", 10)

        with patch.object(ComfyClient, "generate", generate):
            self.worker.perform("media", {"kind": "image", "workflow": "sd15-preview", "prompt": "snow",
                                "port": 8188, "options": {"seed": 42, "width": 256}}, Event(), lambda **_: None)
        saved = self.worker.rpc("works-library", {})["items"][0]
        self.assertEqual((saved["schema"], saved["status"], saved["runtime"], saved["workflow"]),
                         (1, "completed", "local-comfyui", "sd15-preview"))
        self.assertEqual(saved["source"]["job"], "one-job")
        self.assertEqual(saved["options"]["seed"], 42)

    def test_malformed_webm_is_ignored(self):
        path = self.add("a12345678901.webm", bytes.fromhex("18538067840000"), 10)
        self.assertEqual(media_metadata(path), {})

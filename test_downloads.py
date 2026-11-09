"""Verify the range downloader can resume short reads without corrupting a GGUF."""
from io import BytesIO
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from downloads import download_model
from download_recovery import download_lock


PINNED = "https://huggingface.co/example/repo/resolve/" + "a" * 40 + "/model.gguf"
PAYLOAD = b"GGUF" + (3).to_bytes(4, "little") + bytes(range(248))


def fixture_opener(_url, byte_range, etag=None):
    first, last = byte_range
    return RangeResponse(PAYLOAD[first:last + 1], first, last, len(PAYLOAD))


class RangeResponse(BytesIO):
    def __init__(self, payload, first, last, size, *, short=False):
        super().__init__(payload[:15] if short else payload)
        self.status = 206
        self.headers = {"Content-Range": f"bytes {first}-{last}/{size}",
                        "Content-Length": str(len(payload)), "ETag": '"fixed"'}
        self.read1 = self.read


class DownloadTests(unittest.TestCase):
    def test_abrupt_worker_exit_recovers_ranges_on_desktop_reopen(self):
        from desktop_worker import Desktop
        script = """
import os, sys
from pathlib import Path
from threading import Event
from test_downloads import PINNED, fixture_opener
import downloads, download_recovery
downloads.BLOCK = download_recovery.BLOCK = 64
models = Path(sys.argv[1]) / 'models'
def interrupted(url, byte_range, etag=None):
    if byte_range[0] == 64:
        os._exit(73)
    return fixture_opener(url, byte_range, etag)
downloads.download_model(PINNED, models, 1, Event(), lambda *_: None,
                         opener=interrupted, recovery=models / '.localllm-downloads')
"""
        with TemporaryDirectory() as folder, patch("downloads.BLOCK", 64), patch("download_recovery.BLOCK", 64):
            self.assertEqual(subprocess.run([sys.executable, "-c", script, folder], timeout=20).returncode, 73)
            worker = Desktop(Path(folder))
            self.addCleanup(worker.close)
            legacy = worker.models / ".model-legacy.part"
            legacy.write_bytes(b"user data")
            recovered = worker.rpc("info", {})["recoverable_downloads"]
            self.assertEqual([(item["url"], item["received"]) for item in recovered], [(PINNED, 64)])
            self.assertEqual(worker.rpc("info", {})["models"], [])
            calls = []

            def opener(url, byte_range, etag=None):
                calls.append(byte_range)
                return fixture_opener(url, byte_range, etag)

            result = download_model(PINNED, worker.models, 3, Event(), lambda *_: None, opener=opener,
                                    recovery=worker.download_cache)
            self.assertNotIn((0, 63), calls)
            self.assertEqual(result.read_bytes(), PAYLOAD)
            self.assertEqual(legacy.read_bytes(), b"user data")
            self.assertEqual(worker.rpc("info", {})["recoverable_downloads"], [])

    def test_hash_mismatch_and_cancellation_never_publish_a_model(self):
        with TemporaryDirectory() as folder, patch("downloads.BLOCK", 64), patch("download_recovery.BLOCK", 64):
            models = Path(folder)
            cache = models / ".localllm-downloads"
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                download_model(PINNED, models, 2, Event(), lambda *_: None, opener=fixture_opener,
                               recovery=cache, expected_sha="a" * 64)
            from downloads import DownloadCancelled
            cancel = Event()
            with self.assertRaises(DownloadCancelled):
                download_model(PINNED, models, 2, cancel, lambda count, *_: count and cancel.set(),
                               opener=fixture_opener, recovery=cache, expected_sha=sha256(PAYLOAD).hexdigest())
            self.assertFalse((models / "model.gguf").exists())
            self.assertEqual(list(cache.glob("*/data.part")), [])

    def test_same_target_lock_rejects_overlapping_writers(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with download_lock(root, root / "Model.gguf"):
                with self.assertRaises(ValueError), download_lock(root, root / "model.gguf"):
                    self.fail("duplicate writer acquired lock")

    def test_reopen_cleans_only_owned_nonresumable_staging(self):
        from desktop_worker import Desktop
        with TemporaryDirectory() as folder:
            data = Path(folder)
            models = data / "models"
            cache = models / ".localllm-downloads"
            with download_lock(cache, models / "model.gguf") as checkpoints:
                checkpoints.prepare(PINNED, 0, None, None)
                checkpoints.staging.write_bytes(PAYLOAD[:50])
                unrelated = checkpoints.directory / "personal.part"
                unrelated.write_bytes(b"unrelated")
            worker = Desktop(data)
            self.addCleanup(worker.close)
            self.assertFalse(checkpoints.staging.exists())
            self.assertFalse(checkpoints.manifest.exists())
            self.assertEqual(unrelated.read_bytes(), b"unrelated")
            self.assertEqual(worker.rpc("info", {})["recoverable_downloads"], [])

    def test_verified_source_is_tied_to_the_downloaded_file(self):
        from catalog import model_source
        from desktop_worker import Desktop
        checksum = sha256(PAYLOAD).hexdigest()
        metadata = {"sha": "a" * 40, "cardData": {"license": "apache-2.0"},
                    "siblings": [{"rfilename": "model.gguf", "size": len(PAYLOAD), "lfs": {"sha256": checksum}}]}
        with (
            TemporaryDirectory() as folder,
            patch("catalog.read_metadata", return_value=metadata),
            patch("desktop_worker.download_model", side_effect=lambda *args, **options:
                  download_model(*args, **options, opener=fixture_opener)),
        ):
            self.assertEqual(model_source(PINNED)["expected_sha256"], checksum)
            worker = Desktop(Path(folder))
            self.addCleanup(worker.close)
            worker.download({"url": PINNED, "workers": 2}, Event(), lambda **_: None)
            entry = worker.rpc("info", {})["registry"]["models"][0]
            self.assertEqual((entry["verification"], entry["sha256"], entry["license"]),
                             ("verified", checksum, "apache-2.0"))
            path = worker.models / "model.gguf"
            path.write_bytes(PAYLOAD + b"changed")
            self.assertEqual(worker.rpc("info", {})["registry"]["models"][0]["verification"], "unknown")
            worker.rpc("model-imported", {"model": path.name})
            self.assertEqual(worker.rpc("info", {})["registry"]["models"][0]["verification"], "imported")

    def test_each_worker_resumes_with_smaller_requests_after_disconnect(self):
        payload = b"GGUF" + (3).to_bytes(4, "little") + bytes(range(128))

        def opener(_url, byte_range, etag=None):
            first, last = byte_range
            short = etag is not None and last - first > 31
            return RangeResponse(payload[first:last + 1], first, last, len(payload), short=short)

        progress = []
        with TemporaryDirectory() as folder, patch("downloads.RETRY_SPAN", 32):
            result = download_model("https://example.test/model.gguf", folder, 2, Event(),
                                    lambda *values: progress.append(values), opener=opener)
            self.assertEqual(result.read_bytes(), payload)
            self.assertEqual(progress[-1], (len(payload), len(payload), 2))

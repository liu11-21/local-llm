"""Verify the range downloader can resume short reads without corrupting a GGUF."""
from io import BytesIO
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from downloads import download_model


class RangeResponse(BytesIO):
    def __init__(self, payload, first, last, size, *, short=False):
        super().__init__(payload[:15] if short else payload)
        self.status = 206
        self.headers = {"Content-Range": f"bytes {first}-{last}/{size}",
                        "Content-Length": str(len(payload)), "ETag": '"fixed"'}
        self.read1 = self.read


class DownloadTests(unittest.TestCase):
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

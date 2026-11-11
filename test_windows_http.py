from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import ssl
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase, skipIf

from test_remote_host import make_certificate
from windows_http import WindowsResponse


class WindowsDownloadTests(TestCase):
    def test_transport_rejects_plaintext_and_embedded_credentials_before_connecting(self):
        for url in ("http://example.test/file","https://user:password@example.test/file"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                WindowsResponse(url)

    @skipIf(os.name!="nt" or os.environ.get("LOCALLLM_TEST_TLS_INTERCEPTED")=="1",
            "Requires unmodified Windows TLS validation")
    def test_system_tls_rejects_an_untrusted_loopback_certificate(self):
        with TemporaryDirectory() as directory:
            cert,key = make_certificate(Path(directory))
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert,key)
            server = ThreadingHTTPServer(("127.0.0.1",0),BaseHTTPRequestHandler)
            server.socket = context.wrap_socket(server.socket,server_side=True)
            thread = Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                with self.assertRaises(ConnectionError):
                    WindowsResponse(f"https://127.0.0.1:{server.server_port}/asset",(0,0))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

from contextlib import contextmanager
from io import BytesIO
import os
from pathlib import Path
import ssl
from tempfile import TemporaryDirectory
from threading import Event
import unittest

from remote_client import RemoteClient, protect
from test_remote_host import make_certificate


class EventStream(BytesIO):
    def getheader(self, key):
        return "text/event-stream"


class ClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.cert, cls.key = make_certificate(Path(folder.name))

    @unittest.skipUnless(os.name == "nt", "DPAPI requires Windows")
    def test_dpapi_round_trip(self):
        data = b"unit test only"
        encrypted = protect(data)
        self.assertNotIn(data, encrypted)
        self.assertEqual(protect(encrypted, decrypt=True), data)

    def test_tls_identity_without_network_interception(self):
        client = RemoteClient("1"*32, "127.0.0.1", 9443, "test", self.cert.read_text())
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.cert), str(self.key))

        def handshake(hostname):
            inbound, outbound = ssl.MemoryBIO(), ssl.MemoryBIO()
            server_in, server_out = ssl.MemoryBIO(), ssl.MemoryBIO()
            peer = client.context.wrap_bio(inbound, outbound, server_hostname=hostname)
            server = context.wrap_bio(server_in, server_out, server_side=True)
            for _ in range(15):
                for connection, outgoing, incoming in ((peer, outbound, server_in), (server, server_out, inbound)):
                    try:
                        connection.do_handshake()
                    except ssl.SSLWantReadError:
                        pass
                    incoming.write(outgoing.read())
                if peer.version() and server.version():
                    return peer.getpeercert(binary_form=True)
            self.fail("TLS handshake did not complete")

        self.assertEqual(handshake("127.0.0.1"), client.cert_der)
        with self.assertRaises(ssl.SSLCertVerificationError):
            handshake("127.0.0.2")

    def test_stream_resume_reuses_request_and_only_yields_new_data(self):
        client = RemoteClient("1"*32, "127.0.0.1", 9443, "test", self.cert.read_text())
        submissions = []

        def submit(method, path, body=None):
            submissions.append(body["request"])
            return {"id": body["request"]}

        @contextmanager
        def receive(method, path):
            output = (b'data: {"state":"running","delta":"one"}\n\n' if len(submissions) == 1 else
                      b'data: {"state":"completed","delta":"one two"}\n\n')
            yield EventStream(output)

        client.json, client.request = submit, receive
        answer = list(client.stream("demo.gguf", [{"role":"user","content":"question"}], 128, 0.4, Event()))
        self.assertEqual(answer, ["one", " two"])
        self.assertEqual(len(submissions), 2)
        self.assertEqual(submissions[0], submissions[1])

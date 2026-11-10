from pathlib import Path
from tempfile import TemporaryDirectory
import os
import ssl
import unittest
from unittest.mock import patch

from desktop_worker import Desktop
from remote_client import RemoteClient
from remote_tls import create_material, private_addresses
from test_remote_host import free_port


class ManagedTLSTests(unittest.TestCase):
    def test_network_choices_exclude_public_and_loopback(self):
        ips = ["10.20.30.40", "8.8.8.8", "127.0.0.1", "10.20.30.40", "192.168.1.5"]
        with patch("remote_tls.socket.getaddrinfo", return_value=[(None, (ip, 0)) for ip in ips]):
            self.assertEqual(private_addresses(), ["10.20.30.40", "192.168.1.5"])

    @unittest.skipUnless(os.name == "nt", "DPAPI requires Windows")
    def test_managed_key_is_encrypted_and_certificate_is_accepted_by_tls_parser(self):
        address, cert, key, protected, expires = create_material("127.0.0.1")
        self.assertIn(b"ENCRYPTED PRIVATE KEY", key)
        self.assertNotIn(b"PRIVATE KEY", cert)
        client = RemoteClient("a"*32, address, 9443, "fixture", cert.decode("ascii"))
        self.assertEqual(client.context.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreater(expires, 0)
        self.assertNotIn(key, protected)

    @unittest.skipUnless(os.name == "nt", "DPAPI requires Windows")
    def test_reuses_identity_and_revokes_on_confirmed_rotation(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        worker = Desktop(Path(folder.name))
        self.addCleanup(worker.close)
        args = {"address":"127.0.0.1", "label":"Fixture", "port":free_port(), "confirmed":True}
        first = worker.rpc("remote-host-start-auto", args)
        preview = worker.rpc("remote-client-preview", {"invite":worker.rpc("remote-host-invite", {"confirmed":True})})
        self.assertEqual(preview["fingerprint"], first["fingerprint"])
        worker.rpc("remote-host-stop", {})
        args["port"] = free_port()
        self.assertEqual(worker.rpc("remote-host-start-auto",args)["fingerprint"], first["fingerprint"])
        worker.rpc("remote-host-stop", {})
        with worker.connect() as db:
            db.execute("INSERT INTO remote_host_grants VALUES(?,?,?)", ("a"*32, "Old peer", "1"*64))
        with self.assertRaisesRegex(ValueError, "更新主機憑證"):
            worker.rpc("remote-host-start-auto", {**args, "address":"127.0.0.2"})
        args["port"] = free_port()
        rotated = worker.rpc("remote-host-start-auto", {**args,"replace":True})
        self.assertNotEqual(rotated["fingerprint"], first["fingerprint"])
        self.assertEqual(rotated["peers"], [])

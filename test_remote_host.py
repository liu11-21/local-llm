from contextlib import closing
from http.client import HTTPSConnection
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from threading import Event
from uuid import uuid4

from desktop_worker import Desktop
from remote_host import PROTOCOL, private_ip


def make_certificate(folder, ip="127.0.0.1"):
    pwsh = shutil.which("pwsh")
    if not pwsh:
        raise unittest.SkipTest("PowerShell 7 is needed to create isolated test certificates")
    script = f"""
      $ErrorActionPreference='Stop'
      $key=[Security.Cryptography.RSA]::Create(2048)
      $request=[Security.Cryptography.X509Certificates.CertificateRequest]::new('CN=Local LLM Test',$key,
        [Security.Cryptography.HashAlgorithmName]::SHA256,[Security.Cryptography.RSASignaturePadding]::Pkcs1)
      $san=[Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder]::new()
      $san.AddIpAddress([Net.IPAddress]::Parse('{ip}'))
      $request.CertificateExtensions.Add($san.Build())
      $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($true,$false,0,$true))
      $request.CertificateExtensions.Add([Security.Cryptography.X509Certificates.X509SubjectKeyIdentifierExtension]::new($request.PublicKey,$false))
      $now=[DateTimeOffset]::UtcNow
      $cert=$request.CreateSelfSigned($now.AddMinutes(-10),$now.AddDays(1))
      [IO.File]::WriteAllText((Join-Path (Get-Location) 'cert.pem'),$cert.ExportCertificatePem())
      [IO.File]::WriteAllText((Join-Path (Get-Location) 'key.pem'),$key.ExportPkcs8PrivateKeyPem())
    """
    subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", script], cwd=folder,
                   capture_output=True, check=True, timeout=20)
    return folder / "cert.pem", folder / "key.pem"


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipIf(os.environ.get("LOCALLLM_TEST_TLS_INTERCEPTED") == "1",
                 "Machine security software substitutes the loopback TLS certificate")
class HostProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = TemporaryDirectory()
        cls.addClassCleanup(folder.cleanup)
        cls.cert, cls.key = make_certificate(Path(folder.name))

    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.worker = Desktop(Path(folder.name))
        self.addCleanup(self.worker.close)
        self.host = self.worker.remote_host
        self.host.engine_status = lambda: {"accepting": True, "installed": True, "busy": False, "error": None}
        self.host.model_names = lambda: ["demo.gguf"]
        self.port = free_port()
        self.host.start("127.0.0.1", self.port, "Test host", str(self.cert), str(self.key))
        self.context = ssl.create_default_context(cafile=str(self.cert))
        self.context.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN

    def request(self, method, path, body=None, token=None, protocol=PROTOCOL, context=None):
        headers = {"X-LocalLLM-Protocol": str(protocol)}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with closing(HTTPSConnection("127.0.0.1", self.port, context=context or self.context, timeout=5)) as client:
            client.request(method, path, json.dumps(body).encode() if body is not None else None, headers)
            with client.getresponse() as response:
                raw = response.read()
                return response.status, (raw if path.endswith("/events") else json.loads(raw))

    def pair(self):
        import base64
        code = json.loads(base64.urlsafe_b64decode(self.host.issue()))["code"]
        status, grant = self.request("POST", "/v1/pair", {"code":code, "label":"laptop"})
        self.assertEqual(status, 200)
        self.assertEqual(self.request("POST", "/v1/pair", {"code":code, "label":"laptop"})[0], 403)
        return grant

    def test_verified_transport_revocation_and_management_isolation(self):
        self.assertEqual(self.request("GET", "/v1/capabilities")[0], 401)
        self.assertEqual(self.request("GET", "/v1/capabilities", protocol=99)[0], 426)
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.request("GET", "/v1/capabilities", context=ssl.create_default_context())
        grant = self.pair()
        token = grant["token"]
        status, cap = self.request("GET", "/v1/capabilities", token=token)
        self.assertEqual((status, cap["models"], cap["kind"]), (200, ["demo.gguf"], "remote-host"))
        self.assertEqual(self.request("POST", "/v1/host/stop", token=token)[0], 404)
        self.assertEqual(self.host.status()["state"], "ready")
        self.host.revoke(grant["peer"])
        self.assertEqual(self.request("GET", "/v1/capabilities", token=token)[0], 401)
        self.host.stop()
        self.assertEqual(self.host.status()["state"], "stopped")
        with self.assertRaises(OSError):
            self.request("GET", "/v1/capabilities", token=token)

    def test_idempotent_queued_and_cancelled_jobs_are_owned(self):
        token, other = self.pair()["token"], self.pair()["token"]
        args = {"model":"demo.gguf", "request":uuid4().hex, "max_tokens":128, "temperature":0.4,
                "messages":[{"role":"user","content":"hello"}]}
        path = "/v1/jobs/" + args["request"]
        with patch.object(self.worker.scheduler, "_dispatch"):
            self.assertEqual(self.request("POST", "/v1/jobs", args, token)[0], 202)
            self.assertEqual(self.request("POST", "/v1/jobs", args, token)[0], 202)
            self.assertEqual(self.request("POST", "/v1/jobs", {**args, "temperature":0.9}, token)[0], 409)
            self.assertEqual(self.request("GET", path, token=other)[0], 404)
            self.assertEqual(self.request("GET", path, token=token)[1]["state"], "queued")
            self.assertEqual(self.request("POST", path + "/cancel", token=token)[1]["state"], "cancelled")
            self.assertIn(b'cancelled', self.request("GET", path + "/events", token=token)[1])

    def test_private_bind_only(self):
        for forbidden in ("0.0.0.0", "8.8.8.8", "example.com"):
            with self.subTest(forbidden=forbidden), self.assertRaises(ValueError):
                private_ip(forbidden)

    @unittest.skipUnless(os.name == "nt", "DPAPI requires Windows")
    def test_client_pairs_streams_reopens_and_revokes(self):
        from remote_client import RemoteClients
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        client = Desktop(Path(folder.name))
        self.addCleanup(client.close)

        def infer(_data, _cancel, update):
            update(answer="測試回答")

        self.worker.host_chat = infer
        client.rpc("remote-client-pair", {"invite": self.host.issue(), "label":"laptop", "confirmed":True})
        stored = client.remote_clients.get(self.host.id)
        data = {"chat":uuid4().hex, "runtime":stored.id, "model":"demo.gguf", "prompt":"hello", "policy":"auto"}
        with self.assertRaises(ValueError):
            client.perform("chat", data, Event(), lambda **_: None)
        answer = client.perform("chat", {**data, "consent":True}, Event(), lambda **_: None)
        self.assertEqual(answer["answer"], "測試回答")
        self.assertEqual(client.history(data["chat"], with_runtime=True)[-1]["runtime"], stored.id)
        with client.connect() as db:
            self.assertNotIn(stored.token.encode(), bytes(db.execute("SELECT protected FROM remote_client_secrets").fetchone()[0]))
        restored = RemoteClients(client.connect)
        self.assertFalse(restored.get(stored.id).summary()["connected"])
        self.assertTrue(restored.get(stored.id).discover()["connected"])
        self.assertTrue(restored.remove(stored.id)["revoked"])
        self.assertEqual(self.host.status()["peers"], [])

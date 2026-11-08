import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from desktop_worker import Desktop
from runtime_provider import ColabAdapter, Providers, endpoint, route

ROOT = Path(__file__).resolve().parent
PACKAGED = ROOT / "build" / "desktop-worker" / "LocalLLMWorker" / "LocalLLMWorker.exe"


class RuntimePolicyTests(unittest.TestCase):
    def test_never_automatically_sends_to_an_external_runtime(self):
        for policy in ("auto", "local", "performance", "cost", "privacy"):
            with self.subTest(policy=policy):
                self.assertEqual(route(policy, "local"), "local")
                with self.assertRaises(ValueError):
                    route(policy, "provider", True)
        with self.assertRaises(ValueError):
            route("manual", "provider")
        self.assertEqual(route("manual", "provider", True), "provider")

    def test_external_endpoint_rejects_insecure_or_ambiguous_urls(self):
        self.assertEqual(endpoint("https://example.test:8443/v1/"), ("example.test", 8443, "/v1"))
        for url in ("http://localhost", "https://user:password@example.test", "https://example.test/v1?key=foo",
                    "https://example.test:99999/v1", "https://example.test/v1#chat"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                endpoint(url)

    def test_colab_has_no_enabled_tasks_or_provisioning(self):
        adapter = ColabAdapter()
        self.assertFalse(adapter.capabilities()["available"])
        self.assertTrue(adapter.capabilities()["requires_authorization"])
        self.assertEqual(adapter.capabilities()["tasks"], [])
        with self.assertRaises(RuntimeError):
            adapter.submit({"type": "chat"})

    def test_provider_summary_does_not_expose_the_key(self):
        providers = Providers()
        key = "secret-for-test"
        with patch("runtime_provider.OpenAIProvider.discover"):
            summary = providers.connect(dict(kind="remote", label="測試", url="https://example.test/v1", key=key))
        self.assertNotIn(key, json.dumps(summary))
        self.assertNotIn(key, repr(providers.get(summary["id"])))


class ConversationTests(unittest.TestCase):
    def test_persists_completed_exchange_but_not_a_cancelled_exchange(self):
        with TemporaryDirectory() as directory:
            desktop = Desktop(Path(directory))
            chat = "a" * 32
            cancel = Event()
            provider = unittest.mock.Mock()
            provider.stream.return_value = (part for part in ("繁體", "中文"))
            events = []
            data = dict(prompt="你好", model="demo", chat=chat, policy="manual", runtime="test", consent=True)
            with patch.object(desktop.providers, "get", return_value=provider):
                result = desktop.perform("chat", data, cancel, lambda **kw: events.append(kw))
                cancel.set()
                provider.stream.return_value = (part for part in ("不應保存",))
                desktop.perform("chat", data, cancel, lambda **kw: None)
            self.assertEqual(result["answer"], "繁體中文")
            self.assertIn({"answer": "繁體"}, events)
            restored = Desktop(Path(directory))
            self.assertEqual(restored.history(chat), [
                {"role": "user", "content": "你好"}, {"role": "assistant", "content": "繁體中文"}])


@unittest.skipUnless(PACKAGED.is_file(), "Build the Windows onedir worker first.")
class PackagedWorkerTests(unittest.TestCase):
    def test_binary_handles_utf8_and_returns_safe_ipc_errors(self):
        with TemporaryDirectory() as directory:
            requests = b'{"op":"colab","data":{}}\n{"op":"missing","data":{}}\n'
            completed = subprocess.run([str(PACKAGED), "--data", directory],
                                       input=requests, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, timeout=20, check=True)
            first, second = [json.loads(row) for row in completed.stdout.splitlines()]
            self.assertTrue(first["ok"])
            self.assertFalse(first["value"]["available"])
            self.assertFalse(second["ok"])
            self.assertIn("未支援", second["error"])


if __name__ == "__main__":
    unittest.main()

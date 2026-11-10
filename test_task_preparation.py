from pathlib import Path
from tempfile import TemporaryDirectory
from time import time
import unittest
from unittest.mock import patch

from desktop_worker import Desktop
from runtime_provider import OpenAIProvider


class PreparationTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.worker = Desktop(Path(directory.name))
        self.addCleanup(self.worker.close)

    def check(self, task, runtime, model, policy="auto", **extra):
        return self.worker.rpc("task-preflight", {
            "task":task, "targets":[{"runtime":runtime, "model":model}], "policy":policy, **extra})

    def test_text_install_and_model_requirements(self):
        with patch("web_bridge.engine_path", return_value=None):
            result = self.check("chat", "local", "missing.gguf")
        self.assertEqual(len(result["blockers"]), 2)
        self.assertEqual(result["transfers"], [])

    def test_policy_and_cost_are_shown_without_contacting_provider(self):
        provider = OpenAIProvider("1"*32, "cloud", "Provider", "example.test", 443, "/v1", "key",
                                  ["model"], True, int(time()))
        self.worker.providers.items[provider.id] = provider
        with patch.object(provider, "request", side_effect=AssertionError("preflight must remain local")):
            self.assertTrue(self.check("chat", provider.id, "model")["blockers"])
            result = self.check("chat", provider.id, "model", policy="manual")
            self.assertEqual(result["blockers"], [])
            self.assertEqual(result["transfers"][0]["cost"], "unknown")
            self.assertNotIn("key", repr(result))
            self.assertTrue(self.check("chat", provider.id, "missing", policy="manual")["blockers"])
            provider.connected = False
            self.assertTrue(self.check("chat", provider.id, "model", policy="manual")["blockers"])

    def test_creation_uses_live_readiness_and_rejects_external_target(self):
        state = {"state":"missing","port":8188,"missing":["weight"]}
        with patch.object(self.worker, "media_readiness", return_value=state):
            self.assertEqual(self.check("image","local","sd15",port=8188)["media"], state)
            with self.assertRaisesRegex(ValueError, "本機 ComfyUI"):
                self.check("image","1"*32,"sd15",port=8188)

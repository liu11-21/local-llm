from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import Mock, patch

from desktop_worker import Desktop
from tool_registry import Tool, ToolError, ToolRegistry, obj, string


class ToolRegistryTests(TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        self.tool = Tool("sample", "Sample", "Sample description", "1", obj(term=string(24)), obj(value=string(24)))
        self.handler = Mock(return_value={"value": "ok"})
        self.registry.register(self.tool, self.handler)

    def test_registration_schema_and_default_deny(self):
        with self.assertRaises(ValueError):
            self.registry.register(self.tool, self.handler)
        self.assertEqual(self.registry.manifests()[0]["version"], "1")
        for args, allowed, granted, code in (
            ({"term": "x", "command": "Get-ChildItem"}, ["sample"], True, "TOOL_PARAMETERS"),
            ({"term": ["x"]}, ["sample"], True, "TOOL_PARAMETERS"),
            ({"term": "x"}, [], True, "TOOL_FORBIDDEN"),
            ({"term": "x"}, ["sample"], False, "TOOL_APPROVAL_REQUIRED"),
        ):
            with self.subTest(code=code), self.assertRaisesRegex(ToolError, code):
                self.registry.execute("sample", args, allowed, Event(), granted=granted)
        self.handler.assert_not_called()
        self.assertEqual(self.registry.execute("sample", {"term": "x"}, ["sample"], Event()), {"value": "ok"})
        self.handler.return_value = {"not": "valid"}
        with self.assertRaisesRegex(ToolError, "TOOL_OUTPUT"):
            self.registry.execute("sample", {"term": "x"}, ["sample"], Event())

    def test_privileged_contract_never_executes(self):
        self.registry.register(Tool("write", "Write", "Writes a file", "1", obj(), obj(),
                                    permission="file-write", modifies_state=True), self.handler)
        with self.assertRaisesRegex(ToolError, "TOOL_FORBIDDEN"):
            self.registry.execute("write", {}, ["write"], Event())
        self.handler.assert_not_called()

    def test_timeout_and_cancel(self):
        began, release, cancel = Event(), Event(), Event()

        def handler(_args, stopped):
            began.set()
            stopped.wait(2)
            release.set()
            return {}

        self.registry.register(Tool("slow", "Slow", "Slow", "1", obj(), obj(), timeout=.06), handler)
        with self.assertRaisesRegex(ToolError, "TOOL_TIMEOUT"):
            self.registry.execute("slow", {}, ["slow"], cancel)
        self.assertTrue(release.wait(1))
        cancel.set()
        with self.assertRaisesRegex(ToolError, "TOOL_CANCELLED"):
            self.registry.execute("slow", {}, ["slow"], cancel)


class AgentPlanTests(TestCase):
    def test_versions_independent_approval_and_restart(self):
        with TemporaryDirectory() as directory:
            desktop = Desktop(Path(directory))
            desktop.models.mkdir()
            (desktop.models / "fixture.gguf").touch()
            form = {"role": "general", "model": "fixture.gguf", "prompt": "Test task", "tools": ["models"]}
            first = desktop.rpc("agent-plan", form)
            other = desktop.rpc("agent-plan", {**form, "prompt": "Second task"})
            self.assertNotEqual(first["id"], other["id"])
            revised = desktop.rpc("agent-plan", {**form, "previous": first["id"], "version": first["version"], "tools": []})
            self.assertEqual(revised["version"], 2)
            with patch.object(desktop.scheduler, "_dispatch"):
                payload = {"action": "agent", "confirmed": True, "id": first["id"]}
                with self.assertRaises(ValueError):
                    desktop.rpc("run", {**payload, "version": 1})
                task = desktop.rpc("run", {**payload, "version": 2})
            reopened = Desktop(Path(directory))
            self.assertEqual(reopened.agent_plans.get(other["id"])["state"], "awaiting_approval")
            self.assertEqual(reopened.agent_plans.get(first["id"])["state"], "interrupted")
            self.assertEqual(reopened.task_list()[0]["id"], task["id"])

    def test_expired_and_revoked_plans_cannot_be_executed(self):
        with TemporaryDirectory() as directory:
            desktop = Desktop(Path(directory))
            desktop.models.mkdir()
            (desktop.models / "fixture.gguf").touch()
            form = {"role": "general", "model": "fixture.gguf", "prompt": "Test task", "tools": []}
            expired = desktop.rpc("agent-plan", form)
            with desktop.agent_plans.edit(expired["id"]) as saved:
                saved["expires_at"] = 0
            cancelled = desktop.rpc("agent-plan", form)
            desktop.rpc("agent-plan-revoke", cancelled)
            self.assertEqual(desktop.agent_plans.get(expired["id"])["state"], "expired")
            for plan in (expired, cancelled):
                with self.assertRaises(ValueError):
                    desktop.rpc("run", {"action": "agent", "id": plan["id"], "version": plan["version"], "confirmed": True})

from pathlib import Path
from dataclasses import replace
import json
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic, sleep
from unittest import TestCase
from unittest.mock import Mock, patch

from desktop_worker import Desktop
from agent_runtime import InvalidDecision, native_decision, parse_decision
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


class AgentRuntimeTests(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.desktop = Desktop(Path(folder.name))
        self.addCleanup(self.desktop.close)
        self.desktop.models.mkdir()
        (self.desktop.models / "fixture.gguf").touch()
        self.desktop.agent_runtime.prepare = Mock()
        self.desktop.local.prompt_tokens = Mock(return_value=100)

    def start(self, *, mode="structured", review=False, steps=5, calls=3, retries=1):
        plan = self.desktop.rpc("agent-plan", {"role": "general", "model": "fixture.gguf", "mode": mode,
            "prompt": "Use the local model list.", "tools": ["models"], "review_calls": review,
            "limits": {"steps": steps, "calls": calls, "retries": retries}})
        task = self.desktop.rpc("run", {"action": "agent", "id": plan["id"], "version": plan["version"],
                                       "confirmed": True})
        return plan["id"], task

    def wait(self, task, state):
        until = monotonic() + 8
        while monotonic() < until:
            job = self.desktop.rpc("job", task)
            if job["state"] == state:
                return job
            if job["state"] in {"completed", "failed", "cancelled"}:
                self.fail(f"Unexpected terminal task state: {job}")
            sleep(.025)
        self.fail(f"Task did not reach {state}: {job}")

    def reply(self, *responses):
        self.desktop.local.stream = Mock(side_effect=[(chunk for chunk in (response,)) for response in responses])

    def test_review_releases_compute_and_only_approved_request_executes(self):
        self.reply('{"type":"tool","tool":"models","arguments":{}}', '{"type":"final","answer":"Done"}')
        key, task = self.start(review=True)
        self.wait(task, "paused")
        plan = self.desktop.agent_plans.get(key)
        self.assertEqual(plan["evidence"], [])
        self.wait(self.desktop.rpc("run", {"action": "engine-stop"}), "completed")
        with self.assertRaises(ValueError):
            self.desktop.rpc("agent-decision", {"id": key, "request": "other", "approved": True})
        decision = {"id": key, "request": plan["pending"]["id"], "approved": True}
        self.desktop.rpc("agent-decision", decision)
        self.wait(task, "completed")
        plan = self.desktop.agent_plans.get(key)
        self.assertEqual(plan["evidence"], [{"tool": "models", "output": ["fixture.gguf"]}])
        self.assertEqual(plan["answer"], "Done")
        observations = json.loads(self.desktop.local.stream.call_args.args[0][-1]["content"])["observations"]
        self.assertEqual(observations, plan["evidence"])
        with self.assertRaises(ValueError):
            self.desktop.rpc("agent-decision", decision)

    def test_denial_and_cancel_do_not_run_tool(self):
        self.reply('{"type":"tool","tool":"models","arguments":{}}', '{"type":"final","answer":"No data"}',
                   '{"type":"tool","tool":"models","arguments":{}}')
        key, task = self.start(review=True)
        self.wait(task, "paused")
        pending = self.desktop.agent_plans.get(key)["pending"]
        self.desktop.rpc("agent-decision", {"id": key, "request": pending["id"], "approved": False})
        self.wait(task, "completed")
        plan = self.desktop.agent_plans.get(key)
        self.assertEqual(plan["evidence"], [])
        self.assertIn("TOOL_REJECTED", [item.get("code") for item in plan["events"]])
        key, task = self.start(review=True)
        self.wait(task, "paused")
        self.desktop.rpc("cancel", task)
        self.wait(task, "cancelled")
        self.assertIsNone(self.desktop.agent_plans.get(key)["pending"])
        self.assertEqual(self.desktop.agent_plans.get(key)["evidence"], [])

    def test_failed_tools_and_bounds_keep_completed_evidence(self):
        self.reply('{"type":"tool","tool":"models","arguments":{}}',
                   '{"type":"tool","tool":"powershell","arguments":{"command":"Get-ChildItem"}}',
                   '{"type":"tool","tool":"models","arguments":{"path":"C:/Windows"}}')
        key, task = self.start(steps=3)
        self.assertIn("AGENT_LIMIT", self.wait(task, "failed")["message"])
        plan = self.desktop.agent_plans.get(key)
        self.assertEqual(len(plan["evidence"]), 1)
        self.assertEqual([item["code"] for item in plan["events"] if item["kind"] == "tool_failed"],
                         ["TOOL_UNKNOWN", "TOOL_PARAMETERS"])

    def test_json_is_strict_and_invalid_retries_are_bounded(self):
        for raw in ('prefix {"type":"final","answer":"ok"}',
                    '{"type":"final","answer":"one","answer":"two"}', '{"type":"tool","tool":"a","arguments":NaN}'):
            with self.assertRaises(InvalidDecision):
                parse_decision(raw)
        self.reply("invalid first", "invalid second")
        key, task = self.start()
        self.assertIn("AGENT_FORMAT", self.wait(task, "failed")["message"])
        self.assertEqual(sum(item["kind"] == "model_format_error" for item in self.desktop.agent_plans.get(key)["events"]), 2)

    def test_native_fragments_use_exact_schema_and_return_tool_message(self):
        def delta(**values):
            return {"choices": [{"delta": values}]}

        def fragments():
            yield delta(tool_calls=[{"index": 0, "id": "call_1", "type": "function",
                                     "function": {"name": "models", "arguments": "{"}}])
            yield delta(tool_calls=[{"index": 0, "function": {"arguments": "}"}}])

        with self.assertRaises(InvalidDecision):
            native_decision(iter([delta(tool_calls=[{"index": 1}])]))
        self.desktop.local.completion_events = Mock(side_effect=[fragments(), (item for item in [delta(content="Done")])])
        key, task = self.start(mode="native")
        self.wait(task, "completed")
        messages = self.desktop.local.completion_events.call_args.args[0]
        self.assertEqual(messages[-1]["role"], "tool")
        self.assertEqual(messages[-1]["tool_call_id"], "call_1")
        self.assertEqual(self.desktop.agent_plans.get(key)["answer"], "Done")

    def test_approval_expires_and_paused_plan_is_interrupted_on_reopen(self):
        self.reply('{"type":"tool","tool":"models","arguments":{}}', '{"type":"tool","tool":"models","arguments":{}}')
        key, task = self.start(review=True)
        self.wait(task, "paused")
        pending = self.desktop.agent_plans.get(key)["pending"]
        with self.desktop.agent_plans.edit(key) as plan:
            plan["deadline"] = 0
        self.assertEqual(self.desktop.rpc("agent-plan-get", {"id": key})["state"], "failed")
        with self.assertRaises(ValueError):
            self.desktop.rpc("agent-decision", {"id": key, "request": pending["id"], "approved": True})
        second, job = self.start(review=True)
        self.wait(job, "paused")
        reopened = Desktop(self.desktop.data)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.agent_plans.get(second)["state"], "interrupted")
        self.assertIsNone(reopened.agent_plans.get(second)["pending"])

    def test_changed_tool_contract_invalidates_saved_preview(self):
        plan = self.desktop.rpc("agent-plan", {"role": "general", "model": "fixture.gguf",
                                               "prompt": "Test", "tools": ["models"]})
        tool, handler = self.desktop.agent_tools.entries["models"]
        self.desktop.agent_tools.entries["models"] = replace(tool, version="2"), handler
        with self.assertRaisesRegex(ValueError, "AGENT_TOOL_CHANGED"):
            self.desktop.rpc("run", {"action": "agent", "id": plan["id"], "version": plan["version"], "confirmed": True})

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic, sleep
from unittest import TestCase
from unittest.mock import Mock, patch

from desktop_worker import Desktop
from team_workflow import node, specification, templates


class TeamWorkflowTests(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.desktop = Desktop(Path(folder.name))
        self.addCleanup(self.desktop.close)
        self.desktop.models.mkdir()
        (self.desktop.models / "fixture.gguf").touch()
        self.desktop.prepare = Mock()
        self.desktop.local.prompt_tokens = Mock(return_value=100)

    def form(self, template="research"):
        team = next(item for item in templates() if item["id"] == template)
        for member in team["members"]:
            member["model"] = "fixture.gguf"
        return team

    def start(self, team, **options):
        return self.desktop.rpc("run", {"action": "team-workflow", "team": team, "prompt": "Common prompt", **options})

    def wait(self, task, state):
        until = monotonic() + 8
        while monotonic() < until:
            job = self.desktop.rpc("job", task)
            if job["state"] == state:
                return self.desktop.rpc("team-run-get", {"id": job["team_run_id"]})
            if job["state"] in {"completed", "failed", "cancelled"}:
                self.fail(f"Unexpected task state: {job}")
            sleep(.02)
        self.fail(f"Task did not reach {state}: {job}")

    def test_modes_supply_isolated_context_and_dependency_outputs(self):
        inputs = []

        def stream(messages, **_):
            self.assertEqual([item["role"] for item in messages], ["system", "user"])
            content = json.loads(messages[-1]["content"])
            inputs.append(content)
            yield f"Output {len(inputs)}"

        self.desktop.local.stream = stream
        for key, order, dependency_counts in (
            ("research", ["draft1", "draft2", "draft3", "final"], [0, 0, 0, 3]),
            ("document", ["brief", "delegate1", "delegate2", "final"], [0, 1, 2, 2]),
            ("code", ["draft", "review", "revision", "final"], [0, 1, 2, 3]),
        ):
            with self.subTest(template=key):
                inputs.clear()
                result = self.wait(self.start(self.form(key)), "completed")
                self.assertEqual([item["id"] for item in result["nodes"]], order)
                self.assertEqual([len(item["dependencies"]) for item in inputs], dependency_counts)
                self.assertEqual(result["answer"], f"Output {len(order)}")
                self.assertTrue(all(item["common_task"] == "Common prompt" for item in inputs))
                self.assertEqual([item["role"] for item in inputs],
                    [next(member["role"] for member in result["spec"]["members"] if member["id"] == step["agent"])
                     for step in result["nodes"]])

    def test_reviewer_failure_skips_revision_and_preserves_draft(self):
        def stream(messages, **_):
            content = json.loads(messages[-1]["content"])
            if content["role"] == "reviewer":
                raise RuntimeError("Review unavailable")
            yield "Usable partial result"

        self.desktop.local.stream = stream
        result = self.wait(self.start(self.form("code")), "completed")
        self.assertEqual([item["state"] for item in result["nodes"]], ["completed", "failed", "skipped", "completed"])
        self.assertIn("Review unavailable", result["nodes"][1]["error"])
        self.assertEqual(result["nodes"][0]["text"], "Usable partial result")

    def test_invalid_dags_and_budget_do_not_schedule(self):
        team = self.form("code")
        team.update(mode="custom", final="second")
        for dependencies in (["missing"], ["second"]):
            team["nodes"] = [node("first", "m1", "First", "Work", dependencies),
                             node("second", "m2", "Second", "Work", ["first"])]
            with self.assertRaises(ValueError):
                self.start(team)
        team["members"][0]["steps"] = 1
        team["nodes"] = [node("first", "m1", "First", "Work"),
                         node("second", "m1", "Second", "Work", ["first"])]
        with self.assertRaises(ValueError):
            self.start(team)
        self.assertEqual(self.desktop.rpc("team-runs", {}), [])

    def test_settings_read_write_and_template_is_independent(self):
        form = self.form()
        saved = self.desktop.rpc("team-config-save", {"team": form})
        form["members"][0]["goal"] = "Edited goal"
        self.desktop.rpc("team-config-save", {"id": saved["id"], "team": form})
        reopened = Desktop(self.desktop.data)
        self.assertEqual(reopened.rpc("team-configs", {})[0]["members"][0]["goal"], "Edited goal")
        self.assertEqual(self.form()["members"][0]["goal"], "")

    def test_external_and_tool_permissions_are_checked_before_scheduling(self):
        form = self.form()
        form["members"][1]["runtime"] = "external"
        with patch.object(self.desktop.providers, "get") as get:
            with self.assertRaises(ValueError):
                self.start(form, policy="manual", consent=False)
            get.assert_not_called()
        form["members"][0]["tools"] = ["models"]
        with self.assertRaisesRegex(ValueError, "本機工具"):
            self.start(form, policy="manual", consent=True, confirm_tools=True)
        form["members"][1]["runtime"] = "local"
        with self.assertRaisesRegex(ValueError, "核准"):
            self.start(form, confirm_tools=False)
        self.assertEqual(self.desktop.rpc("team-runs", {}), [])

    def test_shared_lane_and_cancelled_run_persists_completed_node(self):
        second_node, release = Event(), Event()
        self.addCleanup(release.set)

        def stream(messages, *, cancel, **_):
            content = json.loads(messages[-1]["content"])
            if content["role"] == "reviewer":
                second_node.set()
                while not release.is_set() and not cancel.wait(.05):
                    pass
            if not cancel.is_set():
                yield "Saved draft"

        self.desktop.local.stream = stream
        first = self.start(self.form("code"))
        self.assertTrue(second_node.wait(5))
        other = self.start(self.form("research"))
        self.assertEqual(self.desktop.rpc("job", other)["state"], "queued")
        self.desktop.rpc("cancel", first)
        cancelled = self.wait(first, "cancelled")
        self.assertEqual(cancelled["nodes"][0]["text"], "Saved draft")
        self.assertEqual(cancelled["nodes"][1]["state"], "cancelled")
        release.set()
        self.wait(other, "completed")

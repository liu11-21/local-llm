import json
from pathlib import Path
from sqlite3 import OperationalError
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic, sleep
from unittest import TestCase

from desktop_worker import Desktop
from media import workflow_options
from task_manager import TaskManager


def wait_for(manager, task_id, state):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        snapshot = manager.snapshot(task_id)
        if snapshot["state"] == state:
            return snapshot
        sleep(0.01)
    raise AssertionError(f"Expected {state}, got {manager.snapshot(task_id)}")


def url(name):
    return f"https://huggingface.co/example/repo/resolve/main/{name}.gguf"


class TaskManagerTests(TestCase):
    def test_downloads_overlap_chat_while_second_compute_waits(self):
        release = Event()
        started = {key: Event() for key in ("first", "second", "chat", "team")}

        def perform(action, payload, stop, progress):
            started[payload.get("test", action)].set()
            if not release.wait(5):
                raise TimeoutError()

        manager = TaskManager(perform)
        self.addCleanup(manager.close)
        self.addCleanup(release.set)
        first = manager.submit("download", {"url": url("first"), "test": "first"})["id"]
        second = manager.submit("download", {"url": url("second"), "test": "second"})["id"]
        chat = manager.submit("chat", {"chat": "abc"})["id"]
        team = manager.submit("team", {})["id"]
        for name in ("first", "second", "chat"):
            self.assertTrue(started[name].wait(2), name)
        self.assertEqual(manager.snapshot(team)["state"], "queued")
        with self.assertRaises(ValueError):
            manager.submit("download", {"url": url("first")})
        with self.assertRaises(ValueError):
            manager.submit("chat", {"chat": "abc", "runtime": "remote"})
        self.assertEqual(manager.snapshot(team, cancel=True)["state"], "cancelled")
        release.set()
        for task_id in (first, second, chat):
            wait_for(manager, task_id, "completed")
        self.assertFalse(started["team"].is_set())

    def test_failed_download_can_retry_and_transient_history_error_does_not_stall(self):
        attempt = 0

        def perform(action, payload, stop, progress):
            nonlocal attempt
            attempt += 1
            progress(answer="private response")
            if attempt == 1:
                raise OSError("Connection reset")
            return {"message": "saved"}

        def save(record):
            self.assertNotIn("private", json.dumps(record))
            if record["state"] == "running":
                raise OperationalError("database temporarily busy")

        manager = TaskManager(perform, save)
        self.addCleanup(manager.close)
        task_id = manager.submit("download", {"url": url("model"), "prompt": "private input"})["id"]
        wait_for(manager, task_id, "failed")
        self.assertTrue(manager.list()[0]["retryable"])
        second = manager.retry(task_id)["id"]
        self.assertNotEqual(second, task_id)
        wait_for(manager, second, "completed")
        self.assertIsNone(manager.list()[0]["history_warning"])

    def test_restart_recovers_saved_task_and_preserves_existing_rows(self):
        with TemporaryDirectory() as directory:
            first = Desktop(Path(directory))
            with first.connect() as db:
                db.execute("INSERT INTO tasks(id,action,state,message) VALUES('old','chat','done','saved')")
                db.execute("INSERT INTO chats(id,title) VALUES('example','Keep this chat')")
            first.save_task(dict(id="new", action="download", kind="download", state="running",
                                 message="Downloading", created="2026-11-09T00:00:00+00:00"))
            reopened = Desktop(Path(directory))
            records = {record["id"]: record for record in reopened.task_list()}
            self.assertEqual(records["old"]["state"], "completed")
            self.assertEqual(records["new"]["state"], "interrupted")
            self.assertFalse(records["new"]["retryable"])
            self.assertEqual(reopened.rpc("chats", {}), [("example", "Keep this chat")])

    def test_workflow_options_validate_type_kind_and_steps(self):
        self.assertEqual(workflow_options("image", "sd15-preview", {"width": 512})["width"], 512)
        for kind, workflow, options in (("music", "sd15-preview", {}), ("image", "sd15-preview", {"width": 513}),
                                        ("image", "sd15-preview", {"seed": True})):
            with self.subTest(options=options), self.assertRaises(ValueError):
                workflow_options(kind, workflow, options)

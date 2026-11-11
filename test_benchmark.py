"""Controlled framework regressions; native hardware evidence is collected separately."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from benchmark_adapters import Budget
from benchmark_core import BenchmarkStore, fingerprint, parameters, statistics
from desktop_worker import Desktop


class StatisticsTests(unittest.TestCase):
    def test_warm_statistics_exclude_first_and_warmup(self):
        samples = [{"phase":"first","latency_ms":1000},{"phase":"warmup","latency_ms":500}]
        samples += [{"phase":"measured","latency_ms":value} for value in (1,2,3,4,5)]
        result = statistics(samples)
        self.assertEqual(result["count"],5)
        self.assertEqual(result["p50_ms"],3)
        self.assertEqual(result["p95_ms"],4.8)
        self.assertAlmostEqual(result["stddev_ms"],2**.5)
        self.assertIsNone(statistics([]))
        with self.assertRaises(ValueError):
            statistics([{"phase":"measured","latency_ms":float("nan")}])

    def test_defaults_and_bounded_workloads(self):
        params,workloads = parameters({},"text")
        self.assertEqual((params["warmup"],params["iterations"],len(workloads)),(3,10,2))
        self.assertNotEqual(fingerprint(workloads[0]),fingerprint(workloads[1]))
        for data in ({"iterations":100},{"timeout":0},{"memory_mib":True}):
            with self.assertRaises(ValueError):
                parameters(data,"text")

    def test_budget_timeout_does_not_cancel_user_event(self):
        stop = Event()
        budget = Budget(stop,0)
        self.assertTrue(budget.is_set())
        with self.assertRaises(TimeoutError):
            budget.check()
        self.assertFalse(stop.is_set())
        stop.set()
        with self.assertRaises(InterruptedError):
            budget.check()


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.app = Desktop(Path(self.tmp.name))

    def tearDown(self):
        self.app.close()
        self.tmp.cleanup()

    def test_persistence_exports_filters_delete_recovery_and_chat_survival(self):
        store = self.app.benchmarks.store
        with self.app.connect() as db:
            db.execute("INSERT INTO chats(id,title) VALUES('keep','old chat')")
        identity = store.create("test","openvino",{"workloads":[{"sha256":"safe"}]})
        store.begin(identity,{"comparison_key":"a"})
        run = store.start_run(identity,"CPU",{"backend_version":"controlled"})
        store.measurement(run,{"workload":"a","phase":"measured","latency_ms":2,"input_tokens":11})
        self.assertEqual(len(store.list(device="CPU")),1)
        self.assertEqual(store.list(model="other"),[])
        with self.assertRaises(ValueError):
            store.delete(identity)
        with self.app.connect() as db:
            BenchmarkStore.initialize(db)
            self.assertEqual(db.execute("SELECT title FROM chats WHERE id='keep'").fetchone()[0],"old chat")
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0],11)
        result = store.get(identity)
        self.assertEqual(result["state"],"interrupted")
        self.assertEqual(result["runs"][0]["state"],"interrupted")
        self.assertEqual(len(result["runs"][0]["measurements"]),1)
        self.assertEqual(json.loads(store.export(identity,"json"))["id"],identity)
        self.assertIn("11",store.export(identity,"csv"))
        exported = self.app.benchmarks.export({"id":identity,"format":"json"})
        self.assertTrue(Path(exported["path"]).is_file())
        store.delete(identity)
        self.assertEqual(store.list(),[])

    def test_explicit_confirmation_devices_and_private_payload(self):
        plan = {"models":[{"id":"text","kind":"text","engine":"openvino"}]}
        with patch.object(self.app.benchmarks,"plan",return_value=plan):
            data = {"model":"text","engine":"openvino","devices":["CPU"]}
            with self.assertRaises(ValueError):
                self.app.benchmarks.prepare(data)
            with self.assertRaises(ValueError):
                self.app.benchmarks.prepare({**data,"confirmed":True,"devices":["HETERO:CPU,GPU"]})
            payload = self.app.benchmarks.prepare({**data,"confirmed":True})
        saved = json.dumps(self.app.benchmarks.store.get(payload["benchmark_id"]))
        self.assertNotIn("sky looks blue",saved)
        self.assertNotIn('"prompt"',saved)

    def test_queue_cancel_keeps_record_without_running_adapter(self):
        started,release = Event(),Event()
        original = self.app.scheduler.execute
        def execute(action,data,stop,update):
            if action=="controlled":
                started.set()
                release.wait(3)
                return {}
            return original(action,data,stop,update)
        self.app.scheduler.execute = execute
        self.app.scheduler.submit("controlled",{})
        self.assertTrue(started.wait(2))
        try:
            with patch.object(self.app.benchmarks,"plan",return_value={"models":[{"id":"text","kind":"text","engine":"openvino"}]}):
                job = self.app.benchmarks.submit({"model":"text","engine":"openvino","devices":["CPU"],"confirmed":True})
            self.assertEqual(self.app.scheduler.snapshot(job["id"])["state"],"queued")
            self.app.scheduler.snapshot(job["id"],cancel=True)
            self.assertEqual(self.app.benchmarks.store.get(job["benchmark_id"])["state"],"cancelled")
        finally:
            release.set()
            for task in list(self.app.scheduler.tasks.values()):
                if task.thread:
                    task.thread.join(timeout=3)


if __name__=="__main__":
    unittest.main()

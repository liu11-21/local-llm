"""Controlled framework regressions; native hardware evidence is collected separately."""
from contextlib import contextmanager
import gc
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
import unittest
import weakref
from unittest.mock import patch

from benchmark_adapters import Budget
from benchmark_core import BenchmarkStore, comparable, fingerprint, parameters, statistics
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
        self.assertIn("model_hashes",store.export(identity,"csv"))
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
            class InputBuffer(list):
                pass
            private_inputs = InputBuffer([[[1,2,3]]])
            retained = weakref.ref(private_inputs)
            with patch.object(self.app.benchmarks,"plan",return_value={"models":[{"id":"tensor","kind":"tensor","engine":"openvino"}]}):
                job = self.app.benchmarks.submit({"model":"tensor","engine":"openvino","devices":["CPU"],"confirmed":True,
                                                  "workloads":[{"inputs":private_inputs}]})
            del private_inputs
            self.assertEqual(self.app.scheduler.snapshot(job["id"])["state"],"queued")
            self.app.scheduler.snapshot(job["id"],cancel=True)
            self.assertEqual(self.app.benchmarks.store.get(job["benchmark_id"])["state"],"cancelled")
            gc.collect()
            self.assertIsNone(retained(),"Cancelled private tensor inputs must not be retained by task callbacks")
        finally:
            release.set()
            for task in list(self.app.scheduler.tasks.values()):
                if task.thread:
                    task.thread.join(timeout=3)

    def run_controlled(self,execute,*,free=8*1024**3):
        # This adapter fixture measures no hardware; native acceptance has a separate script.
        with patch.object(self.app.benchmarks,"plan",return_value={"models":[{"id":"text","kind":"text","engine":"openvino"}]}):
            payload = self.app.benchmarks.prepare({"model":"text","engine":"openvino","devices":["CPU"],"confirmed":True,"warmup":0,"iterations":2})
        metadata = {"hashes":{"weights":"known-hash"},"kind":"text","bytes":1024}
        self.app.hardware_monitor.refresh_thread = None
        with patch.object(self.app.openvino,"validate_model",return_value=(Path(self.tmp.name),metadata)), \
             patch.object(self.app.openvino,"installed",return_value=True), \
             patch.object(self.app.hardware_monitor,"snapshot",return_value={"devices":[]}), \
             patch('benchmark_service.detect_hardware',return_value=SimpleNamespace(ram_available=free)), \
             patch('benchmark_service.OpenVINOBenchmark.run',side_effect=execute):
            try:
                self.app.benchmarks.run(payload,Event(),lambda **_:None)
            except RuntimeError:
                pass
        return self.app.benchmarks.store.get(payload["benchmark_id"])

    def test_progressive_raw_data_survives_backend_failure(self):
        def execute(_model,_device,_params,_workloads,_windows,_budget,receive):
            receive({"event":"environment","backend_version":"controlled"})
            receive({"event":"measurement","workload":"short","phase":"measured","index":0,"latency_ms":2})
            raise ValueError("private model input must never be logged")
        result = self.run_controlled(execute)
        self.assertEqual(result["state"],"failed")
        self.assertEqual(len(result["runs"][0]["measurements"]),1)
        self.assertNotIn("private model",json.dumps(result))

    def test_timeout_and_cancel_are_distinct(self):
        for cancel,expected in ((False,"timeout"),(True,"cancelled")):
            def execute(_model,_device,_params,_workloads,_windows,budget,receive):
                receive({"event":"measurement","workload":"short","phase":"measured","index":0,"latency_ms":2})
                if cancel:
                    budget.stop.set()
                else:
                    budget.deadline = 0
                budget.check()
            result = self.run_controlled(execute)
            self.assertEqual(result["state"],expected)
            self.assertEqual(result["runs"][0]["state"],expected)
            self.assertEqual(len(result["runs"][0]["measurements"]),1)

    def test_insufficient_memory_never_starts_inference(self):
        execute = unittest.mock.Mock()
        result = self.run_controlled(execute,free=1)
        self.assertEqual(result["message"],"INSUFFICIENT_MEMORY")
        self.assertFalse(execute.called)

    def test_completed_summary_and_unknown_placement_remain_separate(self):
        def execute(_model,_device,_params,_workloads,_windows,_budget,receive):
            receive({"event":"environment","backend_version":"controlled"})
            receive({"event":"preparation","requested_precision":"backend-default"})
            for workload in ("short","long"):
                for phase in ("first","measured","measured"):
                    receive({"event":"measurement","workload":workload,"phase":phase,"index":0,"latency_ms":3})
            return {"evidence":{"verified_inference":False,"fallback":"unknown"}}
        result = self.run_controlled(execute)
        self.assertEqual(result["state"],"completed")
        run = result["runs"][0]
        self.assertEqual(run["summary"]["short"]["count"],2)
        self.assertEqual(run["summary"]["long"]["count"],2)
        self.assertFalse(run["evidence"]["verified_inference"])
        self.assertTrue(comparable(result,result)["comparable"])
        result2 = json.loads(json.dumps(result))
        result2["config"]["comparison_key"] = "different-quantization"
        self.assertFalse(comparable(result,result2)["comparable"])
        result2["engine"] = "other"
        self.assertGreaterEqual(len(comparable(result,result2)["reasons"]),2)

    def test_incomplete_adapter_result_is_not_successful_benchmark(self):
        def execute(*_args):
            return {"evidence":{"verified_inference":True}}
        result = self.run_controlled(execute)
        self.assertEqual(result["state"],"failed")
        self.assertEqual(result["runs"][0]["error"],"INCOMPLETE_MEASUREMENTS")


if __name__=="__main__":
    unittest.main()

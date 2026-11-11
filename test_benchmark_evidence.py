from copy import deepcopy
from datetime import datetime,timezone
import unittest

from benchmark_evidence import describe,evaluate


def fixture(device="GPU"):
    session = {"id":"session","model":"model","engine":"openvino","state":"completed","created":"2026-11-11T00:00:00+00:00",
        "config":{"model_hashes":{"weights":"abc"},"quantization":"FP32","parameters":{"context":2048,"max_tokens":32,"memory_mib":4096,"iterations":2},
                  "workloads":[{"id":"short","sha256":"workload-hash"}]}}
    run = {"id":"run","device":device,"state":"completed","environment":{"cpu":"CPU-id","machine":"AMD64",
        "environment":{"backend_version":"2025.4.1","mapping":{"state":"verified","windows_id":"gpu-luid","driver":"1"}},
        "preparation":{"requested_precision":"f32"}},"evidence":{"verified_inference":True,"execution_devices":[device],"fallback":"none-reported"},
        "measurements":[{"phase":"first","workload":"short","latency_ms":10}]+[{"phase":"measured","workload":"short","latency_ms":10,"output_correct":True} for _ in range(2)],
        "summary":{"short":{"mean_ms":10,"count":2}}}
    usage = {"workload":"short","workload_sha256":"workload-hash","parameters":describe(session,run)["parameters"].copy()}
    return session,run,describe(session,run),usage


class EvidenceTests(unittest.TestCase):
    def result(self,session,run,current,usage,days=0):
        now = datetime(2026,11,11,tzinfo=timezone.utc).timestamp()+days*86400
        return evaluate(session,run,current,usage,now=now)

    def test_current_does_not_imply_full_operator_allocation(self):
        result = self.result(*fixture())
        self.assertEqual(result["freshness"],"current")
        self.assertEqual(result["comparability"],"partially_comparable")
        self.assertTrue(result["eligible_for_ranking"])
        self.assertFalse(result["full_operator_allocation_verified"])

    def test_driver_update_is_stale_without_deleting_history(self):
        session,run,current,usage = fixture()
        current["driver"] = "2"
        result = self.result(session,run,current,usage)
        self.assertEqual(result["freshness"],"stale")
        self.assertFalse(result["eligible_for_ranking"])
        self.assertEqual(run["environment"]["environment"]["mapping"]["driver"],"1")

    def test_weights_backend_engine_quantization_and_device_changes(self):
        for key,value in (("model_hashes",{"weights":"changed"}),("backend_version","new"),("engine","other"),
                          ("quantization","INT4"),("device_identity",{"id":"other-gpu"})):
            session,run,current,usage = fixture()
            current[key] = value
            result = self.result(session,run,current,usage)
            self.assertEqual(result["freshness"],"invalidated",key)
            self.assertEqual(result["comparability"],"not_comparable",key)

    def test_binary_change(self):
        session,run,current,usage = fixture("CPU")
        session["engine"] = current["engine"] = "llama.cpp"
        run["environment"]["environment"]["executable_sha256"] = "old"
        current["executable_sha256"] = "new"
        self.assertIn("executable_sha256",self.result(session,run,current,usage)["changed"])

    def test_workload_and_parameters_are_separate_from_freshness(self):
        for change in ("workload","tokens","batch"):
            session,run,current,usage = fixture()
            if change=="tokens":
                usage["parameters"]["max_tokens"] = 2048
            else:
                usage["workload_sha256"] = "different-input-or-batch"
            result = self.result(session,run,current,usage)
            self.assertEqual(result["freshness"],"current")
            self.assertEqual(result["comparability"],"not_comparable")

    def test_partial_missing_samples_and_bad_output(self):
        for mode in ("partial","samples","output"):
            session,run,current,usage = fixture()
            if mode=="partial":session["state"]="partial"
            if mode=="samples":run["measurements"].pop()
            if mode=="output":run["measurements"][1]["output_correct"]=False
            self.assertFalse(self.result(session,run,current,usage)["eligible_for_ranking"])

    def test_missing_identity_is_unknown_not_slow(self):
        session,run,current,usage = fixture()
        current["device_identity"] = None
        result = self.result(session,run,current,usage)
        self.assertEqual(result["freshness"],"unknown")
        self.assertIsNone(result["summary"])

    def test_npu_placement_unknown_is_not_npu_benchmark(self):
        session,run,current,usage = fixture("NPU")
        run["evidence"]["verified_inference"] = False
        result = self.result(session,run,current,usage)
        self.assertFalse(result["eligible_for_ranking"])
        self.assertEqual(result["comparability"],"insufficient_evidence")

    def test_backend_only_evidence_is_limited_and_fallback_is_rejected(self):
        session,run,current,usage = fixture()
        run["evidence"]["verified_inference"] = False
        self.assertEqual(self.result(session,run,current,usage)["comparability"],"partially_comparable")
        run["evidence"]["execution_devices"] = ["CPU"]
        result = self.result(session,run,current,usage)
        self.assertTrue(result["cpu_fallback"])
        self.assertFalse(result["eligible_for_ranking"])

    def test_age_is_advisory_not_invalidated(self):
        result = self.result(*fixture(),days=31)
        self.assertEqual(result["freshness"],"stale")
        self.assertEqual(result["changed"],[])
        self.assertIn("age-advisory",result["stale_reasons"])

    def test_batch_sampling_and_missing_first_run_are_not_equivalent(self):
        for key,value in (("batch",8),("temperature",.8),("ignore_eos",False),("do_sample",True)):
            session,run,current,usage=fixture()
            usage["parameters"][key]=value
            self.assertFalse(self.result(session,run,current,usage)["eligible_for_ranking"])
        session,run,current,usage=fixture()
        run["measurements"]=run["measurements"][1:]
        self.assertFalse(self.result(session,run,current,usage)["eligible_for_ranking"])


if __name__=="__main__":unittest.main()

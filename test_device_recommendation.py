"""Controlled decision inputs, never hardware performance evidence."""
from copy import deepcopy
from types import SimpleNamespace
from time import time
from unittest.mock import patch
import unittest

from device_recommendation import DeviceRecommendations
from runtime_contract import capability,observed
from runtime_recommendation import recommend


def candidate(id="CPU",**changes):
    return {"id":id,"device":id,"runtime":"local","engine":"llama.cpp","model":"model","availability":"ready",
            "executable":True,"network":False,"cost":"no-api-fee","evidence":[],**changes}


def evidence(latency=10,decode=50,group="same",**changes):
    return {"eligible_for_ranking":True,"execution_device_verified":False,"comparability":"partially_comparable",
            "condition_key":group,"summary":{"mean_ms":latency,"decode_tokens_per_s":decode},"limitations":["Placement unknown"],**changes}


class RecommendationTests(unittest.TestCase):
    def test_missing_measurement_is_not_zero_or_slowest(self):
        result = recommend([candidate(evidence=[evidence()]),candidate("GPU"),candidate("NPU",availability="incompatible",executable=False)])
        self.assertIsNone(result["comparison"])
        self.assertIsNone(result["candidates"][1]["performance"])
        self.assertIn("目前無法確定",result["candidates"][0]["reasons"][-1])

    def test_latency_and_decode_are_different_objectives(self):
        candidates = [candidate(evidence=[evidence(20,200)]),candidate("GPU",evidence=[evidence(10,100)])]
        self.assertEqual(recommend(candidates,preference="speed")["recommended"],"GPU")
        self.assertEqual(recommend(candidates,preference="speed",objective="decode")["recommended"],"CPU")
        self.assertEqual(recommend(candidates)["candidates"][0]["evidence_level"],"backend-benchmark-limited")

    def test_incompatible_backend_or_quantization_not_ranked(self):
        result = recommend([candidate(evidence=[evidence(group="quant-a")]),candidate("GPU",evidence=[evidence(group="quant-b")])],preference="speed")
        self.assertIsNone(result["comparison"])

    def test_stale_evidence_not_ranked(self):
        result = recommend([candidate(evidence=[evidence(eligible_for_ranking=False)])])
        self.assertIsNone(result["candidates"][0]["performance"])

    def test_privacy_cost_local_first_and_energy_are_explained(self):
        choices = [candidate("cloud",network=True,cost="unknown"),candidate()]
        for preference in ("privacy","cost","local-first"):
            result = recommend(choices,preference=preference)
            self.assertEqual(result["recommended"],"CPU")
            self.assertFalse(result["automatic_dispatch"])
        result = recommend(choices,preference="energy")
        self.assertIn("沒有可靠功耗",result["candidates"][0]["uncertainty"][0])

    def test_hard_gate_excludes_faster_but_unavailable_candidate(self):
        result = recommend([candidate(),candidate("GPU",availability="needs-setup",executable=False,evidence=[evidence(1)])])
        self.assertEqual(result["recommended"],"CPU")

    def test_memory_prefers_only_comparable_measured_ram(self):
        choices = [candidate(evidence=[evidence(summary={"mean_ms":10,"peak_ram_bytes":1000})]),
                   candidate("GPU",evidence=[evidence(summary={"mean_ms":20,"peak_ram_bytes":500})])]
        result = recommend(choices,preference="low-memory")
        self.assertEqual(result["recommended"],"GPU")
        self.assertTrue(any("VRAM 未知" in text for text in result["candidates"][1]["reasons"]))


class InventoryGateTests(unittest.TestCase):
    def query(self,*,ram=4*1024**3,npu=False,kind="unified",free=1,driver_age=0):
        now = int(time())
        hardware = {"devices":[{"id":"gpu-id","kind":"gpu","memory_type":kind,
            "vram_available":{"value":free,"status":"available","checked_at":now-driver_age},"driver":{"value":"1"}}]}
        info={"models":[],"devices":[],"engine":False,"openvino":{"installed":True,"devices":["CPU","GPU","NPU"],"models":[{"id":"model"}]},
              "hardware_capabilities":hardware}
        record=capability("openvino","OV","local","OpenVINO",tasks=["chat"],connected=True,models=["model"],network=False,cost="no-api-fee",
                          resources={"ram_available":observed(ram,unit="bytes",checked_at=now)})
        app=SimpleNamespace(rpc=lambda *_:info,runtime_capabilities=lambda *_:[record])
        service=DeviceRecommendations(app)
        descriptor={"kind":"text","ram":1024**3,"bytes":100*1024**2,"npu_candidate":npu}
        with patch.object(service,"history",return_value=[]),patch.object(service,"models",return_value=descriptor), \
             patch.object(service,"identity",side_effect=lambda _engine,device,*_:{"mapping":{"windows_id":"gpu-id"} if device=="GPU" else {}}):
            return service.query({"task":"chat","model":"model"})

    def test_uma_does_not_fail_due_to_small_dedicated_memory(self):
        result=self.query()
        gpu=next(item for item in result["candidates"] if item["device"]=="GPU")
        self.assertTrue(gpu["executable"])
        self.assertEqual(gpu["resource"]["memory_type"],"unified")

    def test_single_discrete_vram_shortage_and_stale_monitoring(self):
        result=self.query(kind="dedicated")
        self.assertFalse(next(item for item in result["candidates"] if item["device"]=="GPU")["executable"])
        result=self.query(kind="dedicated",driver_age=100)
        gpu=next(item for item in result["candidates"] if item["device"]=="GPU")
        self.assertTrue(any("過期" in text for text in gpu["uncertainty"]))

    def test_npu_incompatible_is_rejected_and_ram_shortage_explained(self):
        result=self.query(ram=1)
        npu=next(item for item in result["candidates"] if item["device"]=="NPU")
        self.assertEqual(npu["availability"],"incompatible")
        self.assertFalse(any(item["executable"] for item in result["candidates"]))


if __name__=="__main__":unittest.main()

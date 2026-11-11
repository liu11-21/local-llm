from copy import deepcopy
from time import time
from unittest import TestCase

from resource_contract import gpu_memory, reading
from runtime_contract import capability
from runtime_recommendation import compare


class ResourceContractTests(TestCase):
    def gpu(self, brand="Intel", memory="dedicated", sampled=100):
        return {"id":"gpu-1","kind":"gpu","name":brand,"vendor":brand,"memory_type":memory,
                "vram_total":reading(8*1024**3,unit="bytes",checked_at=sampled),
                "vram_available":reading(6*1024**3,unit="bytes",checked_at=sampled),
                "shared_limit":reading(16*1024**3,unit="bytes",checked_at=sampled)}

    def test_dedicated_pools_are_current_identified_and_never_summed(self):
        for brand in ("NVIDIA","AMD","Intel"):
            hardware = {"devices":[self.gpu(brand)]}
            self.assertEqual(gpu_memory(hardware,105)[1]["value"],6*1024**3)
            self.assertEqual(gpu_memory(hardware,116),(None,None))
            self.assertEqual(gpu_memory(hardware,99),(None,None))
            self.assertEqual(gpu_memory({"devices":hardware["devices"]*2},105),(None,None))
        self.assertEqual(gpu_memory(None,105),(None,None))

    def test_unified_memory_never_uses_the_shared_limit_as_available(self):
        gpu = self.gpu(memory="unified")
        gpu["vram_available"] = reading(128*1024**2,checked_at=100,unit="bytes")
        self.assertEqual(gpu_memory({"devices":[gpu]},105),(None,None))
        record = capability("local","Local","local","Local LLM",connected=True,health="ready",tasks=["image"],
                            formats=["safetensors"],engines=["ComfyUI"],cost="no-api-fee")
        record["hardware"] = {"devices":[gpu]}
        result = compare(record,"image","sd15",vram=4*1024**3,now=105)
        self.assertFalse(any("低於" in risk for risk in result["risks"]))
        self.assertTrue(any("統一記憶體" in reason for reason in result["unknown"]))
        self.assertFalse(result["inference_verified"])
        self.assertEqual(result["requirements"]["vram"]["evidence"],"estimated")

    def test_runtime_reported_legacy_memory_is_not_relabelled_as_dedicated(self):
        record = capability("local","Local","local","Local LLM",tasks=["chat"],models=["m"],engines=["llama.cpp"],
                            health="ready",cost="no-api-fee",resources={"vram_available":reading(99*1024**3,"reported")})
        result = compare(record,"chat","m",vram=1024,now=105)
        self.assertTrue(any("記憶體池" in text for text in result["unknown"]))
        self.assertFalse(any("達到" in text for text in result["reasons"]))

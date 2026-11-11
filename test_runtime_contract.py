import unittest

from runtime_contract import capability, colab_capability, external_capability, fresh, observed, validate
from runtime_recommendation import compare


class RuntimeContractTests(unittest.TestCase):
    def test_health_is_specific_to_the_requested_task_and_still_requires_freshness(self):
        host = capability("host","Desk","remote-host","Local LLM",connected=True,network=True,health="unhealthy",
                          tasks=["chat","image"],models=["demo"],cost="no-api-fee",checked_at=100,
                          media={"image":{"state":"ready","installed":True,"workflows":["sd15"]}},
                          task_health={"chat":"unhealthy","image":"ready"})
        self.assertTrue(compare(host,"image","sd15",ram=1,now=105)["unknown"])
        self.assertEqual(compare(host,"image","sd15",ram=1,now=105)["risks"],[])
        self.assertTrue(compare(host,"chat","demo",now=105)["risks"])
        self.assertTrue(compare(host,"image","sd15",now=170)["needs_connection"])
        host["task_health"] = {"chat":"ready","image":"unhealthy"}
        self.assertEqual(compare(host,"chat","demo",now=105)["risks"],[])
        self.assertTrue(compare(host,"image","sd15",now=105)["risks"])
        with self.assertRaises(ValueError):
            validate({**host,"task_health":{"video":"ready"}})

    def test_version_optional_features_and_unknown_resources(self):
        record = capability("local", "Local", "local", "Local LLM", checked_at=100)
        self.assertEqual(record["resources"]["vram_available"], observed())
        self.assertIsNone(record["features"]["stream"])
        self.assertEqual(record["cost"], "unknown")
        self.assertTrue(fresh(record, 160))
        self.assertFalse(fresh(record, 161))
        self.assertFalse(fresh(record, 99))
        self.assertEqual(validate({**record, "future_field": "ignored"}), record)
        with self.assertRaisesRegex(ValueError, "版本"):
            validate({**record, "schema": 2})

    def test_rejects_fake_unknown_and_invalid_resource_types(self):
        for value in (observed(0, "unknown"), observed(True), observed(-1), observed(2**60)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                capability("local", "Local", "local", "Local LLM", resources={"ram_available": value})
        self.assertEqual(capability("local", "Local", "local", "Local LLM",
                                   resources={"ram_available": observed(0)})["resources"]["ram_available"]["value"], 0)

    def test_external_and_colab_do_not_invent_hardware_or_cost(self):
        provider = {"id":"id", "label":"Provider", "kind":"cloud", "host":"example.org", "port":443, "models":["model"],
                    "connected":False}
        result = external_capability(provider)
        self.assertEqual((result["health"], result["cost"], result["kind"]), ("offline", "unknown", "cloud-api"))
        self.assertIsNone(result["resources"]["gpus"]["value"])
        self.assertEqual(colab_capability(False)["tasks"], ["notebook"])

    def test_resource_comparison_and_privacy_are_explanatory(self):
        values = {"health":"ready", "connected":True, "tasks":["chat"], "models":["demo"],
                  "formats":["GGUF"], "engines":["llama.cpp"], "cost":"no-api-fee", "checked_at":100}
        local = capability("local", "Local", "local", "Local LLM", **values,
                           resources={"ram_available":observed(8)})
        host = capability("host", "Host", "remote-host", "Local LLM", **values, network=True,
                          resources={"ram_available":observed(32, "reported")})
        self.assertTrue(compare(local, "chat", "demo", ram=4, now=105)["recommended"])
        self.assertFalse(compare(local, "chat", "demo", ram=12, now=105)["recommended"])
        result = compare(host, "chat", "demo", ram=12, now=105)
        self.assertTrue(result["recommended"])
        self.assertTrue(result["needs_consent"])
        self.assertTrue(compare(host, "chat", "demo", ram=12, now=175)["needs_connection"])
        self.assertEqual(compare(host, "chat", "demo", policy="privacy", now=105)["state"], "incompatible")
        self.assertEqual(compare(host, "chat", "demo", vram=1, now=105)["state"], "uncertain")
        self.assertTrue(compare(local, "chat", "missing", ram=4, now=105, installable=True)["needs_install"])
        self.assertEqual(compare(local, "chat", "missing", now=105)["state"], "incompatible")

    def test_unknown_cost_and_bad_health_do_not_get_recommended(self):
        cloud = capability("cloud", "Cloud", "cloud-api", "Provider", health="unhealthy", connected=True,
                           tasks=["chat"], models=["demo"], network=True, checked_at=100)
        result = compare(cloud, "chat", "demo", now=105)
        self.assertIn("費用未知。", result["unknown"])
        self.assertFalse(result["recommended"])
        self.assertIsNone(result["may_charge"])
        self.assertEqual(compare(cloud, "chat", "demo", policy="cost", now=105)["state"], "incompatible")

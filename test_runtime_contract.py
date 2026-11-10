import unittest

from runtime_contract import capability, colab_capability, external_capability, fresh, observed, validate


class RuntimeContractTests(unittest.TestCase):
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

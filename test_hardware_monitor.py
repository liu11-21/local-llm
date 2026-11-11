from copy import deepcopy
from unittest import TestCase
from unittest.mock import Mock, patch

from hardware_contract import validate_hardware
from hardware_monitor import HardwareMonitor, counter_values, npu_devices, reading
from hardware_providers import probe
from runtime_contract import capability, validate


class HardwareMonitorTests(TestCase):
    def monitor(self, *, rows=(), devices=None):
        adapter = {"id":"00000000_00000001","name":"Test GPU","vendor":"Intel","kind":"gpu",
                   "vram_total":reading(128),"shared_limit":reading(4096)}
        counter = Mock()
        counter.sample.return_value = {"engines":[("pid_2_luid_0x0_0x1_phys_0_eng_0_engtype_3D",7)],
                                       "dedicated":[("luid_0x0_0x1_phys_0",64)],
                                       "shared":[("luid_0x0_0x1_phys_0",2048)]}
        monitor = HardwareMonitor(inventory=Mock(return_value=list(rows)),
                                  adapters=Mock(return_value=[adapter] if devices is None else devices),
                                  counters=Mock(return_value=counter),windows=True)
        self.addCleanup(monitor.close)
        monitor.refresh_inventory()
        return monitor,counter

    def test_dedicated_shared_multigpu_and_device_aggregation(self):
        rows = [("pid_1_luid_0x0_0x1_phys_0_eng_0_engtype_3D",30),
                ("pid_2_luid_0x0_0x1_phys_0_eng_0_engtype_3D",40),
                ("pid_1_luid_0x0_0x1_phys_0_eng_1_engtype_Copy",55),
                ("pid_3_luid_0x0_0x2_phys_0_eng_0_engtype_3D",100)]
        self.assertEqual(counter_values(rows,"00000000_00000001",engines=True),70)
        self.assertEqual(counter_values(rows,"00000000_00000002",engines=True),100)
        self.assertIsNone(counter_values(rows,"00000000_00000003",engines=True))
        monitor,_ = self.monitor()
        snapshot = validate_hardware(monitor.snapshot())
        gpu = snapshot["devices"][0]
        self.assertEqual(gpu["vram_total"]["value"],128)
        self.assertEqual(gpu["vram_available"]["value"],64)
        self.assertEqual(gpu["shared_used"]["value"],2048)
        self.assertFalse(snapshot["npu_present"]["value"])

    def test_monitoring_failures_do_not_invent_zero_or_reinitialize_repeatedly(self):
        monitor,counter = self.monitor()
        counter.sample.side_effect = OSError("unavailable")
        first = monitor.snapshot()
        self.assertIsNone(first["devices"][0]["utilization"]["value"])
        self.assertIs(monitor.snapshot(),first)
        monitor.counter_factory.assert_called_once()
        counter.close.assert_called_once()
        monitor.cached = None
        monitor.snapshot()
        monitor.counter_factory.assert_called_once()

    def test_no_npu_is_distinct_from_failed_inventory_and_unknown_accelerator(self):
        monitor,_ = self.monitor()
        self.assertFalse(monitor.snapshot()["npu_present"]["value"])
        monitor.inventory.side_effect = OSError("denied")
        monitor.refresh_inventory()
        self.assertIsNone(monitor.snapshot()["npu_present"]["value"])
        self.assertEqual(npu_devices([{"id":"x","class":"ComputeAccelerator","name":"Unknown accelerator"}])[0]["kind"],"accelerator")
        self.assertEqual(npu_devices([{"id":"cpu","class":"Processor","name":"Intel Core Ultra"}]),[])

    def test_three_npu_vendors_and_driver_errors_remain_unverified(self):
        rows = [{"id":"intel","class":"ComputeAccelerator","name":"Intel(R) AI Boost","problem":0,"driver":"1.0"},
                {"id":"amd","class":"ComputeAccelerator","name":"AMD IPU Device","problem":28},
                {"id":"qualcomm","class":"NeuralProcessor","name":"Qualcomm Hexagon NPU","problem":0}]
        monitor,_ = self.monitor(rows=rows)
        snapshot = validate_hardware(monitor.snapshot())
        npus = [device for device in snapshot["devices"] if device["kind"]=="npu"]
        self.assertEqual([device["vendor"] for device in npus],["Intel","AMD","Qualcomm"])
        self.assertEqual(npus[1]["driver_state"]["value"],28)
        self.assertTrue(snapshot["npu_present"]["value"])
        self.assertTrue(all(not device["verified_inference"] and device["utilization"]["value"] is None for device in npus))

    def test_runtime_contract_rejects_fabricated_and_unbounded_metrics(self):
        monitor,_ = self.monitor()
        record = capability("local","Local","local","Local LLM",hardware=monitor.snapshot())
        self.assertEqual(validate(record),record)
        for value in (True,-1,float("nan"),101):
            invalid = deepcopy(record)
            invalid["hardware"]["devices"][0]["utilization"] = reading(value)
            with self.subTest(value=value),self.assertRaises(ValueError):
                validate(invalid)
        invalid = deepcopy(record)
        invalid["hardware"]["devices"][0]["vram_used"] = {"value":12,"source":"unknown","status":"available"}
        with self.assertRaises(ValueError):
            validate(invalid)

    def test_nonwindows_and_missing_provider_are_safe(self):
        monitor = HardwareMonitor(windows=False)
        self.addCleanup(monitor.close)
        self.assertEqual(validate_hardware(monitor.snapshot())["state"],"unsupported")
        with patch("hardware_providers.importlib.util.find_spec",return_value=None):
            self.assertTrue(all(item["state"]=="missing" and not item["verified_inference"] for item in probe()))

    def test_provider_errors_and_cpu_enumeration_are_not_npu_verification(self):
        module = Mock(__version__="test")
        module.Core.return_value.available_devices = ["CPU"]
        module.get_available_providers.side_effect = RuntimeError("driver not available")
        with patch("hardware_providers.importlib.util.find_spec",return_value=True), \
             patch("hardware_providers.importlib.import_module",return_value=module):
            records = probe()
        self.assertEqual(records[0]["devices"],["CPU"])
        self.assertFalse(records[0]["verified_inference"])
        self.assertEqual(records[1]["state"],"initialization-failed")

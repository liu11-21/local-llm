from threading import Event
from unittest import TestCase
from unittest.mock import Mock

from engine_health import EngineHealth


class EngineHealthTests(TestCase):
    def test_process_and_api_health_are_distinct(self):
        running = Mock(return_value=True)
        probe = Mock(return_value=False)
        health = EngineHealth(running, probe)
        self.assertEqual(health.snapshot(False)["state"], "not_installed")
        self.assertEqual(health.snapshot(True)["state"], "installed")
        with health.transition(True):
            self.assertEqual(health.snapshot(True)["state"], "starting")
        self.assertEqual(health.snapshot(True, busy=True)["state"], "busy")
        health.check(health.generation)
        self.assertEqual(health.snapshot(True)["code"], "ENGINE_API_UNAVAILABLE")
        self.assertFalse(health.usable())
        probe.return_value = True
        health.check(health.generation)
        self.assertEqual(health.snapshot(True)["state"], "ready")
        running.return_value = False
        self.assertEqual(health.snapshot(True)["code"], "ENGINE_PROCESS_EXIT")

    def test_timeout_cancel_and_manual_stop_have_distinct_results(self):
        health = EngineHealth(lambda: False, lambda: False)
        with self.assertRaises(TimeoutError), health.transition(True):
            raise TimeoutError()
        self.assertEqual(health.snapshot(True)["code"], "ENGINE_TIMEOUT")
        cancel = Event()
        cancel.set()
        with self.assertRaises(InterruptedError), health.transition(True, cancel):
            raise InterruptedError()
        self.assertEqual(health.snapshot(True)["state"], "stopped")
        with health.transition(False):
            self.assertEqual(health.snapshot(True)["state"], "stopping")
        self.assertEqual(health.snapshot(True)["state"], "stopped")

    def test_late_probe_cannot_replace_new_lifecycle_state(self):
        health = EngineHealth(lambda: True, lambda: False)
        with health.transition(True):
            pass
        generation = health.generation
        with health.transition(False):
            pass
        health.check(generation)
        self.assertEqual(health.snapshot(True)["state"], "stopped")

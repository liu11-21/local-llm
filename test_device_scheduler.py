"""Controlled admission tests; CPU/GPU/NPU names here are not hardware evidence."""
from threading import Event
from time import monotonic,sleep
import unittest

from device_resources import ResourceDemand,admission
from task_manager import TaskManager


def demand(device,ram=30,**kwargs):
    return ResourceDemand(device=device,ram=ram,exclusive=(device,),**kwargs)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.started={key:Event() for key in ("CPU","GPU","GPU2","NPU","shared","later")}
        self.release={key:Event() for key in self.started}
        self.snapshot={"ram_available":100,"vram":{"GPU":100,"GPU2":100},"external":[]}
        def execute(action,data,stop,update):
            key=data["key"]
            self.started[key].set()
            while not self.release[key].wait(.01):
                if stop.is_set():raise InterruptedError("controlled stop")
            if data.get("fail"):raise ValueError("controlled failure")
            return {}
        self.manager=TaskManager(execute)
        self.manager.resource_snapshot=lambda:self.snapshot

    def tearDown(self):
        self.manager.close()
        for event in self.release.values():event.set()
        for task in list(self.manager.tasks.values()):
            if task.thread:task.thread.join(timeout=2)

    def submit(self,key,claim,**extra):
        return self.manager.submit("controlled",{"key":key,**extra},demand=claim)["id"]

    def terminal(self,id):
        end=monotonic()+3
        while monotonic()<end:
            value=self.manager.snapshot(id)
            if value["state"] not in ("queued","running"):return value
            sleep(.01)
        self.fail("Task did not release its resources")

    def test_cpu_gpu_and_distinct_discrete_gpus_can_run_in_parallel(self):
        for key in ("CPU","GPU","GPU2"):
            self.submit(key,demand(key,vram=((key,30),) if key!="CPU" else ()))
            self.assertTrue(self.started[key].wait(1))
        self.assertEqual(sum(task["state"]=="running" for task in self.manager.list()),3)

    def test_controlled_cpu_npu_parallel_not_a_real_npu_claim(self):
        self.submit("CPU",demand("CPU",cpu_load=60,bandwidth=40))
        self.submit("NPU",demand("NPU",cpu_load=20,bandwidth=50))
        self.assertTrue(self.started["CPU"].wait(1));self.assertTrue(self.started["NPU"].wait(1))

    def test_ram_queue_and_cancel_release_then_recover(self):
        first=self.submit("CPU",demand("CPU",ram=70))
        second=self.submit("GPU",demand("GPU",ram=70))
        self.assertEqual(self.manager.snapshot(second)["state"],"queued")
        self.assertIn("RAM_BUDGET",self.manager.snapshot(second)["message"])
        self.manager.snapshot(first,cancel=True)
        self.assertEqual(self.terminal(first)["state"],"cancelled")
        self.assertTrue(self.started["GPU"].wait(1))

    def test_same_engine_and_shared_memory_conflicts_queue(self):
        for resource in ("engine:shared","unified:accelerator"):
            with self.subTest(resource=resource):
                first=self.submit("GPU",ResourceDemand(device="GPU",ram=30,exclusive=(resource,)))
                second=self.submit("NPU",ResourceDemand(device="NPU",ram=30,exclusive=(resource,)))
                self.assertEqual(self.manager.snapshot(second)["state"],"queued")
                self.manager.snapshot(first,cancel=True);self.terminal(first)
                self.manager.snapshot(second,cancel=True);self.terminal(second)

    def test_vram_pools_unknown_and_bandwidth_do_not_overcommit(self):
        allowed,reason=admission(demand("GPU",vram=(("GPU",101),)),[],self.snapshot)
        self.assertFalse(allowed);self.assertIn("VRAM_BUDGET",reason)
        allowed,reason=admission(demand("GPU",vram=(("missing",1),)),[],self.snapshot)
        self.assertFalse(allowed);self.assertIn("VRAM_UNKNOWN",reason)
        allowed,reason=admission(demand("NPU",bandwidth=60),[("other",demand("GPU",bandwidth=60))],self.snapshot)
        self.assertFalse(allowed);self.assertIn("SHARED_BANDWIDTH",reason)

    def test_failure_timeout_shutdown_and_queued_cancel_release(self):
        failed=self.submit("CPU",demand("CPU"),fail=True)
        self.release["CPU"].set()
        self.assertEqual(self.terminal(failed)["state"],"failed")
        timed=self.submit("GPU",demand("GPU",seconds=1))
        self.assertIn("SCHEDULER_TIMEOUT",self.terminal(timed)["error"])
        queued=self.submit("GPU2",demand("GPU2",ram=200))
        self.manager.snapshot(queued,cancel=True)
        self.assertEqual(self.manager.snapshot(queued)["state"],"cancelled")
        running=self.submit("NPU",demand("NPU"))
        self.assertTrue(self.started["NPU"].wait(1))
        self.manager.close()
        self.assertEqual(self.terminal(running)["state"],"interrupted")

    def test_comfyui_blocks_gpu_benchmark_and_stop_is_not_deadlocked(self):
        self.snapshot["external"]=[("comfyui-resident",ResourceDemand(engine="ComfyUI"))]
        benchmark=self.manager.submit("benchmark",{"benchmark_id":"controlled","key":"GPU"})["id"]
        self.assertEqual(self.manager.snapshot(benchmark)["state"],"queued")
        self.manager.tasks[benchmark].queued_at-=60
        stop=self.manager.submit("comfy-stop",{"key":"later"})["id"]
        self.assertTrue(self.started["later"].wait(1))
        self.snapshot["external"]=[]
        self.release["later"].set();self.terminal(stop)
        self.assertTrue(self.started["GPU"].wait(1))

    def test_unknown_gpu_identity_locks_all_gpu_backends(self):
        first=self.submit("GPU",ResourceDemand(device="Vulkan0",exclusive=("gpu:*",)))
        second=self.submit("GPU2",ResourceDemand(device="GPU.1",exclusive=("gpu:luid-2",)))
        self.assertEqual(self.manager.snapshot(second)["state"],"queued")
        self.manager.snapshot(first,cancel=True);self.terminal(first)
        self.assertTrue(self.started["GPU2"].wait(1))

    def test_long_cpu_queue_does_not_starve_an_unrelated_gpu(self):
        self.submit('CPU',demand('cpu:host'))
        queued=self.submit('later',demand('cpu:host'))
        self.manager.tasks[queued].queued_at-=60
        gpu=self.submit('GPU',demand('gpu:separate',ram=20))
        self.assertTrue(self.started['GPU'].wait(1))
        self.assertEqual(self.manager.snapshot(gpu)['state'],'running')
        self.assertEqual(self.manager.snapshot(queued)['state'],'queued')


if __name__=="__main__":unittest.main()

from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic, sleep
import unittest
from uuid import uuid4

from desktop_worker import Desktop
from remote_host import ProtocolError


class RemoteJobsTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name)
        self.worker = self.open()
        self.owner = "1"*32
        self.other = "2"*32
        with self.worker.connect() as db:
            for peer in (self.owner,self.other):
                db.execute("INSERT INTO remote_host_grants VALUES(?,?,?)", (peer,peer,peer*2))

    def open(self):
        worker = Desktop(self.path)
        self.addCleanup(worker.close)
        host = worker.remote_host
        host.state = "ready"
        host.model_names = lambda: ["demo.gguf"]
        host.engine_status = lambda: {"accepting":True}
        return worker

    @staticmethod
    def payload():
        return {"request":uuid4().hex,"model":"demo.gguf","messages":[{"role":"user","content":"private prompt"}],
                "max_tokens":128,"temperature":0.4}

    def test_completed_answer_and_idempotency_survive_restart(self):
        args = self.payload()
        self.worker.host_chat = lambda _data,_stop,update:update(answer="stored reply")
        host = self.worker.remote_host
        host.submit(self.owner,args)
        until = monotonic()+5
        while host.job(self.owner,args["request"])["state"]!="completed" and monotonic()<until:
            sleep(0.02)
        host = self.open().remote_host
        job = host.job(self.owner,args["request"])
        self.assertEqual(job["answer"], "stored reply")
        self.assertNotIn("private prompt", repr(job))
        self.assertEqual(host.submit(self.owner,args), {"id":args["request"]})
        with self.assertRaises(ProtocolError):
            host.submit(self.owner,{**args,"temperature":1})
        with self.assertRaises(ProtocolError):
            host.job(self.other,args["request"])
        host.revoke(self.owner)
        with self.assertRaises(ProtocolError):
            host.job(self.owner,args["request"])

    def test_startup_marks_live_jobs_interrupted_and_caps_each_owner(self):
        started, finish = Event(), Event()
        self.addCleanup(finish.set)

        def execute(_data, _stop, _update):
            started.set()
            finish.wait(4)

        self.worker.host_chat = execute
        host = self.worker.remote_host
        args = self.payload()
        host.submit(self.owner,args)
        self.assertTrue(started.wait(2))
        host.submit(self.owner,self.payload())
        with self.assertRaises(ProtocolError) as issue:
            host.submit(self.owner,self.payload())
        self.assertEqual(issue.exception.status,429)
        reopened = self.open().remote_host
        self.assertEqual(reopened.job(self.owner,args["request"])["state"],"interrupted")
        finish.set()
        until = monotonic()+4
        while any(task["state"] in ("running","queued") for task in self.worker.scheduler.list()) and monotonic()<until:
            sleep(0.02)

"""Controlled Team child scheduling, dependencies, grants and cancellation."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Event,Lock
from time import monotonic,sleep
from types import SimpleNamespace
import unittest

from device_resources import ResourceDemand
from task_manager import TaskManager
from team_dispatch import run_team,run_node
from team_workflow import TeamStore,specification


class TeamDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        @contextmanager
        def connect():
            db=sqlite3.connect(str(Path(self.tmp.name)/'test.sqlite'),timeout=5)
            try:
                with db:yield db
            finally:db.close()
        self.store=TeamStore(connect)
        with connect() as db:self.store.initialize(db)
        self.started,self.release=Event(),Event()
        self.seen=[]
        self.lock=Lock()
        def ask(member,node,deps,prompt,expected,deadline,update):
            with self.lock:
                self.seen.append((member['model'],node['id'],prompt,[item['text'] for item in deps]))
                if len(self.seen)>=2:self.started.set()
            if not deps:
                while not self.release.wait(.01):deadline.check()
            return member['model']+' result '+prompt
        self.app=SimpleNamespace(team_store=self.store,agent_tools=SimpleNamespace(),ask_team_agent=ask)
        def execute(action,data,cancel,update):
            return run_team(self.app,data['id'],cancel,update,data['_task_id']) if action=='team-workflow' else run_node(self.app,data,cancel,update)
        self.manager=TaskManager(execute)
        self.manager.resource_snapshot=lambda:{'ram_available':100,'vram':{},'external':[]}
        self.app.scheduler=self.manager
        def prepare(task,data):
            return SimpleNamespace(demand=ResourceDemand(device=data['execution']['device'],ram=20,exclusive=(data['execution']['device'],)))
        self.app.device_execution=SimpleNamespace(prepare=prepare,submit=lambda action,data,target,**kwargs:self.manager.submit(action,data,demand=target.demand,**kwargs))
        self.spec=specification({'name':'Controlled devices','lead':'m1','mode':'parallel','members':[
            {'id':'m1','name':'CPU member','role':'writer','model':'model-a','runtime':'local','execution':{'device':'CPU','confirmed':True},'tools':[]},
            {'id':'m2','name':'GPU member','role':'analyst','model':'model-b','runtime':'local','execution':{'device':'GPU','confirmed':True},'tools':[]}]},SimpleNamespace())

    def tearDown(self):
        self.manager.close();self.release.set()
        for task in list(self.manager.tasks.values()):
            if task.thread:task.thread.join(timeout=3)
        self.tmp.cleanup()

    def submit(self):
        identity=self.store.create_run(self.spec,'private common task')
        job=self.manager.submit('team-workflow',{'id':identity},demand=ResourceDemand(scope='control',exclusive=()))
        return identity,job['id']

    def terminal(self,id):
        end=monotonic()+5
        while monotonic()<end:
            value=self.manager.snapshot(id)
            if value['state'] not in ('queued','running'):return value
            sleep(.02)
        self.fail('Team did not finish')

    def test_children_parallel_then_final_uses_both_isolated_drafts(self):
        identity,job=self.submit()
        self.assertTrue(self.started.wait(3))
        self.assertEqual({item[0] for item in self.seen},{'model-a','model-b'})
        self.release.set()
        result=self.terminal(job)
        self.assertEqual(result['state'],'completed',result.get('error'))
        run=self.store.get(identity)
        self.assertTrue(all(node['state']=='completed' for node in run['nodes']))
        self.assertEqual(len(self.seen[-1][3]),2)
        self.assertEqual(sum(task.get('parent_id')==job for task in self.manager.list()),3)

    def test_parent_cancel_stops_children_and_releases_all_locks(self):
        identity,job=self.submit()
        self.assertTrue(self.started.wait(3))
        self.manager.snapshot(job,cancel=True)
        self.assertEqual(self.terminal(job)['state'],'cancelled')
        end=monotonic()+3
        while any(task['state']=='running' for task in self.manager.list()) and monotonic()<end:sleep(.02)
        self.assertFalse(any(task['state']=='running' for task in self.manager.list()))
        self.assertTrue(any(node['state']=='cancelled' for node in self.store.get(identity)['nodes']))

    def test_missing_external_grant_does_not_execute_remote_member(self):
        self.spec['members'][1]['runtime']='ungranted-cloud'
        identity,job=self.submit()
        self.release.set()
        result=self.terminal(job)
        run=self.store.get(identity)
        failed=next(item for item in run['nodes'] if item['agent']=='m2')
        self.assertEqual(failed['state'],'failed')
        self.assertIn('TEAM_EXTERNAL_NOT_GRANTED',failed['error'])
        self.assertFalse(any(item[0]=='model-b' for item in self.seen))


if __name__=='__main__':unittest.main()

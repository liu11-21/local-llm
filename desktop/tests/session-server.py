"""Test-only real HTTP host: controlled waiting TaskManager job, never AI inference.

No test control endpoints are added to the shipped application. Expiry is triggered
through a file in this test's owned temporary profile; auth/CSRF remain production.
"""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import sys
import time

parser=argparse.ArgumentParser();parser.add_argument('--app',type=Path,required=True);parser.add_argument('--data',type=Path,required=True);parser.add_argument('--port',type=int,required=True);parser.add_argument('--transport',type=Path)
args=parser.parse_args();sys.path.insert(0,str(args.app))
from web_launcher import official_python,save_state,state_path
from web_environment import ensure_environment
from download_recovery import exclusive
official_python();args.data.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(ensure_environment(args.data)))
from workspace_web import serve

async def main():
    static=args.data/'test-static'
    shutil.copytree(args.app/'desktop/dist',static,dirs_exist_ok=True)
    if args.transport:shutil.copyfile(args.transport,static/'transport-test.js')
    watch=None
    def ready(app,url):
        nonlocal watch
        save_state(args.data,app,url)
        original=app.application.service.scheduler.execute
        def execute(action,data,cancel,update):
            if action!='session-test-wait':return original(action,data,cancel,update)
            while not cancel.wait(.1):update(message='Controlled waiting task; no model or GPU used')
            raise InterruptedError('Controlled task cancelled')
        app.application.service.scheduler.execute=execute
        job=app.application.service.scheduler.submit('session-test-wait',{})
        (args.data/'test-job.json').write_text(json.dumps({'id':job['id']}))
        async def expire():
            while not app.stopping:
                if (args.data/'expire-session').is_file():
                    for session in app.sessions.values():session['expires']=time.monotonic()-1
                    (args.data/'expire-session').unlink()
                await asyncio.sleep(.1)
        watch=asyncio.create_task(expire())
    try:await serve(args.data,args.port,static=static,browser=False,on_ready=ready)
    finally:
        if watch:watch.cancel()
        state_path(args.data).unlink(missing_ok=True)

with exclusive(args.data/'.workspace.lock'):asyncio.run(main())

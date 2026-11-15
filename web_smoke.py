"""Clean ZIP deployment acceptance; no PyInstaller/own EXE execution."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile

from web_launcher import read_state,control
from web_update import update,rollback,selected
from web_environment import verify_distribution,verify_environment
from workspace_version import VERSION


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parent;output=root/'build/v090-deployment';output.mkdir(exist_ok=True)
    bundle=root/f'build/web-release/LocalLLM-Web-{VERSION}-Windows-x64.zip'
    summary={'status':'PASS','scope':'actual official-Python -I -S launch from extracted ZIP; synthetic user data only',
        'self_built_executable_executed':False,'SAC':'NOT VERIFIED; clean Windows is not a SAC-enabled device test'}
    with tempfile.TemporaryDirectory(prefix='v090-clean-',dir=root/'build') as scratch:
        scratch=Path(scratch);extracted=scratch/'installed';extracted.mkdir()
        with zipfile.ZipFile(bundle) as archive:
            assert not any(Path(i.filename).suffix.lower() in ('.exe','.dll','.pyd','.gguf') for i in archive.infolist())
            archive.extractall(extracted)
        app=next(extracted.glob('*/app'));data=scratch/'data';data.mkdir()
        marker=data/'models';marker.mkdir();(marker/'keep.txt').write_bytes(b'keep model')
        if args.baseline:
            old=args.baseline.resolve()
            result=subprocess.run([sys.executable,'-B',str(old/'desktop_worker.py'),'--data',str(data)],
                input='{"op":"build-info","data":{}}\n',text=True,encoding='utf-8',capture_output=True,check=True,timeout=60)
            assert json.loads(result.stdout)['value']['version']=='0.8.0'
            # Seed using the shared probe, after old 0.8 genuinely initialized schema.
            from upgrade_probe import seed
            expected=seed(data);assert expected['source_version']=='0.8.0'
            (output/'upgrade-before.json').write_text(json.dumps(expected,indent=2)+'\n',encoding='utf-8')
        launcher=app/'web_launcher.py';log=(output/'launcher.log').open('w',encoding='utf-8')
        child=subprocess.Popen([sys.executable,'-I','-S','-B',str(launcher),'start','--data',str(data),'--port','18773','--no-browser'],stdout=log,stderr=log)
        try:
            for _ in range(180):
                if read_state(data):break
                if child.poll() is not None:raise RuntimeError('ZIP launcher exited; inspect launcher.log')
                time.sleep(.25)
            assert read_state(data) and control(data)
            summary['first_start']='PASS';summary['distribution']=verify_distribution(app)
            environment=next((data/'web-environments').iterdir());verify_environment(environment)
            summary['pure_dependency_integrity']='PASS'
            duplicate=subprocess.run([sys.executable,'-I','-S','-B',str(launcher),'start','--data',str(data),'--no-browser'],capture_output=True,check=True,timeout=20)
            summary['duplicate_start']='PASS'
            assert control(data,stop=True);child.wait(25);assert child.returncode==0
        finally:
            if child.poll() is None:
                if not control(data,stop=True):child.kill()
                child.wait(25)
            log.close()
        if args.baseline:
            from upgrade_probe import fingerprint
            assert fingerprint(data/'workspace.sqlite3')==expected['tables']
            assert all(hashlib.sha256((data/name).read_bytes()).hexdigest()==sha for name,sha in expected['files'].items())
            backups=list((data/'backups').glob('workspace-pre-090-*.sqlite3'));assert backups
            report={'status':'PASS','source_version':'0.8.0','destination_version':VERSION,'tables':fingerprint(data/'workspace.sqlite3'),'backup_count':len(backups),'files':'preserved'}
            (output/'upgrade-after.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');summary['real_080_upgrade']='PASS'
        with closing(sqlite3.connect(data/'workspace.sqlite3')) as db:
            assert db.execute('SELECT version,minimum_reader FROM workspace_storage').fetchone()==('0.9.0','0.8.0')
        assert (marker/'keep.txt').read_bytes()==b'keep model'
        zipsha=hashlib.sha256(bundle.read_bytes()).hexdigest()
        update(app,bundle,zipsha);assert selected(app)!=app
        # Start the new side-by-side version through the original launcher.
        child=subprocess.Popen([sys.executable,'-I','-S','-B',str(launcher),'start','--data',str(data),'--port','18773','--no-browser'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for _ in range(160):
                if control(data):break
                time.sleep(.25)
            assert control(data);assert control(data,stop=True);child.wait(25);assert child.returncode==0
        finally:
            if child.poll() is None:
                control(data,stop=True);child.wait(25)
        rollback(app);assert selected(app)==app
        summary['update_and_rollback']='PASS: exact ZIP hash, verified manifest, side-by-side launch, original pointer restored; data retained'
        summary['no_PE_payload']='PASS';summary['shutdown']='PASS'
    (output/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()

"""Actual CMD start/stop and interpreter fallbacks, using only owned synthetic data."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from web_launcher import read_state,control
from upgrade_probe import seed,fingerprint

app=Path(os.environ.get('LOCALLLM_WEB_PACKAGE',ROOT)).resolve()
wrapper=app.parent if (app.parent/'Start-Web-Workspace.cmd').is_file() else app
output=ROOT/'build/session-recovery';output.mkdir(parents=True,exist_ok=True)
env={**os.environ,'LOCALLLM_NO_PAUSE':'1'}
result={'status':'PASS','scope':'actual Windows CMD + installed official Python; disposable synthetic profile, not target RTX QA','checks':{}}
system=Path(os.environ['SystemRoot']);minimal=[str(system/'System32'),str(system),str(system/'System32/WindowsPowerShell/v1.0')]
for label,paths in [('PATH without py',[str(Path(sys.executable).parent),*minimal]),('Registry without py or PATH Python',minimal)]:
    probe=subprocess.run(['cmd.exe','/d','/c','Find-Web-Python.cmd'],cwd=wrapper,env={**env,'PATH':os.pathsep.join(paths)},capture_output=True,encoding='utf-8',errors='replace',timeout=40)
    if probe.returncode or not Path(probe.stdout.strip()).is_file():raise AssertionError(label+': '+probe.stderr)
    selected=Path(probe.stdout.strip())
    actual=json.loads(subprocess.check_output([str(selected),'-I','-S','-B','-c','import sys,struct,json;print(json.dumps([list(sys.version_info[:3]),struct.calcsize("P")*8]))'],text=True))
    assert actual[0][:2]==[3,12] and actual[1]==64
    result['checks'][label]={'status':'PASS','version':actual[0],'bits':actual[1]}

with tempfile.TemporaryDirectory(prefix='LocalLLM launcher with spaces ') as folder:
    data=Path(folder).resolve();port=18783;child=None
    log=(output/'launcher-desktop.log').open('w',encoding='utf-8')
    def cmd(name):return ['cmd.exe','/d','/c',name,'--data',str(data),'--port',str(port),'--no-browser']
    def start():
        process=subprocess.Popen(cmd('Start-Web-Workspace.cmd'),cwd=wrapper,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(180):
            if read_state(data) and control(data):
                assert '/launch#bootstrap=' in control(data)
                return process
            if process.poll() is not None:raise AssertionError('CMD start exited; inspect launcher-desktop.log')
            time.sleep(.15)
        raise AssertionError('CMD start timeout')
    def stop(process):
        completed=subprocess.run(cmd('Stop-Web-Workspace.cmd'),cwd=wrapper,env=env,stdout=log,stderr=log,timeout=25)
        assert completed.returncode==0;process.wait(25);assert process.returncode==0
        assert not read_state(data)
        with socket.socket() as probe:probe.bind(('127.0.0.1',port))
    try:
        child=start();pid=read_state(data)['pid']
        duplicate=subprocess.run(cmd('Start-Web-Workspace.cmd'),cwd=wrapper,env=env,stdout=log,stderr=log,timeout=25)
        assert duplicate.returncode==0 and read_state(data)['pid']==pid
        result['checks']['CMD first start and duplicate']='PASS'
        stop(child);result['checks']['CMD stop process and port cleanup']='PASS'
        saved=seed(data)
        # Retain a previously validated SDK setting without repeating Runtime CLI or inference.
        sdk=ROOT/'build/v080-upstream/llama.exe'
        if sdk.is_file():
            (data/'llama-runtime.json').write_text(json.dumps({'kind':'llama-app','path':str(sdk),'sha256':hashlib.sha256(sdk.read_bytes()).hexdigest(),'version':'previously verified b12360; preservation only'}))
        runtime=(data/'llama-runtime.json').read_bytes() if (data/'llama-runtime.json').exists() else None
        child=start();stop(child);result['checks']['CMD restart']='PASS'
        assert fingerprint(data/'workspace.sqlite3')==saved['tables']
        assert all(hashlib.sha256((data/name).read_bytes()).hexdigest()==sha for name,sha in saved['files'].items())
        if runtime is not None:assert (data/'llama-runtime.json').read_bytes()==runtime
        result['checks']['SQLite chats Agent Team library works preservation']='PASS'
        result['checks']['saved Runtime setting preservation']='PASS' if runtime is not None else 'NOT TESTED: no pre-existing SDK on this runner'
        result['runtime_cli_repeated']=False;result['model_downloads']=0;result['inference']=False
        result['python_version']=sys.version.split()[0]
        (output/'PYTHON_LAUNCHER_TESTS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print('PASS actual CMD start/stop/restart, PATH/registry fallback, spaced data path, port cleanup and synthetic data preservation')
    finally:
        if child and child.poll() is None:
            if not control(data,stop=True):child.kill()
            child.wait(25)
        log.close()

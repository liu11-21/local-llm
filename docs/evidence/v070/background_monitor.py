"""Run from any directory: python <this file>. Windows process CPU baseline, no inference."""
import ctypes as ct
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
from queue import Queue
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic,sleep

ROOT=Path(__file__).resolve().parents[3]


def main():
    if os.name!='nt':raise SystemExit('Windows process counters required')
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    kernel.GetProcessTimes.argtypes=(wt.HANDLE,ct.POINTER(wt.FILETIME),ct.POINTER(wt.FILETIME),ct.POINTER(wt.FILETIME),ct.POINTER(wt.FILETIME))
    kernel.GetProcessTimes.restype=wt.BOOL
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    with TemporaryDirectory(prefix='workspace-monitor-') as folder:
        worker=subprocess.Popen([sys.executable,str(ROOT/'desktop_worker.py'),'--data',folder],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        lines=Queue()
        def reader():
            for line in worker.stdout:lines.put(line)
            lines.put(b'')
        thread=Thread(target=reader,daemon=True);thread.start()
        def rpc(op):
            worker.stdin.write((json.dumps({'op':op,'data':{}})+'\n').encode());worker.stdin.flush()
            value=json.loads(lines.get(timeout=40))
            if not value['ok']:raise RuntimeError(value['error'])
            return value['value']
        def cpu():
            times=[wt.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(int(worker._handle),*[ct.byref(value) for value in times]):raise ct.WinError(ct.get_last_error())
            return sum((value.dwHighDateTime<<32)+value.dwLowDateTime for value in times[2:])/10_000_000
        try:
            identity=rpc('build-info');rpc('info')
            until=monotonic()+25
            while monotonic()<until:
                hardware=rpc('system-resources').get('hardware',{})
                if hardware.get('inventory_at') is not None:break
                sleep(1)
            samples=[]
            for mode in ('idle','poll','idle','poll','idle','poll'):
                begin=monotonic();before=cpu();calls=[];next_call=begin
                while monotonic()-begin<7:
                    if mode=='poll' and monotonic()>=next_call:
                        start=monotonic();rpc('system-resources');calls.append((monotonic()-start)*1000);next_call+=3.5
                    sleep(.05)
                elapsed=monotonic()-begin;used=cpu()-before
                samples.append({'mode':mode,'wall_seconds':elapsed,'worker_cpu_ms':used*1000,
                    'cpu_percent_one_core':100*used/elapsed,'cpu_percent_all_logical_cores':100*used/elapsed/os.cpu_count(),'rpc_ms':calls})
        finally:
            worker.stdin.close()
            try:worker.wait(timeout=15)
            except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=5)
            thread.join(timeout=2);worker.stdout.close();worker.stderr.close()
    record={'status':'PASS','source_commit':commit,'identity':identity,'model_inference':False,'cpu_threads':os.cpu_count(),
        'scope':'Windows GetProcessTimes for Worker only, after up to 25s inventory warmup; excludes WebView, external processes and startup; no CPU improvement percentage claimed',
        'hardware_inventory_ready':hardware.get('inventory_at') is not None,
        'poll_interval_seconds':3.5,'samples':samples}
    target=Path(__file__).with_name('background-monitor.json');target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','samples':len(samples),'report':str(target)}))


if __name__=='__main__':main()

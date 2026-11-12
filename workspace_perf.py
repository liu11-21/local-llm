"""Repeated process-cold IPC baseline; synthetic volume is never inference evidence."""
import argparse
import json
import os
from pathlib import Path
from queue import Queue
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import perf_counter
from desktop_worker import Desktop
from workspace_version import build_info


def summary(values):
    ordered=sorted(values)
    return {'unit':'ms','samples':values,'n':len(values),'mean':statistics.mean(values),
            'median':statistics.median(values),'min':ordered[0],'max':ordered[-1]}


def seed(data,chats=2000,works=500):
    app=Desktop(data)
    try:
        with app.connect() as db:
            db.executemany('INSERT INTO chats(id,title) VALUES(?,?)',[(f'{n:032x}',f'Volume chat {n:05d}') for n in range(chats)])
        app.outputs.mkdir(exist_ok=True)
        fixture=(Path(__file__).parent/'desktop/tests/media-fixtures/sample.png').read_bytes()
        for n in range(works):(app.outputs/f'{n:012x}.png').write_bytes(fixture)
    finally:app.close()


def measure(data,repeats,worker=None):
    timings={name:[] for name in ('worker_first_identity','info','home_summary','chats_page','chats_search','works_page','runtime_refresh','resource_sample')}
    for _ in range(repeats):
        command=[str(worker.resolve())] if worker else [sys.executable,str(Path(__file__).with_name('desktop_worker.py'))]
        started=perf_counter()
        process=subprocess.Popen(command+['--data',str(data)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        replies=Queue()
        def read():
            for line in process.stdout:replies.put(line)
            replies.put(b'')
        reader=Thread(target=read,daemon=True);reader.start()
        def rpc(op,options=None):
            process.stdin.write((json.dumps({'op':op,'data':options or {}})+'\n').encode());process.stdin.flush()
            raw=replies.get(timeout=40)
            if not raw:raise RuntimeError('Worker stopped during performance baseline')
            result=json.loads(raw)
            if not result['ok']:raise RuntimeError(result['error'])
            return result['value']
        try:
            identity=rpc('build-info');timings['worker_first_identity'].append((perf_counter()-started)*1000)
            if identity['version']!='0.7.0':raise RuntimeError('Wrong worker baseline version')
            for name,op,options in [('info','info',{}),('home_summary','home-summary',{}),
                ('chats_page','chats-page',{'offset':1000}),('chats_search','chats-page',{'query':'00199'}),
                ('works_page','works-library',{'offset':240}),('runtime_refresh','runtime-capability-refresh',{'id':'local'}),
                ('resource_sample','system-resources',{})]:
                before=perf_counter();value=rpc(op,options);timings[name].append((perf_counter()-before)*1000)
                if name=='chats_page':assert len(value['items'])==50 and value['total']==2000
                if name=='works_page':assert len(value['items'])==24 and value['total']==500
        finally:
            process.stdin.close()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            reader.join(timeout=2);process.stdout.close();process.stderr.close()
    return {key:summary(values) for key,values in timings.items()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repeats',type=int,default=5);parser.add_argument('--worker',type=Path)
    args=parser.parse_args()
    if not 3<=args.repeats<=20:parser.error('use 3..20 repetitions')
    with TemporaryDirectory(prefix='workspace-perf-') as folder:
        data=Path(folder);seed(data);measurements=measure(data,args.repeats,args.worker)
    report={'status':'PASS','build':build_info(),'platform':sys.platform,'cpu_threads':os.cpu_count(),
        'scope':'process-cold; OS disk cache not flushed; production Worker/RPC with synthetic 2000 chats and 500 legal PNG files',
        'ui_render_included':False,'model_inference':False,'measurements':measurements,
        'first_model_load':{'status':'NOT RUN','reason':'No inference is started by baseline; llama.cpp currently blocked by OS application control. Use explicit real acceptance on a permitted model/runtime.'},
        'comparison':'Baseline only; no improvement percentage claimed'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:round(value['median'],2) for key,value in measurements.items()}))


if __name__=='__main__':main()

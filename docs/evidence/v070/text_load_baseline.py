"""Repeat real CPU GenAI load measurements using an already imported model; no downloads."""
import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import openvino_acceptance as acceptance


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True);parser.add_argument('--model',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if not re.fullmatch('[0-9a-f]{16}',args.model):parser.error('Expected an imported text model ID')
    args.output.mkdir(parents=True,exist_ok=True)
    original=acceptance.Desktop;samples=[]
    try:
        for index in range(1,4):
            events=[]
            def factory(path):
                app=original(path);execute=app.openvino.execute
                def observed(request,cancel,update,**options):
                    def capture(event):
                        if event.get('event')=='loaded':events.append(dict(event))
                        update(event)
                    return execute(request,cancel,capture,**options)
                app.openvino.execute=observed
                return app
            acceptance.Desktop=factory
            report=args.output/f'text-cpu-load-run-{index}.json'
            sys.argv=['openvino_acceptance.py','--data',str(args.data.resolve()),'--device','CPU','--model',args.model,'--output',str(report.resolve())]
            with redirect_stdout(StringIO()):acceptance.main()
            value=json.loads(report.read_text(encoding='utf-8'))
            if value['status']!='PASS' or not events or not value['task'].get('answer','').strip():
                raise RuntimeError('Real text generation or load evidence failed')
            samples.append({'task_id':value['task']['id'],'loaded':events[-1],'answer':value['task']['answer'],
                            'model_hashes':value['runs'][0]['details']['model_hashes']})
    finally:acceptance.Desktop=original
    loads=[sample['loaded']['load_ms'] for sample in samples]
    record={'status':'PASS','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'model_id':args.model,'requested_device':'CPU','operator_placement_verified':False,'downloads_started':False,
        'scope':'Actual managed GenAI text pipeline loaded event, including runtime/pipeline/tokenizer initialization; fresh process and temporary import/cache each sample; OS cache not flushed',
        'samples':samples,'load_ms':loads,'median_load_ms':statistics.median(loads),'comparison':'Baseline only, no performance improvement percentage'}
    (args.output/'text-cpu-load-baseline.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','samples':3,'load_ms':loads,'median_load_ms':statistics.median(loads)}))


if __name__=='__main__':main()

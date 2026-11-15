"""Opt-in real model tests through the Web HTTP transport; no paid APIs."""
import argparse
import http.client
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from web_launcher import read_state,control


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--qwen',type=Path,required=True)
    parser.add_argument('--smol',type=Path,required=True);parser.add_argument('--port',type=int,default=18775)
    parser.add_argument('--app',type=Path,help='Optional extracted, hash-verified Web ZIP app directory')
    args=parser.parse_args();root=Path(__file__).resolve().parent;output=root/'build/v090-native';output.mkdir(exist_ok=True)
    (output/'validation.json').unlink(missing_ok=True)
    app=args.app.resolve() if args.app else root
    evidence={'scope':'actual official-Python Web host -> HTTP/SSE -> shared scheduler -> signed llama.app',
        'hardware':'Intel Iris Xe development host; RTX/CUDA/NPU not tested','paid_cloud':'NOT RUN'}
    with tempfile.TemporaryDirectory(prefix='v090-native-',dir=root/'build') as scratch:
        data=Path(scratch).resolve();models=data/'models';models.mkdir()
        for source in (args.qwen,args.smol):shutil.copyfile(source,models/source.name)
        log=(output/'launcher-private.log').open('w',encoding='utf-8')
        child=subprocess.Popen([sys.executable,'-I','-S','-B',str(app/'web_launcher.py'),'start','--data',str(data),'--port',str(args.port),'--no-browser'],stdout=log,stderr=log)
        cookie='';csrf='';origin=f'http://127.0.0.1:{args.port}'
        def request(path,body=None,headers=None):
            connection=http.client.HTTPConnection('127.0.0.1',args.port,timeout=180)
            connection.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body).encode(),headers={
                'Origin':origin,'Content-Type':'application/json','Cookie':cookie,'X-Workspace-CSRF':csrf,**(headers or {})})
            response=connection.getresponse();value=json.loads(response.read());status=response.status;extra=response.getheader('Set-Cookie');connection.close()
            assert status==200 and value['ok'],(status,value)
            return value['value'],extra
        def rpc(op,data={}):return request('/api/rpc',{'op':op,'data':data})[0]
        def wait(job,seconds=180):
            end=time.monotonic()+seconds
            while time.monotonic()<end:
                value=rpc('job',{'id':job['id']})
                if value['state'] not in ('queued','running','paused'):return value
                time.sleep(.15)
            rpc('cancel',{'id':job['id']});raise TimeoutError('Native Web acceptance task timed out')
        def run(action,body,seconds=180):
            value=wait(rpc('run',{'action':action,**body}),seconds);assert value['state']=='completed',value
            return value
        try:
            for _ in range(180):
                state=read_state(data)
                if state:break
                if child.poll() is not None:raise RuntimeError('Native launcher failed')
                time.sleep(.25)
            assert state
            session,raw=request('/api/session',{},headers={'X-Workspace-Bootstrap':state['bootstrap']});cookie=raw.split(';')[0];csrf=session['csrf']
            evidence['application_build']=session['build']
            status=rpc('runtime-select',{'kind':'llama-app','path':str(args.runtime.resolve()),'confirmed':True})
            evidence['runtime']={'version':status['selection']['version'],'sha256':status['selection']['sha256'],
                'authenticode':status['trust']['authenticode'],'devices':status['selection']['devices']}
            common={'model':args.qwen.name,'runtime':'local','policy':'local','mode':'cpu','context':2048,'temperature':0}
            off=run('chat',{**common,'chat':'1'*32,'prompt':'請只輸出以下繁體文字：網頁工作台已連線。','max_tokens':64,'thinking':False})
            on=run('chat',{**common,'chat':'2'*32,'prompt':'What is 7 plus 5? Think briefly, then give the answer.','max_tokens':512,'thinking':True})
            evidence['thinking']={'off':off['result'],'on':on['result']}
            assert off['result']['answer'].strip() and on['result']['answer'].strip() and on['result'].get('reasoning')
            evidence['sqlite_history_rows']=len(rpc('history',{'chat':'1'*32}));assert evidence['sqlite_history_rows']>=2
            plan=rpc('agent-plan',{'role':'general','model':args.qwen.name,'runtime':'local','policy':'local','mode':'native','tools':['models'],
                'prompt':'Call the models tool with {} to list the models actually installed on this computer. You must call the tool before answering because you cannot know the installed filenames. After its result, answer briefly.','limits':{'steps':3,'seconds':75,'tokens':256}})
            agent=wait(rpc('run',{'action':'agent','id':plan['id'],'version':plan['version'],'confirmed':True}),100)
            # A tiny quantized model may loop tools until the approved budget ends.
            # Record that model/task failure, do not pretend it completed or prevent
            # independent Team/Benchmark/browser checks from collecting evidence.
            assert agent['state']=='completed' or agent['state']=='failed' and 'AGENT_LIMIT' in str(agent.get('error')),agent
            saved=rpc('agent-plan-get',{'id':plan['id']});events=saved.get('events',[])
            evidence['agent']={'state':agent['state'],'error':agent.get('error'),'tool_requested':any(e.get('kind')=='tool_requested' for e in events),
                'tool_result':any(e.get('kind')=='tool_result' for e in events),'answer':(agent.get('result') or {}).get('answer'),
                'audit_kinds':[e.get('kind') for e in events]}
            (output/'agent-observation.json').write_text(json.dumps(evidence['agent'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            if not evidence['agent']['tool_result']:evidence['agent']['limitation']='Model completed without selecting the tool; native protocol/permission regression is separately controlled, no tool execution is claimed for this run.'
            if agent['state']=='failed':evidence['agent']['limitation']='Actual AGENT_LIMIT failure; approved limits stopped the model. This native-agent run is not marked completed/PASS.'
            simple=rpc('agent-plan',{'role':'general','model':args.qwen.name,'runtime':'local','policy':'local','mode':'simple','tools':['models'],
                'prompt':'列出本機模型，然後給一個簡短建議。','limits':{'steps':3,'seconds':75,'tokens':192}})
            simple_result=run('agent',{'id':simple['id'],'version':simple['version'],'confirmed':True},100)
            simple_saved=rpc('agent-plan-get',{'id':simple['id']});kinds=[e.get('kind') for e in simple_saved.get('events',[])]
            evidence['simple_agent']={'state':simple_result['state'],'audit_kinds':kinds,'tool_result':'tool_result' in kinds}
            assert evidence['simple_agent']['tool_result']
            from team_workflow import templates
            team=next(t for t in templates() if t['id']=='code')
            for index,member in enumerate(team['members']):member.update(model=args.qwen.name if index%2==0 else args.smol.name,tokens=64,steps=4)
            result=run('team-workflow',{'team':team,'prompt':'請提供一個簡短的本機 AI 使用建議。','confirmed':True},180)
            saved=rpc('team-run-get',{'id':result['team_run_id']})
            evidence['team']={'state':result['state'],'models':[args.qwen.name,args.smol.name],'has_answer':bool(result['result'].get('answer')),
                'saved_nodes':len(saved.get('nodes',[])) if isinstance(saved.get('nodes'),list) else len(saved.get('nodes',{}))}
            assert evidence['team']['has_answer']
            devices=['CPU']+[d['id'] for d in status['selection']['devices'] if d['available'] and d['backend']=='Vulkan'][:1]
            benchmark=run('benchmark',{'confirmed':True,'engine':'llama.cpp','model':args.smol.name,'devices':devices,'warmup':1,'iterations':2,
                'timeout':240,'memory_mib':2048,'max_tokens':32,'context':2048},260)
            record=rpc('benchmark-get',{'id':benchmark['benchmark_id']})
            (output/'benchmark-real.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            evidence['benchmark']={'state':record['state'],'devices':devices,'runs':len(record['runs'])}
            for kind in ('csv','json'):
                export=rpc('benchmark-export',{'id':record['id'],'format':kind});assert export['download_url'].startswith('/api/exports/')
            subprocess.run(['node',str(root/'desktop/tests/web-chat-real.mjs'),str(data)],check=True,timeout=150,
                env={**os.environ,'LOCALLLM_PYTHON':sys.executable})
            evidence['chrome_react_inference']='PASS; see build/v090-browser/chat-real.json'
            job=rpc('run',{'action':'chat',**common,'chat':'3'*32,'prompt':'請寫一篇很長的故事。','max_tokens':1024,'thinking':True})
            for _ in range(300):
                current=rpc('job',{'id':job['id']})
                if current.get('answer') or current.get('reasoning'):break
                time.sleep(.1)
            assert current.get('answer') or current.get('reasoning')
            rpc('cancel',{'id':job['id']});current=wait(job);assert current['state']=='cancelled';evidence['cancel_after_started_stream']='PASS'
            assert not rpc('history',{'chat':'3'*32});evidence['cancelled_answer_not_saved']='PASS'
            assert control(data,stop=True);child.wait(25);assert child.returncode==0;evidence['shutdown_cleanup']='PASS'
        finally:
            if child.poll() is None:
                control(data,stop=True);child.wait(25)
            log.close()
    (output/'validation.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:evidence[k] for k in ('agent','team','benchmark','shutdown_cleanup')},ensure_ascii=False))


if __name__=='__main__':main()

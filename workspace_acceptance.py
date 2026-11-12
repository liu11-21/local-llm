"""Opt-in physical Host/Client acceptance. Never installs or downloads runtimes/weights."""
import argparse
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from threading import Event
from time import monotonic, sleep

from comfy_runtime import install_directory, PROFILES
from desktop_worker import Desktop
from download_recovery import exclusive
from hardware import detect_hardware
from hardware_monitor import windows_inventory
from media import DEFAULT_WORKFLOWS, ComfyClient
from media_install import install_plan, manifest
from registries import media_metadata
from workspace_errors import explain, redact
from workspace_version import build_info

TORCH_PROBE = """import json,torch
r={'torch':torch.__version__,'cuda_build':torch.version.cuda,'cuda_available':torch.cuda.is_available()}
if r['cuda_available']:
 r.update(device=torch.cuda.get_device_name(0),capability=torch.cuda.get_device_capability(0),architectures=torch.cuda.get_arch_list())
 torch.cuda.reset_peak_memory_stats();a=torch.ones((64,64),device='cuda');b=a@a;torch.cuda.synchronize()
 r.update(kernel_ok=bool((b==64).all().item()),peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved())
print(json.dumps(r))
"""


def gpu_matches(devices, expected):
    normalize=lambda text: ''.join(text.lower().split())
    return any(normalize(expected) in normalize(device.get('name','')) for device in devices)


def host_diagnosis(data, profile, devices):
    bundle=install_directory(data/'comfyui',profile)
    python=bundle/'python_embeded/python.exe'
    result={'hardware':asdict(detect_hardware(data)), 'devices':devices, 'profile':profile,
            'bundle':str(bundle), 'torch':{'status':'NOT RUN'}, 'weights':{}, 'downloads_started':False}
    if python.is_file():
        try:
            run=subprocess.run([str(python),'-s','-c',TORCH_PROBE],cwd=bundle,capture_output=True,text=True,timeout=90)
            result['torch']={'status':'PASS' if run.returncode==0 else 'FAIL',
                'returncode':run.returncode,'stderr':redact(run.stderr)}
            if run.returncode==0:
                result['torch']['evidence']=json.loads(run.stdout.strip().splitlines()[-1])
        except (OSError,ValueError,subprocess.TimeoutExpired) as error:
            result['torch']={'status':'FAIL','error':explain(error)}
    for kind in ('image','video','music'):
        result['weights'][kind]=install_plan(data,kind,profile)
    return result


def wait_task(app, action, data, *, seconds=7200, cancel_after=None):
    task=app.rpc('run',{'action':action,**data}); start=monotonic(); records=[]; previous=None
    while True:
        snapshot=app.scheduler.snapshot(task['id'])
        marker=(snapshot['state'],snapshot.get('message'),snapshot.get('received'))
        if marker!=previous:
            records.append(snapshot.copy()); previous=marker
        if snapshot['state'] not in ('queued','running','paused'):
            return {'task':snapshot,'events':records,'elapsed_seconds':monotonic()-start}
        if monotonic()-start>seconds or cancel_after is not None and monotonic()-start>cancel_after:
            app.scheduler.snapshot(task['id'],cancel=True)
            # Keep the process and its reservation alive until backend acknowledges cancellation.
            cancel_limit=min(seconds,cancel_after) if cancel_after is not None else seconds
            if monotonic()-start>cancel_limit+120:
                raise TimeoutError(f"取消仍未確認，請查詢原任務 {task['id']}；不會重新提交。")
        sleep(.5)


def sample_nvidia():
    executable=shutil.which('nvidia-smi')
    if not executable:return None
    try:
        run=subprocess.run([executable,'--query-gpu=timestamp,name,driver_version,memory.used,memory.total,utilization.gpu',
                            '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=8)
        return run.stdout.strip() if run.returncode==0 else None
    except (OSError,subprocess.TimeoutExpired):return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True,help='Close Workspace using this profile first')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--mode',choices=('host','client'),default='host')
    parser.add_argument('--profile',choices=tuple(PROFILES),default='NVIDIA GPU')
    parser.add_argument('--runtime',help='Existing paired Host ID; pair and verify fingerprint in the app first')
    parser.add_argument('--expected-gpu',default='RTX 5070 Ti')
    parser.add_argument('--execute',action='store_true',help='Explicitly run a real managed workflow using existing weights')
    parser.add_argument('--consent',action='store_true',help='Allow the supplied prompt/lyrics to the selected paired Host')
    parser.add_argument('--kind',choices=('image','video','music'),default='video')
    parser.add_argument('--prompt',default='A quiet landscape, slow camera movement')
    parser.add_argument('--lyrics',default='')
    parser.add_argument('--cancel-after',type=float)
    parser.add_argument('--recover',help='Download an existing completed remote Job; never resubmit inference')
    args=parser.parse_args()
    if args.cancel_after is not None and args.cancel_after<=0:parser.error('--cancel-after must be positive')
    if args.mode=='client' and (not args.runtime or (args.execute or args.recover) and not args.consent):
        parser.error('Client requires --runtime and execution/recovery also requires --consent')
    args.data=args.data.resolve();args.data.mkdir(parents=True,exist_ok=True)
    report={'schema':1,'build':build_info(),'status':'NOT RUN','mode':args.mode,'inference_verified':False,
            'downloads_started':False,'expected_gpu':args.expected_gpu,'npu':'NEEDS NPU','tasks':[]}
    app=None
    try:
        with ExitStack() as cleanup:
            cleanup.enter_context(exclusive(args.data/'.workspace.lock'))
            def shutdown():
                if app:
                    app.close()
                    report['local_managed_comfy_stopped']=not app.comfy.running()
            cleanup.callback(shutdown)
            try: devices=windows_inventory()
            except OSError as error: devices=[];report['inventory_error']=explain(error)
            report['local_devices']=devices
            if args.mode=='host':
                report['host']=host_diagnosis(args.data,args.profile,devices)
                matched=gpu_matches(devices,args.expected_gpu)
                if not matched:report['status']='NEEDS GPU'
                elif not args.execute:report['status']='NOT RUN'
                else:
                    torch=report['host']['torch'].get('evidence',{})
                    if not torch.get('kernel_ok') or not gpu_matches([{'name':torch.get('device','')}],args.expected_gpu):
                        raise ValueError('CUDA／PyTorch 實際裝置與核心運算尚未通過。')
                    plan=report['host']['weights'][args.kind]
                    if not plan['installed'] or any(item['status'] not in ('detected','verified') for item in plan['files']):
                        report['status']='NOT RUN';report['reason']='完整 Runtime／權重尚未準備，不下載任何檔案。'
                    else:
                        app=Desktop(args.data)
                        # Every file exists: this production operation only re-hashes existing weights.
                        report['tasks'].append(wait_task(app,'media-install',{'kind':args.kind,'profile':args.profile}))
                        if report['tasks'][-1]['task']['state']!='completed':raise ValueError('現有權重 SHA-256 驗證未通過。')
                        report['tasks'].append(wait_task(app,'comfy-start',{'profile':args.profile,'port':8188}))
                        if report['tasks'][-1]['task']['state']!='completed':raise ValueError('ComfyUI 啟動失敗，請查看服務日誌。')
                        report['comfy_nodes']=ComfyClient(app.comfy.port).json('/object_info').keys()
                        report['comfy_nodes']=list(report['comfy_nodes'])
                        report['gpu_before']=sample_nvidia()
            else:
                app=Desktop(args.data);client=app.remote_clients.get(args.runtime);client.discover()
                record=client.capability()
                report['remote']={'id':client.id,'label':client.label,'fingerprint_sha256':hashlib.sha256(client.cert_der).hexdigest(),'capability':record}
                devices=(record.get('hardware') or {}).get('devices',[])
                matched=gpu_matches(devices,args.expected_gpu)
                report['status']='NEEDS GPU' if not matched else 'NOT RUN'
            ready=(args.mode=='client' and app and (matched or args.recover) or args.mode=='host' and app and app.comfy.running())
            if ready and (args.execute or args.recover):
                workflow=DEFAULT_WORKFLOWS[args.kind]
                options=({'width':256,'height':256,'frames':9,'fps':8,'steps':2,'seed':1} if args.kind=='video' else
                         {'seconds':5,'steps':2,'seed':1} if args.kind=='music' else {'width':256,'height':256,'steps':2,'seed':1})
                data={'kind':args.kind,'workflow':workflow,'prompt':args.prompt,'lyrics':args.lyrics,'options':options,
                      'runtime':args.runtime if args.mode=='client' else 'local','consent':args.consent,'port':8188}
                action='remote-fetch-work' if args.recover else 'media'
                if args.recover:data.update(request=args.recover)
                # Sample actual dedicated GPU memory during the operation, never infer peak from total VRAM.
                from threading import Thread
                stop=Event();samples=[]
                def monitor():
                    while not stop.is_set():
                        samples.append({'elapsed':monotonic(),'gpu':sample_nvidia(),'ram':asdict(detect_hardware(args.data))})
                        stop.wait(1)
                sampler=Thread(target=monitor,daemon=True);sampler.start()
                try:run=wait_task(app,action,data,cancel_after=args.cancel_after)
                finally:stop.set();sampler.join(timeout=10)
                report['tasks'].append(run);report['resource_samples']=samples
                report['model']=manifest(args.kind);report['options']=options
                task=run['task'];result=task.get('result') or {}
                if task['state']=='completed' and result.get('file'):
                    file=Path(result['file']);report['media']={'file':str(file),'bytes':file.stat().st_size,
                        'sha256':hashlib.file_digest(file.open('rb'),'sha256').hexdigest(),'metadata':media_metadata(file)}
                    report['inference_verified']=not bool(args.recover)
                    report['status']='PASS'
                elif task['state']=='cancelled' and args.cancel_after:
                    report['status']='PASS';report['cancellation_verified']=True
                else:report['status']='FAIL'
    except Exception as error:
        report.update(status='FAIL',error=explain(error))
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'inference_verified':report['inference_verified'],'report':str(args.output)},ensure_ascii=False))
    return 1 if report['status']=='FAIL' else 0


if __name__=='__main__':raise SystemExit(main())

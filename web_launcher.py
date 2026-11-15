"""Official-Python launcher/control plane; no self-packaged executable required."""
import argparse
import asyncio
import http.client
import json
import os
from pathlib import Path
import struct
import sys
import webbrowser

ROOT=Path(__file__).resolve().parent
for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8',line_buffering=True)
# -I intentionally omits the script directory. Add only the selected distribution.
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
from download_recovery import exclusive,owned
from runtime_trust import signature,code_integrity
from web_environment import ensure_environment,verify_distribution
from workspace_version import build_info


def official_python():
    if not ((3,12,10)<=sys.version_info[:3]<(3,13,0)) or struct.calcsize('P')!=8:
        raise ValueError('需要官方 Python 3.12 x64（3.12.10 或較新 3.12 版本）。請從 https://www.python.org/downloads/windows/ 安裝。')
    result=signature(sys.executable)
    if os.name=='nt' and (result.get('status')!='Valid' or 'CN=Python Software Foundation' not in result.get('signer','')):
        raise ValueError('無法確認目前 Python 為有效 Python Software Foundation 簽章。請使用官方發行版本；勿停用系統安全政策。')
    return result


def canonical_data(path):
    candidate=Path(path).absolute()
    # Windows TEMP may contain a legitimate DOS 8.3 alias (e.g. RUNNER~1).
    # Reject actual reparse links first, then canonicalize ordinary aliases.
    for component in (candidate,*candidate.parents):
        if component.is_symlink() or component.is_junction():raise ValueError('資料目錄不可為連結或重新導向路徑。')
    return candidate.resolve()


def state_path(data):return Path(data).resolve()/'.web-service.json'


def save_state(data,app,url):
    from remote_client import protect
    record={'port':app.port,'bootstrap':app.bootstrap,'pid':os.getpid(),'build':build_info()}
    path=state_path(data)
    if not owned(path):raise ValueError('服務記錄路徑不安全。')
    encoded=protect(json.dumps(record).encode()) if os.name=='nt' else json.dumps(record).encode()
    staged=path.with_suffix('.tmp');staged.write_bytes(encoded);os.replace(staged,path)


def read_state(data):
    from remote_client import protect
    path=state_path(data)
    if not path.is_file() or not owned(path):return None
    raw=path.read_bytes()
    try:
        value=json.loads(protect(raw,decrypt=True) if os.name=='nt' else raw)
        if type(value.get('port')) is not int or not 1024<=value['port']<=65535 or not isinstance(value.get('bootstrap'),str):return None
        return value
    except (ValueError,OSError):return None


def control(data,*,stop=False):
    record=read_state(data)
    if not record:return False
    port=record['port'];origin=f'http://127.0.0.1:{port}'
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    try:
        connection.request('POST','/api/session','{}',headers={'Origin':origin,'Content-Type':'application/json','X-Workspace-Bootstrap':record['bootstrap']})
        response=connection.getresponse();payload=json.loads(response.read());cookie=response.getheader('Set-Cookie')
        if response.status!=200 or not payload.get('ok') or payload['value']['build']!=record['build']:return False
        if stop:
            connection.request('POST','/api/shutdown',json.dumps({'confirmed':True}),headers={
                'Origin':origin,'Content-Type':'application/json','Cookie':cookie.split(';')[0],'X-Workspace-CSRF':payload['value']['csrf']})
            response=connection.getresponse();response.read();return response.status==200
        return origin+'/#bootstrap='+record['bootstrap']
    except (OSError,ValueError,http.client.HTTPException):return False
    finally:connection.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',nargs='?',default='start',choices=['start','stop','status','diagnose','update','rollback','optional'])
    parser.add_argument('input',nargs='?');parser.add_argument('--sha256')
    parser.add_argument('--data',type=Path,default=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'LocalLLM')
    parser.add_argument('--port',type=int,default=8766);parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--direct',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args();data=canonical_data(args.data)
    if not owned(data):raise ValueError('資料目錄不可為連結或重新導向路徑。')
    data.mkdir(parents=True,exist_ok=True)
    if args.command=='stop':
        print('服務已收到停止要求。' if control(data,stop=True) else '目前沒有可驗證的 Web 服務；不會終止其他程序。');return
    if args.command=='status':
        print('Web 服務執行中。' if control(data) else 'Web 服務尚未啟動。');return
    if args.command=='diagnose':
        report={'python':signature(sys.executable),'python_version':sys.version.split()[0],
                'build':build_info(),'distribution':verify_distribution(),'service_running':bool(control(data)),
                'code_integrity':code_integrity(),'SAC':'NOT VERIFIED: diagnostics do not identify policy compatibility'}
        (data/'web-diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('已保存 web-diagnostics.json（可能含裝置路徑，分享前請檢查）。');return
    if args.command in ('update','rollback'):
        if control(data):raise ValueError('請先執行 Stop-Web-Workspace.cmd 停止服務，再更新或回滾。')
        from web_update import update,rollback
        if args.command=='update':
            if not args.input or not args.sha256:raise ValueError('用法：Update-Web-Workspace.cmd 完整ZIP路徑 --sha256 官方交付的SHA256；不接受未校驗 ZIP。')
            result=update(ROOT,Path(args.input),args.sha256)
        else:result=rollback(ROOT)
        print(result);return
    if not args.direct:
        from web_update import selected
        target=selected(ROOT)
        if target!=ROOT:
            import subprocess
            command=[sys.executable,'-I','-S','-B',str(target/'web_launcher.py'),args.command,'--direct','--data',str(data),'--port',str(args.port)]
            if args.input:command.append(args.input)
            if args.no_browser:command.append('--no-browser')
            raise SystemExit(subprocess.call(command))
    if args.command=='optional':
        from web_optional import install
        official_python();print(install(data,args.input));return
    current=control(data)
    if current:
        print('已使用原有服務，沒有重複啟動。')
        if not args.no_browser:webbrowser.open(current)
        return
    if not 1024<=args.port<=65535:raise ValueError('連接埠無效。')
    if not (ROOT/'desktop/dist/index.html').is_file():raise ValueError('找不到 Web 前端；請下載完整 Web ZIP。原始碼需先執行 npm run build:web。')
    verify_distribution();official_python()
    with exclusive(data/'.workspace.lock'):
        site=ensure_environment(data);sys.path.insert(0,str(site))
        from web_optional import activate
        activate(data)
        from workspace_web import serve
        print(f'Local LLM Web Workspace {build_info()["version"]} · http://127.0.0.1:{args.port}')
        print('保留此視窗。關閉瀏覽器不會立刻停止服務；可使用 Stop-Web-Workspace.cmd。')
        try:asyncio.run(serve(data,args.port,browser=not args.no_browser,on_ready=lambda app,url:save_state(data,app,url)))
        finally:state_path(data).unlink(missing_ok=True)


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,ImportError) as error:
        print('啟動／管理失敗：'+str(error),file=sys.stderr)
        print('請使用官方 Python 與完整 ZIP，保留 Windows 安全政策；可執行 Diagnose-Web-Workspace.cmd。',file=sys.stderr)
        raise SystemExit(1)

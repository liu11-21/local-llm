"""Read current Windows PATHs, resolve aliases, then verify before any execution."""
import ctypes as ct
import hashlib
import os
from pathlib import Path,PureWindowsPath
import re
import struct
import time
from runtime_trust import RuntimeTrust,expected_signer,sha256
from runtime_probe import ProbeError


def registry_paths():
    result={'paths':[],'local_data':[],'errors':[]}
    if os.name!='nt':return result
    import winreg
    for source,hive,key in [('user_path',winreg.HKEY_CURRENT_USER,'Environment'),
            ('system_path',winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')]:
        try:
            with winreg.OpenKey(hive,key) as handle:value,_=winreg.QueryValueEx(handle,'Path')
            result['paths'].append((source,winreg.ExpandEnvironmentStrings(value)))
        except OSError as error:result['errors'].append({'source':source,'reason':type(error).__name__})
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as handle:
            value,_=winreg.QueryValueEx(handle,'Local AppData')
        result['local_data'].append(winreg.ExpandEnvironmentStrings(value))
    except OSError:pass
    return result


def inventory(extra=()):
    registry=registry_paths();locations=[]
    for source,value in [('process_path',os.environ.get('PATH','')),*registry['paths']]:
        for item in value.split(os.pathsep):
            item=os.path.expandvars(item.strip().strip('"'))
            if not item:continue
            directory=Path(item)
            if not directory.is_absolute() or item.startswith(('\\\\','//')):continue
            locations.append((source,directory/'llama.exe'))
    for directory in [os.environ.get('LOCALAPPDATA'),*registry['local_data']]:
        if directory:
            locations.extend([('windows_apps',Path(directory)/'Microsoft/WindowsApps/llama.exe'),('official_install',Path(directory)/'llama-app/llama.exe')])
    locations.extend(extra);seen={};attempts=[]
    for source,path in locations:
        path=Path(path).absolute();key=os.path.normcase(str(path))
        if key in seen:
            if source not in seen[key]['sources']:seen[key]['sources'].append(source)
            continue
        try:
            stat=path.lstat();exists=True
            is_file=path.is_file();is_link=path.is_symlink() or bool(getattr(stat,'st_reparse_tag',0))
            reason='' if is_file or is_link else 'NOT_A_FILE'
        except OSError as error:exists=False;is_file=False;is_link=False;reason='FILE_NOT_FOUND' if isinstance(error,FileNotFoundError) else 'PATH_ACCESS_FAILED'
        attempt={'input_path':str(path),'sources':[source],'exists':exists,'is_file':is_file,'is_link':is_link,'reason':reason}
        attempts.append(attempt);seen[key]=attempt
    return {'attempts':attempts,'found':[dict(row) for row in attempts if row['exists'] and (row['is_file'] or row['is_link'])],
            'errors':registry['errors'],'searched':len(attempts)}


def app_execution_target(data):
    """Bounded AppExecLink StringList: use the target entry, never execute alias text.

    Windows reparse tag/header documented by Microsoft; third StringList entry is
    also confirmed by libuv's upstream Windows readlink implementation.
    """
    if len(data)<14:return None
    tag,length=struct.unpack_from('<IH',data)
    if tag!=0x8000001B or length+8>len(data) or length<6:return None
    count=struct.unpack_from('<I',data,8)[0]
    if not 3<=count<=32:return None
    try:strings=data[12:8+length].decode('utf-16-le').split('\0')
    except UnicodeError:return None
    if len(strings)<3 or not all(strings[:3]):return None
    target=strings[2]
    if not PureWindowsPath(target).is_absolute() or PureWindowsPath(target).name.lower()!='llama.exe':return None
    return target


def read_alias_target(path):
    if os.name!='nt':return None
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[ct.c_wchar_p,ct.c_uint32,ct.c_uint32,ct.c_void_p,ct.c_uint32,ct.c_uint32,ct.c_void_p]
    kernel.CreateFileW.restype=ct.c_void_p;kernel.CloseHandle.argtypes=[ct.c_void_p]
    kernel.DeviceIoControl.argtypes=[ct.c_void_p,ct.c_uint32,ct.c_void_p,ct.c_uint32,ct.c_void_p,ct.c_uint32,ct.POINTER(ct.c_uint32),ct.c_void_p]
    handle=kernel.CreateFileW(str(path),0,7,None,3,0x02200000,None)
    if handle in (None,ct.c_void_p(-1).value):return None
    try:
        buffer=ct.create_string_buffer(16384);size=ct.c_uint32()
        if not kernel.DeviceIoControl(handle,0x000900A8,None,0,buffer,len(buffer),ct.byref(size),None):return None
        return app_execution_target(buffer.raw[:size.value])
    finally:kernel.CloseHandle(handle)


def resolve_runtime(value):
    if not isinstance(value,(str,Path)) or not str(value).strip():raise ProbeError('RUNTIME_PATH','請指定既有的 llama.exe。')
    path=Path(str(value).strip()).absolute()
    if path.name.lower()!='llama.exe':raise ProbeError('WRONG_EXECUTABLE','必須選擇新版 llama.exe，不能將 llama-server.exe 當作新版引擎。')
    alias=read_alias_target(path)
    target=Path(alias).resolve(strict=True) if alias else path.resolve(strict=True)
    if not target.is_file():raise ProbeError('FILE_NOT_FOUND','找不到可讀取的 Runtime 執行檔。')
    if target.name.lower()!='llama.exe':raise ProbeError('WRONG_EXECUTABLE','別名的實際目標不是 llama.exe。')
    return target


def candidate(value,sources=()):
    path=str(value)
    return {'id':hashlib.sha256(os.path.normcase(path).encode()).hexdigest()[:20],'input_path':path,'input_paths':[path],
            'sources':list(sources),'path':None,'exists':False,'state':'found','verified':False,'selected':False,
            'version':None,'authenticode':{'status':'NOT VERIFIED'},'probes':[],'trace':[],'reason':None,'devices':[]}


def validate(row,probe,trust=None,changed=lambda:None):
    trust=trust or RuntimeTrust();row.update(state='verifying',verified=False,reason=None);changed()
    stage='resolve'
    try:
        path=resolve_runtime(row['input_path']);row.update(path=str(path),exists=True)
        row['trace'].append({'stage':'resolve','ok':True,'input_path':row['input_path'],'resolved_path':str(path),'exists':True})
        stage='authenticode';report=trust.inspect(path)
        row.update(authenticode=report['authenticode'],sha256=report['sha256'],trust=report)
        row['trace'].append({'stage':stage,'ok':expected_signer(report['authenticode']),'authenticode':report['authenticode']})
        if not expected_signer(report['authenticode']):raise ProbeError('RUNTIME_SIGNATURE','需要 Valid 且 CN／O 精確為 Hugging Face 的官方簽章；未執行此檔案。')
        stage='cli';caps=probe(path,refresh=True)
        if report['sha256']!=sha256(path):raise ProbeError('RUNTIME_CHANGED','檢查期間 Runtime 內容已變更，未接受此候選。')
        row.update(version=caps['version'],devices=caps.get('devices',[]),probes=caps.get('probes',[]),state='verified',verified=True,checked_at=int(time.time()))
        report.update(version=caps['version'],cli_probe_success=True,gpu_identified=bool(caps.get('devices')))
        row['trace'].append({'stage':'cli','ok':True,'probes':row['probes'],'compatible':True})
    except (OSError,ValueError,RuntimeError) as error:
        code=getattr(error,'code',None) or ('FILE_NOT_FOUND' if isinstance(error,FileNotFoundError) else 'RUNTIME_VALIDATION_FAILED')
        probes=getattr(error,'record',{}).get('probes',[]);row['probes']=probes
        row.update(state='unsupported' if code in ('WRONG_EXECUTABLE','RUNTIME_CAPABILITY') else 'failed',reason={'code':code,'message':str(error)})
        row['trace'].append({'stage':stage,'ok':False,'code':code,'message':str(error),'probes':probes})
    changed();return row

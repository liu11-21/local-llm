"""Runtime evidence is deliberately separated; a valid signature is not SAC approval."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

OFFICIAL = "https://github.com/ggml-org/llama-install.sh"
BASELINE_SHA256 = "ad0e800c73fc892557a5c0f192f206ceec3dac94bccfc b0bed2f750e3ac31614".replace(" ", "")
BASELINE = {"source": OFFICIAL, "build": "12360", "commit": "2d8a32502", "sha256": BASELINE_SHA256,
            "evidence": "maintainer-reported on another Windows host; not this host's verification"}
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def powershell(script, args=(), timeout=20):
    if os.name != "nt":
        return None
    shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not shell:
        return None
    # Arguments are bound positionally, never interpolated into PowerShell source.
    result = subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",script,*map(str,args)],
        capture_output=True,timeout=timeout,creationflags=FLAGS,encoding="utf-8",errors="replace")
    if result.returncode:
        return None
    try:return json.loads(result.stdout.lstrip("\ufeff"))
    except ValueError:return None


def signature(path):
    # Avoid shell injection: path is transferred through the environment, not parsed as code.
    if os.name != "nt":return {"status":"NOT VERIFIED","signer":None}
    env = os.environ.copy();env["LOCALLLM_TRUST_FILE"] = str(Path(path).absolute())
    script = "$s=Get-AuthenticodeSignature -LiteralPath $env:LOCALLLM_TRUST_FILE; @{status=$s.Status.ToString();signer=$s.SignerCertificate.Subject;issuer=$s.SignerCertificate.Issuer;thumbprint=$s.SignerCertificate.Thumbprint}|ConvertTo-Json -Compress"
    shell=shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not shell:return {"status":"NOT VERIFIED","signer":None}
    try:
        result=subprocess.run([shell,"-NoProfile","-NonInteractive","-Command",script],env=env,capture_output=True,timeout=20,creationflags=FLAGS,encoding="utf-8",errors="replace")
        value=json.loads(result.stdout.lstrip("\ufeff"))
        return value if result.returncode==0 else {"status":"NOT VERIFIED","signer":None}
    except (OSError,ValueError,subprocess.TimeoutExpired):return {"status":"NOT VERIFIED","signer":None}


def discover():
    candidates=[]
    for name in ("llama.exe","llama"):
        value=shutil.which(name)
        if value:candidates.append(Path(value))
    local=os.environ.get("LOCALAPPDATA")
    if local:
        candidates += [Path(local)/"llama-app"/"llama.exe",Path(local)/"Microsoft"/"WindowsApps"/"llama.exe"]
    seen=set();result=[]
    for path in candidates:
        if path.is_file() and str(path.absolute()).casefold() not in seen:
            seen.add(str(path.absolute()).casefold());result.append(path.absolute())
    return result


def code_integrity(since=None):
    if os.name!="nt":return {"status":"NOT VERIFIED","events":[]}
    # Read only recent Code Integrity block events. Do not alter any policy.
    value=powershell("$e=@(Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-CodeIntegrity/Operational';Id=3077;StartTime=(Get-Date).AddMinutes(-10)} -MaxEvents 12 -ErrorAction SilentlyContinue | ForEach-Object {$x=[xml]$_.ToXml();@{id=$_.Id;time=$_.TimeCreated.ToUniversalTime().ToString('o');files=@($x.Event.EventData.Data | Where-Object {$_.Name -match 'FileName|ProcessName'} | ForEach-Object {$_.InnerText})}});ConvertTo-Json -InputObject $e -Depth 5 -Compress")
    return {"status":"READ" if value is not None else "NOT VERIFIED","events":value or [],
            "guidance":"3077: inspect the named EXE/DLL in Code Integrity; keep SAC/Defender enabled. Events may belong to other applications."}


class RuntimeTrust:
    def inspect(self,path,*,expected=None,source=None):
        path=Path(path).absolute()
        if not path.is_file() or path.suffix.lower()!=".exe":raise ValueError("RUNTIME_PATH · 請選擇存在的 llama.exe。")
        digest=sha256(path);auth=signature(path)
        verified=bool(expected and digest==expected.lower())
        return {"path":str(path),"sha256":digest,"source":source,"checked_at":int(time.time()),
                "source_confirmed":bool(source==OFFICIAL and verified),"sha256_verified":verified,
                "authenticode":auth,"launch_success":False,"gpu_identified":False,"inference_success":False,
                "sac":"NOT VERIFIED; requires independent real-machine testing",
                "resolved_image":None,"dependencies":[],"dependency_scan":"NOT VERIFIED; process modules must be inspected separately",
                "execution_permission":os.access(path,os.X_OK),"baseline_match":digest==BASELINE_SHA256}

    def modules(self,process):
        if os.name!="nt":return {"resolved_image":None,"dependencies":[],"dependency_scan":"NOT VERIFIED"}
        env=os.environ.copy();env['LOCALLLM_TRUST_PID']=str(int(process.pid))
        script="$p=Get-Process -Id ([int]$env:LOCALLLM_TRUST_PID) -ErrorAction Stop;@{image=$p.Path;modules=@($p.Modules | ForEach-Object {$_.FileName})}|ConvertTo-Json -Depth 3 -Compress"
        shell=shutil.which('powershell.exe') or shutil.which('pwsh.exe')
        if not shell:return {"resolved_image":None,"dependencies":[],"dependency_scan":"NOT VERIFIED"}
        try:
            r=subprocess.run([shell,'-NoProfile','-NonInteractive','-Command',script],env=env,capture_output=True,timeout=20,creationflags=FLAGS,encoding='utf-8',errors='replace')
            data=json.loads(r.stdout.lstrip('\ufeff'));modules=[]
            for path in dict.fromkeys(data.get('modules',[])):
                if Path(path).is_file():modules.append({"name":Path(path).name,"path":path,"sha256":sha256(path),"authenticode":signature(path)})
            image=data.get('image')
            return {"resolved_image":{ "path":image,"sha256":sha256(image),"authenticode":signature(image)} if image and Path(image).is_file() else None,
                    "dependencies":modules,"dependency_scan":"observed process modules only; delay-loaded modules may appear later"}
        except (OSError,ValueError,subprocess.TimeoutExpired):return {"resolved_image":None,"dependencies":[],"dependency_scan":"NOT VERIFIED; process module inspection unavailable"}


def launch_diagnostic(error,executable):
    report=code_integrity();name=Path(executable).name.casefold()
    related=[event for event in report['events'] if any(name in str(path).casefold() for path in event.get('files',[]))]
    files=list(dict.fromkeys(str(path) for event in related for path in event.get('files',[])))
    return {'winerror':getattr(error,'winerror',None),'code_integrity':{**report,'events':related},
            'blocking_files':files,'code':'CODE_INTEGRITY_3077' if related else 'RUNTIME_LAUNCH_FAILED',
            'hint':'請核對 Runtime 診斷中的實際 EXE／DLL；保持 SAC、Defender 與系統政策啟用。'}

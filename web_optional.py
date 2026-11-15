"""Explicit native dependencies; separate from the pure Python Web host."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from web_environment import digest,verify_environment

ROOT=Path(__file__).resolve().parent


def install(data,group):
    if group not in ('runtime','tls'):raise ValueError('選用套件請指定 runtime（zstandard）或 tls（私人遠端 Host）。')
    lock=ROOT/f'requirements-web-{group}.lock'
    if not lock.is_file():raise ValueError('缺少選用依賴鎖定檔。')
    base=data/'web-optionals';base.mkdir(exist_ok=True)
    target=base/(group+'-'+hashlib.sha256(lock.read_bytes()).hexdigest()[:16])
    if target.exists():verify_environment(target);return '選用環境已存在，完整性檢查通過；SAC 仍需實機驗證。'
    with tempfile.TemporaryDirectory(prefix='.optional-',dir=base) as scratch:
        scratch=Path(scratch);site=scratch/'Lib/site-packages';site.mkdir(parents=True)
        # Run pip with the original official Python; never run a venv/packaged EXE.
        command=[sys.executable,'-I','-B','-m','pip','install','--disable-pip-version-check','--only-binary=:all:',
            '--require-hashes','--no-compile','--target',str(site),'-r',str(lock)]
        result=subprocess.run(command,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise ValueError('選用套件安裝失敗；請確認官方 Python 含 pip、網路／TLS 正常；不要略過 hash 或安全政策。')
        files={p.relative_to(site).as_posix():digest(p) for p in site.rglob('*') if p.is_file()}
        (scratch/'web-environment.json').write_text(json.dumps({'files':files,'group':group,'native':'SAC NOT VERIFIED'},indent=2),encoding='utf-8')
        os.replace(scratch,target)
    return '選用套件已安裝並記錄 hash；原生 DLL／PYD 仍須獨立通過 Windows Application Control。'


def activate(data):
    for group in ('runtime','tls'):
        lock=ROOT/f'requirements-web-{group}.lock'
        if not lock.exists():continue
        target=data/'web-optionals'/(group+'-'+hashlib.sha256(lock.read_bytes()).hexdigest()[:16])
        if target.exists():sys.path.insert(0,str(verify_environment(target)))

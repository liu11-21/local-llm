"""Offline, hash-confirmed side-by-side ZIP updates; user data is never extracted here."""
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import tempfile
import zipfile
from web_environment import verify_distribution
from download_recovery import owned


def base(root):return root.parent if root.name=='app' else root
def pointer(root):return base(root)/'.web-active.json'


def selected(root):
    file=pointer(root)
    if not file.exists():return root
    if not owned(file):raise ValueError('更新選擇記錄路徑不安全。')
    value=json.loads(file.read_text(encoding='utf-8'));target=base(root)/value['current']
    if not target.resolve().is_relative_to(base(root)) or not owned(target):raise ValueError('更新路徑無效。')
    verify_distribution(target)
    return target


def write(root,value):
    file=pointer(root);staged=file.with_suffix('.tmp')
    if not owned(file) or not owned(staged):raise ValueError('更新記錄路徑不安全。')
    staged.write_text(json.dumps(value,indent=2),encoding='utf-8');os.replace(staged,file)


def update(root,archive,expected):
    if not re.fullmatch(r'[a-fA-F0-9]{64}',expected):raise ValueError('需要有效的官方 ZIP SHA-256。')
    with archive.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=expected.lower():raise ValueError('ZIP SHA-256 不符，未更新。')
    parent=base(root);versions=parent/'web-versions';versions.mkdir(exist_ok=True)
    if not owned(versions):raise ValueError('更新目錄不安全。')
    target=versions/actual[:20]
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix='.web-update-',dir=versions) as scratch:
            scratch=Path(scratch)
            with zipfile.ZipFile(archive) as bundle:
                entries=bundle.infolist()
                if len(entries)>10000 or sum(e.file_size for e in entries)>512*1024**2:raise ValueError('ZIP 超過更新限制。')
                for entry in entries:
                    path=PurePosixPath(entry.filename)
                    if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename
                            or entry.filename.lower().endswith(('.exe','.dll','.pyd','.gguf'))
                            or (entry.external_attr>>16)&0o170000==0o120000):raise ValueError('ZIP 包含不允許的路徑或執行檔。')
                    if entry.is_dir():continue
                    output=scratch.joinpath(*path.parts);output.parent.mkdir(parents=True,exist_ok=True)
                    with bundle.open(entry) as source,output.open('xb') as out:
                        import shutil
                        shutil.copyfileobj(source,out)
            candidates=list(scratch.glob('*/app/WEB_MANIFEST.json'))
            if len(candidates)!=1:raise ValueError('不是完整 Web Workspace 發行 ZIP。')
            app=candidates[0].parent;verify_distribution(app);os.replace(app,target)
    else:verify_distribution(target)
    current=selected(root)
    write(root,{'current':target.relative_to(parent).as_posix(),'previous':current.relative_to(parent).as_posix()})
    return '更新已準備完成，下次啟動會使用新版本；模型／SQLite 未被覆蓋。'


def rollback(root):
    file=pointer(root)
    if not file.is_file() or not owned(file):raise ValueError('沒有可回滾的更新。')
    value=json.loads(file.read_text(encoding='utf-8'));previous=base(root)/value['previous']
    if not owned(previous) or not previous.resolve().is_relative_to(base(root)):raise ValueError('回滾路徑無效。')
    if previous!=root:verify_distribution(previous)
    write(root,{'current':value['previous'],'previous':value['current']})
    return '已切換回先前程式版本；使用者資料保留。若未來 schema 不相容，需使用已校驗的升級前備份。'

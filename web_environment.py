"""Install a hash-pinned pure-Python wheel set without running generated EXE shims."""
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import tempfile
from urllib.request import urlopen
from urllib.parse import urlsplit
import venv
import zipfile
from download_recovery import owned

ROOT=Path(__file__).resolve().parent


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def dependencies(root=ROOT):
    record=json.loads((root/'web-dependencies.json').read_text(encoding='utf-8'))
    lock=(root/'requirements-web.lock').read_text(encoding='utf-8')
    for item in record:
        assert f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}" in lock
        parsed=urlsplit(item['url'])
        if parsed.scheme!='https' or parsed.hostname!='files.pythonhosted.org':raise ValueError('依賴來源不符。')
    return record


def unpack_wheel(wheel,site):
    with zipfile.ZipFile(wheel) as archive:
        members=archive.infolist()
        if len(members)>2000 or sum(i.file_size for i in members)>32*1024**2:raise ValueError('依賴 wheel 超過限制。')
        paths=[i.filename for i in members if not i.is_dir()]
        records=[p for p in paths if p.endswith('.dist-info/RECORD')]
        if len(records)!=1 or len(set(paths))!=len(paths):raise ValueError('Wheel 目錄不完整。')
        wheel_info=archive.read(records[0].removesuffix('RECORD')+'WHEEL').decode()
        if 'Root-Is-Purelib: true' not in wheel_info:raise ValueError('基本 Web 依賴不得包含原生擴充。')
        hashes={row[0]:row[1:] for row in csv.reader(io.StringIO(archive.read(records[0]).decode()))}
        for member in members:
            if member.is_dir():continue
            path=PurePosixPath(member.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in member.filename or ':' in member.filename
                    or member.filename.lower().endswith(('.exe','.dll','.pyd','.so'))
                    or (member.external_attr>>16)&0o170000==0o120000):raise ValueError('Wheel 含不允許的內容。')
            content=archive.read(member)
            expected,size=hashes.get(member.filename,('',''))
            if member.filename!=records[0]:
                actual='sha256='+base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
                if expected!=actual or str(len(content))!=size:raise ValueError('Wheel RECORD 完整性不符。')
            target=site.joinpath(*path.parts);target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise ValueError('依賴套件檔案衝突。')
            target.write_bytes(content)


def verify_environment(environment):
    if not owned(environment) or not owned(environment/'Lib/site-packages'):raise ValueError('Web 環境路徑不安全。')
    site=environment/'Lib/site-packages'
    record=json.loads((environment/'web-environment.json').read_text(encoding='utf-8'))
    actual={str(p.relative_to(site).as_posix()) for p in site.rglob('*') if p.is_file()}
    if actual!=set(record['files']):raise ValueError('Web 環境有額外或遺失檔案，請移除該環境後重新啟動。')
    for relative,sha in record['files'].items():
        path=site/relative
        if path.is_symlink() or digest(path)!=sha:raise ValueError('Web 依賴檔案已變更，未載入。')
    return site


def ensure_environment(data,root=ROOT):
    pins=dependencies(root);identity=hashlib.sha256((root/'requirements-web.lock').read_bytes()).hexdigest()[:20]
    base=data/'web-environments';base.mkdir(exist_ok=True);target=base/identity
    if not owned(base) or not owned(target):raise ValueError('Web 環境目錄不安全。')
    if target.exists():return verify_environment(target)
    with tempfile.TemporaryDirectory(prefix='.web-setup-',dir=base) as scratch:
        scratch=Path(scratch);environment=scratch/'venv'
        # The generated venv launcher is never executed; the original signed Python
        # hosts the application. No pip/distlib entry-point EXEs are generated.
        venv.EnvBuilder(with_pip=False).create(environment)
        site=environment/'Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
        for item in pins:
            name=urlsplit(item['url']).path.rsplit('/',1)[-1]
            cached=root/'wheelhouse'/name
            if not cached.is_file():cached=root/'build/web-wheels'/name
            if cached.is_file():
                wheel=cached
            else:
                wheel=scratch/name
                with urlopen(item['url'],timeout=30) as response,wheel.open('wb') as output:
                    received=0
                    while block:=response.read(256*1024):
                        received+=len(block)
                        if received>8*1024**2:raise ValueError('依賴下載超過限制。')
                        output.write(block)
            if digest(wheel)!=item['sha256']:raise ValueError('依賴 wheel SHA-256 不符，未安裝。')
            unpack_wheel(wheel,site)
        files={p.relative_to(site).as_posix():digest(p) for p in site.rglob('*') if p.is_file()}
        (environment/'web-environment.json').write_text(json.dumps({'files':files,'pins':pins},indent=2),encoding='utf-8')
        os.replace(environment,target)
    return verify_environment(target)


def verify_distribution(root=ROOT):
    manifest=root/'WEB_MANIFEST.json'
    if not manifest.exists():return {'mode':'source checkout; use the verified CI ZIP for distribution'}
    record=json.loads(manifest.read_text(encoding='utf-8'))
    for relative,sha in record['files'].items():
        path=root/relative
        if not path.resolve().is_relative_to(root) or path.is_symlink() or not path.is_file() or digest(path)!=sha:
            raise ValueError('發行檔案遺失或內容已更改，請重新下載完整 ZIP。')
    return {'mode':'verified manifest','files':len(record['files']),'source_commit':record['commit']}

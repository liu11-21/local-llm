"""Build a source + prebuilt React ZIP, containing no executable/native payloads."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
import ast
from urllib.request import urlopen
from web_environment import dependencies,digest,ROOT
from workspace_version import build_info,VERSION


def build():
    output=ROOT/'build/web-release';output.mkdir(parents=True,exist_ok=True)
    info=build_info()
    if info['commit']=='unknown':raise ValueError('Web 候選包需要明確的來源 Commit。')
    if not (ROOT/'desktop/dist/index.html').is_file():raise ValueError('先執行 npm run build:web。')
    with tempfile.TemporaryDirectory(prefix='web-bundle-',dir=ROOT/'build') as scratch:
        bundle=Path(scratch)/f'LocalLLM-Web-{VERSION}';app=bundle/'app';app.mkdir(parents=True)
        pending=['web_launcher','workspace_web','openvino_runner','benchmark_openvino'];modules=set()
        while pending:
            name=pending.pop()
            if name in modules or not (ROOT/(name+'.py')).is_file():continue
            modules.add(name)
            for node in ast.walk(ast.parse((ROOT/(name+'.py')).read_text(encoding='utf-8'))):
                if isinstance(node,ast.Import):pending.extend(item.name.split('.')[0] for item in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:pending.append(node.module.split('.')[0])
        for name in modules:shutil.copyfile(ROOT/(name+'.py'),app/(name+'.py'))
        for pattern in ('*.json','requirements-web*.lock'):
            for path in ROOT.glob(pattern):
                if path.name=='DEPENDENCY_LICENSES.json':continue
                shutil.copyfile(path,app/path.name)
        (app/'workspace-build.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        shutil.copytree(ROOT/'desktop/dist',app/'desktop/dist')
        shutil.copytree(ROOT/'third_party',app/'third_party')
        shutil.copytree(ROOT/'docs/sbom',app/'notices')
        for name in ('LICENSE','LICENSE_SCOPE.md','LICENSE_STATUS.md','PRIVACY.md','THIRD_PARTY_LICENSES.md'):
            shutil.copyfile(ROOT/name,app/name)
        for name in ('Start-Web-Workspace.cmd','Stop-Web-Workspace.cmd','Diagnose-Web-Workspace.cmd','Update-Web-Workspace.cmd','Rollback-Web-Workspace.cmd','Install-Web-Optional.cmd'):
            shutil.copyfile(ROOT/name,bundle/name)
        shutil.copyfile(ROOT/'WEB-START-HERE.txt',bundle/'WEB-START-HERE.txt')
        docs=app/'docs';docs.mkdir()
        for name in ('WEB_ARCHITECTURE.md','WEB_INSTALLATION.md','WEB_SECURITY.md','WEB_COMPATIBILITY.md','V090_DELIVERY.md'):
            shutil.copyfile(ROOT/'docs'/name,docs/name)
        wheels=app/'wheelhouse';wheels.mkdir()
        inventory=[]
        for item in dependencies():
            filename=item['url'].rsplit('/',1)[-1];source=ROOT/'build/web-wheels'/filename
            if not source.is_file():
                source.parent.mkdir(exist_ok=True)
                with urlopen(item['url'],timeout=30) as response,source.open('wb') as stream:shutil.copyfileobj(response,stream)
            if digest(source)!=item['sha256']:raise ValueError('打包的 wheel SHA-256 不符。')
            shutil.copyfile(source,wheels/filename)
            with zipfile.ZipFile(source) as wheel:
                names=[name for name in wheel.namelist() if 'license' in name.lower() and not name.endswith('/')]
                inventory.append({**item,'original_license_files':names,'distribution':'pure Python wheel, preserved unmodified'})
        (app/'WEB_DEPENDENCIES.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
        (app/'WEB_NOTICE_SCOPE.txt').write_text('WEB_DEPENDENCIES.json and unchanged wheels index the actual pure Python Web host dependencies. notices/ preserves the existing Desktop/frontend dependency review, including non-shipped optional/build targets; it is not a statement that every listed Desktop binary is in this Web ZIP. First-party MIT scope and separate runtime/model/brand terms are preserved.\n',encoding='utf-8')
        forbidden=[p.name for p in bundle.rglob('*') if p.suffix.lower() in ('.exe','.dll','.pyd','.gguf')]
        if forbidden:raise ValueError('Web ZIP 不應包含 PE 或模型權重：'+str(forbidden))
        files={p.relative_to(app).as_posix():digest(p) for p in app.rglob('*') if p.is_file()}
        (app/'WEB_MANIFEST.json').write_text(json.dumps({'version':VERSION,'commit':info['commit'],'files':files,
            'note':'Integrity inventory; not a digital code signature or SAC approval.'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        archive=output/f'LocalLLM-Web-{VERSION}-Windows-x64.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as zipout:
            for file in sorted(bundle.rglob('*')):
                if file.is_file():zipout.write(file,file.relative_to(bundle.parent).as_posix())
    review={**info,'zip':archive.name,'sha256':digest(archive),'bytes':archive.stat().st_size,
        'payload':'Python source + React static files + unchanged hash-pinned pure wheels; no self-built EXE',
        'PE_payloads':0,'SAC':'NOT VERIFIED; scripts/interpreter/native optional runtimes need separate real-device approval'}
    (output/'BUILD.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'SHA256SUMS.txt').write_text(f"{review['sha256']}  {archive.name}\n",encoding='ascii')
    print(json.dumps(review,ensure_ascii=False))
    return review


if __name__=='__main__':build()

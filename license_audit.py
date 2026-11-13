"""Declared-license inventory and SPDX 2.3 evidence; never decides ownership or grants MIT."""
import argparse
import base64
from datetime import datetime, timezone
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import tarfile
import io
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

ROOT=Path(__file__).resolve().parent
WORKSPACE_LICENSE='MIT'
WORKSPACE_COPYRIGHT='Copyright (c) 2026 劉仲軒'
WORKSPACE_SCOPE='First-party code, tests, build scripts and technical documentation only; see LICENSE_SCOPE.md. Third-party components, runtimes, model weights, logos, brand assets, UI screenshots and synthetic media retain separate terms.'
CACHE=ROOT/'build/open-source-audit/cache'
NOTICE=re.compile(r'(?i)(?:^|[/_.-])(licen[cs]e[^/]*|copying[^/]*|notice[^/]*|copyright[^/]*)$')


def fetch(url,network):
    CACHE.mkdir(parents=True,exist_ok=True);path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.bin')
    if path.exists():return path.read_bytes()
    if not network:raise ValueError('Evidence not cached')
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'LocalLLM-license-review/0.7.0 (metadata only)'}),timeout=30) as response:
                if not response.url.startswith('https://'):raise ValueError('Non-HTTPS evidence redirect')
                data=response.read(16*1024**2+1)
            if len(data)>16*1024**2:raise ValueError('Evidence exceeds limit')
            path.write_bytes(data);return data
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)


def declared(value):
    if not isinstance(value,str) or not value.strip():return 'NOASSERTION'
    value=value.strip()
    return {'MIT License':'MIT','Apache 2.0':'Apache-2.0','BSD License':'NOASSERTION',
            'OSI Approved :: Apache Software License':'NOASSERTION'}.get(value,value) if len(value)<180 and '\n' not in value else 'NOASSERTION'


def spdx_expression(value, identifiers, exceptions):
    # Cargo historically used '/' for OR. Preserve the upstream label in the inventory.
    normalized=re.sub(r'\s*/\s*',' OR ',value)
    tokens=re.findall(r'[A-Za-z0-9.+-]+|[()]',normalized)
    if ''.join(tokens)!=re.sub(r'\s+','',normalized):return 'NOASSERTION'
    if not tokens or any(t not in identifiers|exceptions|{'AND','OR','WITH','(',')'} for t in tokens):return 'NOASSERTION'
    position=0
    def expression():
        nonlocal position
        atom()
        while position<len(tokens) and tokens[position] in ('AND','OR'):
            position+=1;atom()
    def atom():
        nonlocal position
        if position>=len(tokens):raise ValueError('Missing license')
        token=tokens[position];position+=1
        if token=='(':
            expression()
            if position>=len(tokens) or tokens[position]!=')':raise ValueError('Missing parenthesis')
            position+=1
        elif token in identifiers:
            if position<len(tokens) and tokens[position]=='WITH':
                position+=1
                if position>=len(tokens) or tokens[position] not in exceptions:raise ValueError('Invalid exception')
                position+=1
        else:raise ValueError('Invalid license')
    try:
        expression()
        if position!=len(tokens):return 'NOASSERTION'
    except ValueError:return 'NOASSERTION'
    return normalized


def identity(ecosystem,name,version):
    return 'SPDXRef-'+hashlib.sha256(f'{ecosystem}:{name}@{version}'.encode()).hexdigest()[:24]


def package(ecosystem,name,version,license,classes,scope,url=None,**extra):
    purl=f'pkg:{ecosystem}/{quote(name,safe="/")}@{version}' if ecosystem in ('npm','pypi','cargo') else None
    return {'id':identity(ecosystem,name,version),'ecosystem':ecosystem,'name':name,'version':version,
        'license_declared':declared(license),'license_concluded':'NOASSERTION','distribution_classes':classes,
        'scope':scope,'source':url,'purl':purl,'notice_files':[],
        'status':'REVIEW REQUIRED' if not license or license=='NOASSERTION' else 'PASS',**extra}


def collect(output,network=False,cargo_metadata=None,crate_archives=False):
    output.mkdir(parents=True,exist_ok=True);notices=output/'license-texts';notices.mkdir(exist_ok=True)
    components=[]
    def notice(component,name,data):
        digest=hashlib.sha256(data).hexdigest();target=notices/(digest+'.txt')
        target.write_bytes(data)
        component['notice_files'].append({'original_name':name,'sha256':digest,'file':'license-texts/'+target.name})
    def directory_notices(component,directory):
        if not directory.is_dir():return
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.resolve().is_relative_to(directory.resolve()) and NOTICE.search(path.name) and path.stat().st_size<1024**2:
                notice(component,path.name,path.read_bytes())
    lock=json.loads((ROOT/'desktop/package-lock.json').read_text(encoding='utf-8'))
    for path,item in lock['packages'].items():
        if not path:continue
        name=item.get('name') or path.rsplit('node_modules/',1)[-1]
        component=package('npm',name,item['version'],item.get('license'),['B'] if not item.get('dev') else [],
            'browser-bundle' if not item.get('dev') else 'build/test; optional platform entries are not all shipped',item.get('resolved'),
            integrity=item.get('integrity'),lock_path=path,optional=bool(item.get('optional')))
        directory_notices(component,ROOT/'desktop'/path)
        components.append(component)
    cargo=tomllib.loads((ROOT/'desktop/src-tauri/Cargo.lock').read_text(encoding='utf-8'))['package']
    resolved={}
    if cargo_metadata:
        resolved={(p['name'],p['version']):p for p in json.loads(cargo_metadata.read_text(encoding='utf-8-sig'))['packages']}
    def crate(item):
        if not item.get('source'):return None
        name,version=item['name'],item['version'];info=resolved.get((name,version));source=f'https://crates.io/crates/{name}/{version}'
        error=None
        if info is None:
            try:info=json.loads(fetch(f'https://crates.io/api/v1/crates/{name}/{version}',network))['version']
            except Exception as failure:info={};error=type(failure).__name__
        return package('cargo',name,version,info.get('license'),['B'],
            'complete lock graph; build/target/optional roles require Cargo graph review',source,
            archive_sha256=item.get('checksum'),repository=info.get('repository'),evidence_error=error,
            manifest_path=info.get('manifest_path'),license_file=info.get('license_file'))
    with ThreadPoolExecutor(max_workers=6) as pool:rust=list(pool.map(crate,cargo))
    def crate_notices(component):
        if component is None:return None
        manifest=component.pop('manifest_path',None);license_file=component.pop('license_file',None)
        if manifest:
            directory=Path(manifest).parent;directory_notices(component,directory)
            if license_file and (directory/license_file).resolve().is_relative_to(directory.resolve()) and (directory/license_file).is_file():notice(component,'declared license_file',(directory/license_file).read_bytes())
        if not component['notice_files'] and crate_archives:
            try:
                data=fetch(f"https://static.crates.io/crates/{component['name']}/{component['name']}-{component['version']}.crate",network)
                if hashlib.sha256(data).hexdigest()!=component['archive_sha256']:raise ValueError('Cargo archive checksum mismatch')
                with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
                    root=f"{component['name']}-{component['version']}"
                    manifest=tomllib.loads(archive.extractfile(root+'/Cargo.toml').read().decode())['package']
                    if component['license_declared']=='NOASSERTION' and manifest.get('license'):
                        component['license_declared']=declared(manifest['license'])
                        component['license_evidence']='Cargo.lock checksum-verified crate manifest'
                    for entry in archive:
                        if entry.isfile() and NOTICE.search(entry.name) and entry.size<1024**2:
                            notice(component,entry.name,archive.extractfile(entry).read())
                    # Monorepo crates sometimes omit shared root LICENSE files.
                    # Retrieve only from the immutable VCS commit embedded in the
                    # checksum-verified archive, never from a floating main branch.
                    if not component['notice_files'] and root+'/.cargo_vcs_info.json' in archive.getnames():
                        vcs=json.loads(archive.extractfile(root+'/.cargo_vcs_info.json').read())
                        repo=(manifest.get('repository') or '').removesuffix('.git').rstrip('/')
                        commit=vcs.get('git',{}).get('sha1','')
                        if re.fullmatch(r'https://github.com/[\w.-]+/[\w.-]+',repo) and re.fullmatch(r'[a-f0-9]{40}',commit):
                            for filename in ('LICENSE','LICENSE.txt','LICENSE-MIT','LICENSE-APACHE','COPYING','LICENSE.md'):
                                url=repo.replace('https://github.com/','https://raw.githubusercontent.com/')+'/'+commit+'/'+filename
                                try:
                                    body=fetch(url,network)
                                    notice(component,filename,body)
                                    component.setdefault('upstream_notice_sources',[]).append(url)
                                except Exception:pass
            except Exception as error:component['notice_error']=type(error).__name__
        if not component['notice_files']:component['notice_status']='REVIEW REQUIRED: body not present locally; metadata alone is not a notice bundle'
        return component
    with ThreadPoolExecutor(max_workers=6) as pool:components.extend(c for c in pool.map(crate_notices,rust) if c)
    pins=[line.strip().split('==') for line in (ROOT/'desktop/requirements-windows.lock').read_text().splitlines() if '==' in line]
    audit_pins=[line.strip().split('==') for line in (ROOT/'desktop/requirements-audit.lock').read_text().splitlines() if '==' in line]
    locations=[str(ROOT/'build/packager'),*sys.path]
    installed={d.metadata['Name'].lower().replace('_','-'):d for d in metadata.distributions(path=locations) if d.metadata.get('Name')}
    for name,version in [*pins,*audit_pins]:
        dist=installed.get(name.lower().replace('_','-'));info={};evidence='local installed metadata'
        if dist is None or dist.version!=version:
            try:info=json.loads(fetch(f'https://pypi.org/pypi/{name}/{version}/json',network))['info'];evidence='pypi exact-version metadata'
            except Exception:pass
        license=(dist.metadata.get('License-Expression') or dist.metadata.get('License')) if dist and dist.version==version else info.get('license_expression') or info.get('license')
        component=package('pypi',name,version,license,['B'] if name.lower() in ('cryptography','cffi','pycparser') else [],
            'worker dependency' if name.lower() in ('cryptography','cffi','pycparser') else 'build tooling; PyInstaller bootloader also in worker',f'https://pypi.org/project/{name}/{version}/',evidence=evidence)
        if name.lower()=='pyinstaller':component['license_declared']='GPL-2.0-or-later WITH Bootloader-exception'
        if dist and dist.version==version:
            for file in dist.files or []:
                if NOTICE.search(str(file)):
                    path=Path(dist.locate_file(file))
                    if path.is_file() and path.stat().st_size<1024**2:notice(component,str(file),path.read_bytes())
        components.append(component)
    python=package('runtime','CPython','3.12.10','Python-2.0',['B','C'],'interpreter and stdlib; bundled subcomponents retain their own terms','https://www.python.org/downloads/release/python-31210/')
    notice(python,'CPython LICENSE.txt',(Path(sys.base_prefix)/'LICENSE.txt').read_bytes());components.append(python)
    for filename in ['LICENSE-LLVM-OpenMP','LICENSE-llama.cpp']:
        path=ROOT/'engine-vulkan'/filename
        component=package('runtime',filename,'b11810','Apache-2.0 WITH LLVM-exception' if 'LLVM' in filename else 'MIT',['C'],'downloaded llama.cpp dependency', 'https://github.com/ggml-org/llama.cpp/releases/tag/b11810')
        if path.is_file():notice(component,filename,path.read_bytes())
        components.append(component)
    extras=[
        ('ComfyUI','v0.44.0','GPL-3.0-only','https://raw.githubusercontent.com/Comfy-Org/ComfyUI/v0.44.0/LICENSE','C'),
        ('OpenSSL','CPython/cryptography bundled versions','Apache-2.0','https://raw.githubusercontent.com/openssl/openssl/openssl-3.0/LICENSE.txt','B'),
        ('WebLLM','0.2.87','Apache-2.0','https://registry.npmjs.org/@mlc-ai/web-llm/0.2.87','C')]
    for name,version,license,url,group in extras:
        component=package('runtime',name,version,license,[group],'separate downloaded runtime; binary transitive contents require separate review' if group=='C' else 'bundled crypto library; exact PE version recorded separately',url)
        try:
            data=fetch(url,network)
            if name=='WebLLM':
                value=json.loads(data);component['license_declared']=declared(value.get('license'));component['dependencies']=value.get('dependencies',{})
            else:notice(component,'upstream LICENSE',data)
        except Exception as error:component.update(status='REVIEW REQUIRED',evidence_error=type(error).__name__)
        components.append(component)
    manifest=json.loads((ROOT/'openvino-packages.lock.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        name,version=item['name'],item['version'];wheel=ROOT/'build/ov-wheelhouse'/item['file']
        component=package('pypi' if item['file'].endswith('.whl') else 'runtime',name,version,None,['C'],'optional OpenVINO runtime',item['url'],archive_sha256=item['sha256'])
        if wheel.is_file():
            if hashlib.sha256(wheel.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Optional wheel evidence checksum mismatch')
            with zipfile.ZipFile(wheel) as archive:
                for path in archive.namelist():
                    if path.endswith('.dist-info/METADATA'):
                        from email.parser import BytesParser
                        meta=BytesParser().parsebytes(archive.read(path));component['license_declared']=declared(meta.get('License-Expression') or meta.get('License'))
                    if NOTICE.search(path) and not path.endswith('/') and archive.getinfo(path).file_size<1024**2:notice(component,path,archive.read(path))
        component['status']='REVIEW REQUIRED' if component['license_declared']=='NOASSERTION' else 'PASS'
        components.append(component)
    from media_install import MODELS_FOR_INSTALL
    for kind,model in MODELS_FOR_INSTALL.items():
        license=model.license if model.license in ('apache-2.0','mit') else 'LicenseRef-CreativeML-OpenRAIL-M'
        component=package('model',kind,model.version,{'apache-2.0':'Apache-2.0','mit':'MIT'}.get(license,license),['C'],'weights not included in installer; use and redistribution terms remain separate',f'https://huggingface.co/{model.repo}/tree/{model.revision}',revision=model.revision,
            weights=[{'file':w.filename,'sha256':w.sha256,'bytes':w.bytes} for w in model.weights])
        component['status']='REVIEW REQUIRED';components.append(component)
    components.extend([
        package('system','Microsoft VC/UCRT/API sets','PE inventory specific','LicenseRef-Microsoft-Redistributable',['B'],'redistribution rights/System Library exception require confirmation','https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files',status='REVIEW REQUIRED'),
        package('runtime','ComfyUI portable transitive CUDA/PyTorch/FFmpeg','profile-specific','NOASSERTION',['C'],'not fully enumerated by top-level GPL license; no multi-GB download in this audit',status='REVIEW REQUIRED'),
        package('model','arbitrary Hugging Face/GGUF/user weights','user-selected','NOASSERTION',['C','D'],'each upstream model card and conversion must be checked; not MIT by file format',status='REVIEW REQUIRED'),
        package('toolchain','Rust standard library/NSIS/WebView2','CI toolchain-specific','NOASSERTION',['B'],'linker/installer generated code and system bootstrapper need separate notices',status='REVIEW REQUIRED')])
    schema_url='https://raw.githubusercontent.com/spdx/spdx-spec/v2.3/schemas/spdx-schema.json'
    schema=fetch(schema_url,network)
    schema_component=package('data','SPDX specification JSON schema','2.3','CC-BY-3.0',['A','B'],
        'unmodified validation schema; SPDX project attribution and upstream license retained',schema_url,archive_sha256=hashlib.sha256(schema).hexdigest())
    notice(schema_component,'SPDX specification LICENSE',fetch('https://raw.githubusercontent.com/spdx/spdx-spec/v2.3/LICENSE',network))
    components.append(schema_component)
    identifiers=json.loads(fetch('https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/json/licenses.json',network))
    exceptions=json.loads(fetch('https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/json/exceptions.json',network))
    license_ids={i['licenseId'] for i in identifiers['licenses']}|{'NOASSERTION','NONE'}
    exception_ids={i['licenseExceptionId'] for i in exceptions['exceptions']}
    for component in components:
        component['license_spdx']=spdx_expression(component['license_declared'],license_ids,exception_ids)
        component['status']='REVIEW REQUIRED' if component['license_spdx']=='NOASSERTION' or not component['notice_files'] else component['status']
    (output/'spdx-schema.json').write_bytes(schema)
    (output/'schema-attribution.txt').write_text('Unmodified SPDX 2.3 JSON schema, published by the SPDX project.\nSource: '+schema_url+'\nLicense: CC-BY-3.0; original license indexed in DEPENDENCY_LICENSES.json.\nSPDX metadata CC0 does not relicense the schema or application.\n',encoding='utf-8')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    result={'schema':1,'source_commit':head,'workspace_license':WORKSPACE_LICENSE,'first_party_license_status':'ADOPTED',
        'workspace_license_scope':WORKSPACE_SCOPE,
        'coverage':{'npm_lock_entries':len(lock['packages'])-1,'cargo_lock_dependencies':len(cargo)-1,'python_build_pins':len(pins),'python_audit_pins':len(audit_pins)},
        'components':components,'legal_eligibility':'REVIEW REQUIRED; scan success is not legal approval'}
    (output/'DEPENDENCY_LICENSES.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    packages=[{'SPDXID':item['id'],'name':item['name'],'versionInfo':item['version'],'downloadLocation':item['source'] or 'NOASSERTION',
        'filesAnalyzed':False,'licenseConcluded':'NOASSERTION','licenseDeclared':item['license_spdx'],
        'copyrightText':'NOASSERTION','comment':json.dumps({'distribution_classes':item['distribution_classes'],'scope':item['scope'],'status':item['status']})} for item in components]
    # Multiple contexts may use the same package/version. Keep a single SPDX identity.
    packages=list({p['SPDXID']:p for p in packages}.values())
    components_by_id={c['id']:c for c in components}
    for entry in packages:
        component=components_by_id[entry['SPDXID']]
        if component['purl']:entry['externalRefs']=[{'referenceCategory':'PACKAGE-MANAGER','referenceType':'purl','referenceLocator':component['purl']}]
        if component.get('archive_sha256'):entry['checksums']=[{'algorithm':'SHA256','checksumValue':component['archive_sha256']}]
        elif (component.get('integrity') or '').startswith('sha512-'):
            entry['checksums']=[{'algorithm':'SHA512','checksumValue':base64.b64decode(component['integrity'].split('-',1)[1]).hex()}]
    bom={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':'LocalLLM-Workspace-0.7.0-license-review',
        'documentNamespace':f'https://github.com/liu11-21/local-llm/sbom/{head}/license-review-'+hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()[:16],
        'creationInfo':{'creators':['Tool: LocalLLM license_audit.py'],'created':datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
        'packages':[{'SPDXID':'SPDXRef-Workspace','name':'Local LLM Workspace','versionInfo':'0.7.0','downloadLocation':'https://github.com/liu11-21/local-llm',
                     'filesAnalyzed':False,'licenseConcluded':'NOASSERTION','licenseDeclared':WORKSPACE_LICENSE,
                     'copyrightText':WORKSPACE_COPYRIGHT,'comment':WORKSPACE_SCOPE},*packages],
        'relationships':[{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'SPDXRef-Workspace'},
                        *[{'spdxElementId':'SPDXRef-Workspace','relationshipType':'DEPENDS_ON','relatedSpdxElement':p['SPDXID']} for p in packages]],
        'comment':'Nonstandard or uncollected license texts are NOASSERTION in SPDX; upstream labels and review issues remain in DEPENDENCY_LICENSES.json. No placeholder license body is fabricated.'}
    (output/'workspace.spdx.json').write_text(json.dumps(bom,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# Third-party inventory — generated, not a project license grant','',f'Source: {head}',
           'A: tracked repository. B: installer or potential compiled dependency. C: downloaded after installation. D: user supplied.',
           'Declared licenses are upstream metadata, not an independent legal conclusion. Complete lock graph includes non-shipped build/optional targets.','',
           '| Ecosystem | Component | Version | Declared license | Class | Scope |','|---|---|---|---|---|---|']
    for item in components:lines.append('| '+' | '.join(str(item[k]).replace('|','\\|') for k in ('ecosystem','name','version','license_declared'))+' | '+','.join(item['distribution_classes'])+' | '+item['scope']+' |')
    (output/'THIRD_PARTY_NOTICES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if output.resolve()==(ROOT/'docs/sbom').resolve():
        root_inventory=json.loads(json.dumps(result))
        for component in root_inventory['components']:
            for entry in component['notice_files']:entry['file']='docs/sbom/'+entry['file']
        (ROOT/'DEPENDENCY_LICENSES.json').write_text(json.dumps(root_inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'components':len(components),'coverage':result['coverage'],'declared_unknown':sum(c['license_declared']=='NOASSERTION' for c in components),'notice_texts':len(list(notices.glob('*.txt')))}))


def validate(directory):
    import jsonschema
    inventory=json.loads((directory/'DEPENDENCY_LICENSES.json').read_text(encoding='utf-8'))
    bom=json.loads((directory/'workspace.spdx.json').read_text(encoding='utf-8'))
    jsonschema.validate(bom,json.loads((directory/'spdx-schema.json').read_text(encoding='utf-8')))
    ids={p['SPDXID'] for p in bom['packages']}|{'SPDXRef-DOCUMENT'}
    assert bom['spdxVersion']=='SPDX-2.3' and len(ids)==len(bom['packages'])+1
    for relationship in bom['relationships']:assert relationship['spdxElementId'] in ids and relationship['relatedSpdxElement'] in ids
    for component in inventory['components']:
        for entry in component['notice_files']:
            path=(directory/entry['file']).resolve();assert path.is_relative_to(directory.resolve())
            assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    print(json.dumps({'status':'PASS','scope':'official SPDX 2.3 JSON schema/references/notice integrity; legal eligibility not approved'}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('collect','validate'))
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--network',action='store_true');parser.add_argument('--cargo-metadata',type=Path)
    parser.add_argument('--crate-archives',action='store_true',help='Fetch hash-verified source archives for missing license bodies; no AI weights')
    args=parser.parse_args()
    collect(args.output,args.network,args.cargo_metadata,args.crate_archives) if args.action=='collect' else validate(args.output)

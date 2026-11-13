"""Read-only source provenance and redacted reachable-history screening."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parent
PATTERNS={
    'github-token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{50,255})\b'),
    'provider-key':re.compile(rb'\b(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{25,200}|AIza[A-Za-z0-9_-]{35}|AKIA[A-Z0-9]{16})\b'),
    'private-key-material':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{64,}'),
    'user-path':re.compile(rb'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s"<>]{2,80}'),
}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def category(name):
    path=Path(name)
    if name.startswith(('third_party/','docs/sbom/license-texts/')) or name=='docs/sbom/spdx-schema.json':
        return 'vendored-license-or-schema'
    if path.suffix.lower() in ('.png','.ico','.svg','.webm','.flac','.jpg','.jpeg'):
        return 'media-fixture' if 'media-fixtures/' in name else 'asset-or-screenshot'
    if name.startswith('.github/') or path.suffix in ('.ps1','.cmd','.iss','.lock') or path.name in ('Cargo.toml','package.json','package-lock.json'):
        return 'build-and-dependency-manifest'
    if path.suffix in ('.py','.tsx','.ts','.rs','.mjs','.css','.html'):
        return 'project-source'
    return 'documentation-and-evidence'


def scan(output):
    output.mkdir(parents=True,exist_ok=True)
    head=git('rev-parse','HEAD').decode().strip()
    commits=git('rev-list','--all').decode().splitlines()
    files=git('ls-tree','-r','--name-only','-z','HEAD').decode().strip('\0').split('\0')
    inventory=[]
    for name in files:
        path=ROOT/name
        history=git('log','--follow','--format=%H|%an','--',name).decode('utf-8',errors='replace').splitlines()
        authors=sorted({line.split('|',1)[1] for line in history if '|' in line})
        kind=category(name)
        third_party=kind=='vendored-license-or-schema'
        llama=name=='third_party/llama.cpp-b11810-LICENSE'
        inventory.append({'path':name,'sha256':hashlib.sha256(git('show','HEAD:'+name)).hexdigest(),'category':kind,
            'observed_commit_authors':authors,'first_observed_commit':history[-1].split('|')[0] if history else None,
            'original_author':'The ggml authors (from unchanged license text)' if llama else 'Original notices retain upstream attribution; see SBOM index' if third_party else 'NOT VERIFIED; commit authors are not legal ownership proof',
            'source':'https://github.com/ggml-org/llama.cpp/blob/b11810/LICENSE' if llama else 'docs/sbom/DEPENDENCY_LICENSES.json source and notice index' if third_party else 'Repository history; external/AI/material provenance not independently established',
            'declared_license':'MIT' if llama else 'Per upstream text and SBOM; not project MIT' if third_party else 'NOASSERTION',
            'mit_relicensing':'NO; retain upstream license' if third_party else 'BLOCKED pending rights confirmation',
            'retain_original_license':third_party,'third_party_consent':'Not needed to preserve existing upstream notice' if third_party else 'REVIEW REQUIRED if external contributions/materials',
            'status':'PASS' if third_party else 'REVIEW REQUIRED'})
    findings=[];objects=git('rev-list','--objects','--all').decode('utf-8',errors='replace').splitlines()
    process=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    checked=0;skipped=0
    try:
        for item in objects:
            sha,_,name=item.partition(' ')
            process.stdin.write((sha+'\n').encode());process.stdin.flush()
            header=process.stdout.readline().decode().split()
            if len(header)!=3:raise RuntimeError('Unexpected git object stream')
            size=int(header[2]);data=process.stdout.read(size);process.stdout.read(1)
            if header[1]!='blob':continue
            if size>4*1024**2 or b'\0' in data[:8192]:skipped+=1;continue
            checked+=1
            for kind,pattern in PATTERNS.items():
                for match in pattern.finditer(data):
                    findings.append({'path':name,'blob':sha,'line':data.count(b'\n',0,match.start())+1,
                        'type':kind,'fingerprint':hashlib.sha256(match.group()).hexdigest()[:12],
                        'status':'REVIEW REQUIRED','classification':'privacy-metadata' if kind=='user-path' else 'credential-pattern-candidate',
                        'secret_value':'NOT EXPORTED'})
    finally:
        process.stdin.close();process.wait(timeout=15);process.stdout.close()
    report={'head':head,'reachable_commits':len(commits),'reachable_text_blobs_checked':checked,
        'binary_or_large_blobs_not_semantically_inspected':skipped,'findings':findings,
        'credential_status':'REVIEW REQUIRED' if any(x['type']!='user-path' for x in findings) else 'No matching credential patterns found; not proof of absence',
        'limitations':['Offline pattern screening; no token validation or use','Screenshots/large/binary objects require human content review',
                      'Commit author names/emails are public metadata, not ownership evidence','No Git history was rewritten'],
        'current_file_categories':dict(Counter(item['category'] for item in inventory))}
    (output/'source-ownership.json').write_text(json.dumps({'head':head,'proposed_attribution':'劉仲軒','rights_confirmation':'PENDING','files':inventory},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'public-history-screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'files':len(inventory),'commits':len(commits),'text_blobs':checked,'findings_by_type':dict(Counter(x['type'] for x in findings))}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    scan(parser.parse_args().output)

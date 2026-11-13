"""Prepare review notices and verify unsigned candidate evidence, without signing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from license_audit import validate

ROOT = Path(__file__).resolve().parent
POLICIES = ('LICENSE', 'PRIVACY.md', 'SECURITY.md', 'CODE_SIGNING_POLICY.md',
            'THIRD_PARTY_LICENSES.md', 'RELEASE_PROCESS.md')


def seed(directory):
    if not directory.exists():
        shutil.copytree(ROOT / 'docs/sbom', directory)
    for name in POLICIES:
        shutil.copyfile(ROOT / name, directory / name)
    shutil.copyfile(ROOT / 'docs/legal/LICENSE-MIT.candidate.txt', directory / 'LICENSE-MIT.candidate.txt')
    shutil.copyfile(ROOT / 'third_party/llama.cpp-b11810-LICENSE', directory / 'llama.cpp-b11810-LICENSE')
    for name in ('LICENSE_AUDIT.md', 'THIRD_PARTY_LICENSES.md', 'CODE_SIGNING_POLICY.md',
                 'RELEASE_SIGNING_PLAN.md', 'OPEN_SOURCE_BLOCKERS.md', 'PRIVACY_STORAGE.md'):
        (directory / 'docs').mkdir(exist_ok=True)
        shutil.copyfile(ROOT / 'docs' / name, directory / 'docs' / name)
    (directory / 'docs/legal').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'docs/legal/LICENSE-MIT.candidate.txt', directory / 'docs/legal/LICENSE-MIT.candidate.txt')
    (directory / 'README.txt').write_text(
        'Unsigned review candidate; MIT NOT ADOPTED; SignPath NOT APPLIED.\n'
        'DEPENDENCY_LICENSES.json indexes original license-texts/ by SHA-256.\n'
        'workspace.spdx.json is a review SBOM, not a legal approval.\n'
        'Missing notices and source obligations remain REVIEW REQUIRED.\n'
        'Full current source/docs: https://github.com/liu11-21/local-llm/tree/dev/desktop-workspace\n', encoding='utf-8')
    (directory / 'STATUS.json').write_text(json.dumps({
        'version': '0.7.0', 'channel': 'Development', 'project_license': 'NOASSERTION',
        'mit_candidate_attribution': '劉仲軒', 'rights_confirmation': 'PENDING',
        'signpath': 'NOT APPLIED; NOT APPROVED', 'distribution': 'unsigned review candidate',
        'third_party': 'Original terms apply; this directory grants no project-wide MIT license',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def prepare(directory):
    seed(directory)
    validate(directory)


def verify(directory):
    build = json.loads((directory / 'BUILD.json').read_text(encoding='utf-8-sig'))
    inventory = json.loads((directory / 'installed-pe-inventory.json').read_text(encoding='utf-8-sig'))
    assert build['authenticode'] == 'NotSigned' and build['version'] == '0.7.0'
    assert inventory['source_commit'] == build['commit']
    files = inventory['files']
    assert any(f['path'] == 'localllm-desktop.exe' for f in files)
    assert any(f['path'] == 'uninstall.exe' for f in files)
    assert any(f['path'] == 'worker/LocalLLMWorker.exe' for f in files)
    assert all(len(f['sha256']) == 64 and not Path(f['path']).is_absolute() for f in files)
    installer = next(directory.glob('*.exe'))
    assert hashlib.sha256(installer.read_bytes()).hexdigest() == build['sha256']
    validate(directory / 'notices')
    print(json.dumps({'status': 'PASS', 'pe_count': len(files),
                      'scope': 'candidate consistency only; no rights or SignPath approval'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare-notices', 'verify'))
    parser.add_argument('--directory', type=Path, required=True)
    options = parser.parse_args()
    (prepare if options.action == 'prepare-notices' else verify)(options.directory)

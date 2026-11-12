"""Validate first-party versions only, optionally including a built worker/installer record."""
import argparse
import ast
import json
from pathlib import Path
import tomllib
import subprocess
from tempfile import TemporaryDirectory
from workspace_version import VERSION, CHANNEL, require_identity

ROOT = Path(__file__).resolve().parent


def check(root=ROOT, build=None):
    desktop = root / 'desktop'
    package = json.loads((desktop / 'package.json').read_text(encoding='utf-8'))
    lock = json.loads((desktop / 'package-lock.json').read_text(encoding='utf-8'))
    cargo = tomllib.loads((desktop / 'src-tauri/Cargo.toml').read_text(encoding='utf-8'))
    cargo_lock = tomllib.loads((desktop / 'src-tauri/Cargo.lock').read_text(encoding='utf-8'))
    own, = [entry for entry in cargo_lock['package'] if entry['name'] == cargo['package']['name']]
    tree = ast.parse((root / 'desktop_worker.py').read_text(encoding='utf-8'))
    worker, = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'WORKSPACE_VERSION' for target in node.targets)]
    versions = {'npm': package['version'], 'npm_lock': lock['version'], 'npm_lock_root': lock['packages']['']['version'],
                'cargo': cargo['package']['version'], 'cargo_lock': own['version'],
                'tauri': json.loads((desktop / 'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))['version'],
                'worker': worker, 'identity': VERSION}
    if any(value != VERSION for value in versions.values()):
        raise ValueError(f'Workspace versions disagree: {versions}')
    if build:
        data = json.loads(Path(build).read_text(encoding='utf-8-sig'))
        require_identity(data)
        if not data.get('commit') or data.get('commit') == 'unknown':
            raise ValueError('Packaged build must identify its source commit')
        versions['build'] = data['version']
    return {'status':'PASS', 'version':VERSION, 'channel':CHANNEL, 'versions':versions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    result = check(build=args.build)
    if args.worker:
        with TemporaryDirectory() as directory:
            run = subprocess.run([str(args.worker.resolve()), '--data', directory],
                input=json.dumps({'op':'build-info','data':{}})+'\n', text=True,
                encoding='utf-8', capture_output=True, timeout=40, check=True)
        value = json.loads(run.stdout)
        if not value.get('ok'):
            raise ValueError('Packaged worker failed its identity handshake')
        from workspace_version import build_info
        require_identity(value['value'], expected_commit=build_info()['commit'])
        result['packaged_worker'] = value['value']
    print(json.dumps(result, ensure_ascii=False))

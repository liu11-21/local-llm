import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import build_windows
import license_audit


class LicenseAuditTests(unittest.TestCase):
    def test_spdx_normalization_does_not_invent_license_or_exception(self):
        ids={'MIT','Apache-2.0'};exceptions={'LLVM-exception'}
        self.assertEqual(license_audit.spdx_expression('MIT/Apache-2.0',ids,exceptions),'MIT OR Apache-2.0')
        for raw in ('MIT OR','MIT WITH Apache-2.0','Made-Up-License','(MIT','MIT MIT'):
            self.assertEqual(license_audit.spdx_expression(raw,ids,exceptions),'NOASSERTION')

    def test_inventory_covers_entire_lock_graph_and_preserves_unknown_rights(self):
        root = Path(__file__).resolve().parent
        data = json.loads((root / 'docs/sbom/DEPENDENCY_LICENSES.json').read_text(encoding='utf-8'))
        npm = json.loads((root / 'desktop/package-lock.json').read_text(encoding='utf-8'))
        import tomllib
        cargo = tomllib.loads((root / 'desktop/src-tauri/Cargo.lock').read_text(encoding='utf-8'))
        self.assertEqual(sum(c['ecosystem'] == 'npm' for c in data['components']), len(npm['packages']) - 1)
        self.assertEqual(sum(c['ecosystem'] == 'cargo' for c in data['components']), len(cargo['package']) - 1)
        self.assertEqual(data['workspace_license'], 'NOASSERTION')
        self.assertTrue(all(c['license_concluded'] == 'NOASSERTION' for c in data['components']))

    def test_modified_notice_is_rejected(self):
        source = Path(__file__).resolve().parent / 'docs/sbom'
        inventory = json.loads((source / 'DEPENDENCY_LICENSES.json').read_text(encoding='utf-8'))
        component = next(c for c in inventory['components'] if c['notice_files'])
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name in ('workspace.spdx.json', 'spdx-schema.json'):
                (directory / name).write_bytes((source / name).read_bytes())
            item = copy.deepcopy(component)
            item['notice_files'] = item['notice_files'][:1]
            entry = item['notice_files'][0]
            (directory / entry['file']).parent.mkdir(parents=True)
            (directory / entry['file']).write_bytes(b'changed license')
            (directory / 'DEPENDENCY_LICENSES.json').write_text(json.dumps({'components': [item]}))
            with self.assertRaises(AssertionError), contextlib.redirect_stdout(io.StringIO()):
                license_audit.validate(directory)

    def test_signing_never_targets_upstream_binary(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = Path(temp)
            for name in ('LocalLLM.exe', 'python312.dll', 'llama-server.exe', 'crypto.pyd'):
                (payload / name).write_bytes(b'test placeholder')
            with patch.object(build_windows.shutil, 'which', return_value='signtool.exe'), patch.object(
                build_windows.subprocess, 'run', return_value=Mock(returncode=1)
            ) as run:
                build_windows.build_installer('ISCC.exe', payload, 'a' * 40)
            signing_targets = [str(call.args[0][-1]) for call in run.call_args_list if 'sign' in call.args[0]]
            self.assertEqual(signing_targets, [str(payload / 'LocalLLM.exe')])

    def test_signing_workflow_cannot_request_service(self):
        root = Path(__file__).resolve().parent
        workflow = (root / '.github/workflows/signing-review.yml').read_text(encoding='utf-8')
        self.assertIn('if: ${{ false }}', workflow)
        self.assertNotIn('uses:', workflow)
        self.assertNotIn('secrets.', workflow)
        self.assertNotIn('pull_request', workflow)
        self.assertNotIn('push:', workflow)


if __name__ == '__main__':
    unittest.main()

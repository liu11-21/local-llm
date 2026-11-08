import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import patch

from hardware import GIB
from load_plan import LoadPlan
from model_team import cloud_member, run_team, team_fits


class CloudReply(io.BytesIO):
    def __init__(self, status, content):
        super().__init__(json.dumps(content).encode())
        self.status = status


class ModelTeamTests(unittest.TestCase):
    def test_combined_memory_budget(self):
        first = LoadPlan('Vulkan0', 10, 10, 2 * GIB, GIB, GIB, 3 * GIB)
        second = LoadPlan('Vulkan0', 10, 10, 2 * GIB, GIB, GIB, 4 * GIB)
        other_gpu = LoadPlan('Vulkan1', 10, 10, 2 * GIB, GIB, GIB, 4 * GIB)
        self.assertTrue(team_fits([first], 4 * GIB))
        self.assertFalse(team_fits([first, second], 8 * GIB))
        self.assertFalse(team_fits([first, other_gpu], 2 * GIB))
        self.assertFalse(team_fits([first, other_gpu], None))
        self.assertTrue(team_fits([first, other_gpu], 8 * GIB))

    def test_partial_run_saves_draft_and_only_merges_successful_answers(self):
        members = [cloud_member('Lead', 'https://a.invalid/v1', 'lead', 'secret-key-a'),
                   cloud_member('Other', 'https://b.invalid/v1/chat/completions/', 'other', 'secret-key-b')]
        captured = {}

        class Connection:
            def __init__(self, host, port, timeout):
                self.host = host

            def request(self, method, path, body, headers):
                self.call = (method, path, json.loads(body), headers['Authorization'])
                captured.setdefault(self.host, []).append(self.call)

            def getresponse(self):
                if self.host == 'b.invalid':
                    return CloudReply(429, {'error': 'do not save secret-key-b'})
                content = 'Final answer' if len(captured[self.host]) == 2 else 'Draft with secret-key-a'
                return CloudReply(200, {'choices': [{'message': {'content': content}}]})

            def close(self):
                pass

        with TemporaryDirectory() as directory, patch('model_team.http.client.HTTPSConnection', Connection):
            result = run_team(members, 0, 'Same prompt', None, Path(directory), Event(), lambda _: None,
                              lambda *_: None)
            self.assertEqual(result.answer, 'Final answer')
            self.assertEqual(result.failures, 1)
            manifest = json.loads((result.directory / 'run.json').read_text(encoding='utf-8'))
            self.assertEqual([row['status'] for row in manifest['members']], ['saved', 'failed'])
            self.assertEqual((result.directory / 'answer.md').read_text(encoding='utf-8'), 'Final answer\n')
            self.assertNotIn('secret-key', '\n'.join(p.read_text(encoding='utf-8') for p in result.directory.iterdir()))
        for host in ('a.invalid', 'b.invalid'):
            verb, path, body, _ = captured[host][0]
            self.assertEqual((verb, path), ('POST', '/v1/chat/completions'))
            self.assertEqual(body['messages'], [{'role': 'user', 'content': 'Same prompt'}])
        merge = captured['a.invalid'][1][2]['messages'][0]['content']
        self.assertIn('Draft with', merge)
        self.assertNotIn('secret-key', merge)
        self.assertNotIn('Other', merge)

    def test_cancelled_run_never_calls_cloud(self):
        members = [cloud_member('', 'https://a.invalid/v1', 'lead', 'secret-key-a'),
                   cloud_member('', 'https://a.invalid/v1', 'other', 'secret-key-b')]
        cancel = Event()
        cancel.set()
        with TemporaryDirectory() as directory, patch('model_team.http.client.HTTPSConnection') as connect:
            result = run_team(members, 0, 'Same prompt', None, Path(directory), cancel, lambda _: None,
                              lambda *_: None)
            connect.assert_not_called()
            self.assertFalse((result.directory / 'answer.md').exists())
            self.assertEqual(json.loads((result.directory / 'run.json').read_text(encoding='utf-8'))['status'],
                             'cancelled')


if __name__ == '__main__':
    unittest.main()

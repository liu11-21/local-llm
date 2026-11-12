import ssl
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from desktop_worker import Desktop
from urllib.error import HTTPError
from workspace_errors import explain, user_message
from runtime_contract import capability, external_capability, colab_capability, task_health
from runtime_recommendation import compare


class IntegrationTests(unittest.TestCase):
    def test_openvino_model_refresh_never_looks_up_an_external_provider(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder))
            try:
                with patch.object(app.openvino,'status',return_value={'installed':True,'models':[{'id':'local-model'}]}),patch.object(app.providers,'get',side_effect=AssertionError('must remain local')):
                    self.assertEqual(app.rpc('runtime-models-refresh',{'runtime':'openvino'}),{'id':'openvino','models':['local-model'],'connected':True})
            finally:app.close()
    def test_recoverable_errors_are_understandable_and_redacted(self):
        cases=[(FileNotFoundError('missing.gguf'),'NOT_INSTALLED'), (PermissionError('denied'),'ACCESS_DENIED'),
            (ssl.SSLError('certificate expired'),'TLS_VERIFY_FAILED'), (TimeoutError(),'TIMEOUT'),
            (ValueError('SHA-256 mismatch'),'INTEGRITY_FAILED'), (ValueError('VRAM out of memory'),'RESOURCE_LIMIT'),
            (ValueError('格式不相容'),'INCOMPATIBLE'), (ConnectionError('offline'),'CONNECTION_LOST'),
            (RuntimeError('unexpected Python Exception'),'WORK_FAILED')]
        for error,code in cases:
            with self.subTest(code=code):
                result=explain(error);self.assertEqual(result['code'],code)
                self.assertTrue(result['recovery']);self.assertNotIn('Python Exception',user_message(result))
        policy=OSError('blocked');policy.winerror=4551
        self.assertIn('下載中斷',user_message(explain(RuntimeError('下載中斷，已保存片段。'))))
        self.assertEqual(explain(OSError('受控下載中斷'))['code'],'DOWNLOAD_INTERRUPTED')
        self.assertEqual(explain(policy)['code'],'POLICY_BLOCKED')
        result=explain(HTTPError('https://host.invalid/?token=private',401,'Bearer secret-value',{},None))
        self.assertNotIn('private',str(result));self.assertNotIn('secret-value',str(result))

    def test_runtime_connection_does_not_grant_other_tasks(self):
        cloud=external_capability({'id':'cloud','label':'Cloud','kind':'cloud','host':'example.org','port':443,'models':['demo'],'connected':True})
        colab=colab_capability(True)
        for record in (cloud,colab):
            self.assertEqual(task_health(record,'video'),'unknown')
            self.assertEqual(compare(record,'video','wan21')['state'],'incompatible')
        host=capability('host','Host','remote-host','Local LLM',connected=True,health='ready',network=True,
                        tasks=['video'],models=['wan21'],formats=['safetensors'])
        self.assertEqual(compare(host,'video','wan21')['state'],'incompatible')

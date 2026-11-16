import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from runtime_discovery import inventory,resolve_runtime,app_execution_target,candidate,validate
from runtime_manager import RuntimeManager
from runtime_probe import run_probe,ProbeError
from llama_app_engine import engine_profile

VALID={'status':'Valid','signer':'CN=Hugging Face, O=Hugging Face'}
CAPS={'version':'1.0.0-dev build 12360','devices':[],'probes':[{'argv':['llama.exe','version'],'exit_code':0}]}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        self.exe=self.root/'llama.exe';self.exe.write_bytes(b'controlled fixture, never executed')
    def tearDown(self):self.temp.cleanup()

    def inventory_with(self,process='',user='',system='',local_data=()):
        with patch.dict(os.environ,{'PATH':process,'LOCALAPPDATA':str(self.root/'absent')},clear=False),patch('runtime_discovery.registry_paths',return_value={
            'paths':[('user_path',user),('system_path',system)],'local_data':list(local_data),'errors':[]}):return inventory()

    def test_user_path_found_even_when_process_path_is_stale(self):
        result=self.inventory_with(user=str(self.root))
        self.assertEqual(result['found'][0]['sources'],['user_path'])
        self.assertEqual(result['found'][0]['input_path'],str(self.exe))

    def test_system_path_found_and_all_versions_are_retained(self):
        other=self.root/'v2';other.mkdir();(other/'llama.exe').write_bytes(b'other fixture')
        result=self.inventory_with(user=str(self.root),system=str(other))
        self.assertEqual(len(result['found']),2)
        self.assertEqual(result['found'][1]['sources'],['system_path'])

    def test_process_path_and_duplicate_sources_are_not_lost(self):
        result=self.inventory_with(process=str(self.root),user=str(self.root))
        self.assertEqual(len(result['found']),1)
        self.assertEqual(result['found'][0]['sources'],['process_path','user_path'])

    def test_current_directory_and_remote_path_are_not_searched(self):
        result=self.inventory_with(process=os.pathsep.join(['.',r'\\server\share']))
        self.assertFalse(result['found'])

    def test_official_windows_apps_location_without_path(self):
        local=self.root/'local';apps=local/'Microsoft/WindowsApps';apps.mkdir(parents=True)
        (apps/'llama.exe').write_bytes(b'fixture')
        result=self.inventory_with(local_data=[str(local)])
        self.assertEqual(result['found'][0]['sources'],['windows_apps'])

    def test_appexeclink_target_format_and_malformed_data(self):
        strings='package\0application\0C:\\Official\\llama.exe\0kind\0'.encode('utf-16-le')
        payload=struct.pack('<I',4)+strings;raw=struct.pack('<IHH',0x8000001B,len(payload),0)+payload
        self.assertEqual(app_execution_target(raw),r'C:\Official\llama.exe')
        self.assertIsNone(app_execution_target(raw[:-3]));self.assertIsNone(app_execution_target(b'invalid'))
        with patch('runtime_discovery.read_alias_target',return_value=str(self.exe)):
            self.assertEqual(resolve_runtime(self.root/'WindowsApps/llama.exe'),self.exe)

    def test_wrong_executable_is_not_new_llama_runtime(self):
        with self.assertRaises(ProbeError):resolve_runtime(self.root/'llama-server.exe')

    def check(self,signature=VALID,path=None,probe=None):
        from unittest.mock import Mock
        runner=probe or Mock(return_value=CAPS)
        with patch('runtime_trust.signature',return_value=signature):row=validate(candidate(str(path or self.exe)),runner)
        return row,runner

    def test_valid_signature_cli_version_and_no_model_are_independent(self):
        row,_=self.check();self.assertTrue(row['verified']);self.assertEqual(row['state'],'verified')
        self.assertFalse(row['selected']);self.assertEqual(row['probes'][0]['exit_code'],0)
        self.assertFalse(row['trust']['inference_success']);self.assertFalse((self.root/'models').exists())

    def test_unsigned_invalid_and_wrong_publisher_never_execute(self):
        for auth in ({'status':'NotSigned'},{'status':'HashMismatch','signer':VALID['signer']},
                {'status':'Valid','signer':'CN=Other, O=Other'},{'status':'Valid','signer':'CN=Hugging Face Imposter, O=Hugging Face Imposter'}):
            with self.subTest(auth=auth):
                row,runner=self.check(auth);self.assertFalse(row['verified']);self.assertEqual(row['reason']['code'],'RUNTIME_SIGNATURE');runner.assert_not_called()

    def test_missing_file_reports_resolve_failure(self):
        row,runner=self.check(path=self.root/'missing/llama.exe');self.assertEqual(row['state'],'failed')
        self.assertEqual(row['reason']['code'],'FILE_NOT_FOUND');runner.assert_not_called()

    def test_timeout_and_unsupported_cli_return_diagnostic_records(self):
        from unittest.mock import Mock
        for code,state in [('PROBE_TIMEOUT','failed'),('RUNTIME_CAPABILITY','unsupported')]:
            row,_=self.check(probe=Mock(side_effect=ProbeError(code,'controlled rejection',{'probes':[{'exit_code':None,'timeout':True}]})))
            self.assertEqual(row['state'],state);self.assertEqual(row['reason']['code'],code);self.assertTrue(row['probes'])

    def test_cli_exit_code_is_preserved(self):
        with patch('llama_app_engine.run_probe',return_value=('controlled exit',{'exit_code':7,'argv':['llama.exe','version']})):
            with self.assertRaises(ProbeError) as caught:engine_profile(self.exe,refresh=True)
        self.assertEqual(caught.exception.record['probes'][0]['exit_code'],7)

    def test_verified_not_selected_scan_then_saved_selection_and_reload(self):
        manager=RuntimeManager(self.root,lambda:None)
        found={'found':[{'input_path':str(self.exe),'sources':['user_path']}],'searched':1,'attempts':[],'errors':[]}
        with patch('runtime_manager.inventory',return_value=found),patch('runtime_trust.signature',return_value=VALID),patch('runtime_manager.engine_profile',return_value=CAPS):
            manager.start_discovery();manager.discovery_thread.join(3)
            self.assertEqual(manager.status()['candidates'][0]['state'],'verified')
            self.assertEqual(manager.record['kind'],'legacy')
            manager.select({'kind':'llama-app','path':str(self.exe),'confirmed':True})
            self.assertEqual(manager.status()['candidates'][0]['state'],'selected')
        restored=RuntimeManager(self.root,lambda:None)
        self.assertEqual(restored.record['path'],str(self.exe));self.assertEqual(restored.executable(),self.exe)
        self.assertEqual(restored.factory().__class__.__name__,'LlamaAppEngine')

    def test_real_probe_timeout_cleans_its_owned_process(self):
        with self.assertRaises(ProbeError) as caught:
            run_probe([sys.executable,'-I','-S','-c','import time;time.sleep(30)'],timeout=.1)
        self.assertEqual(caught.exception.code,'PROBE_TIMEOUT')
        self.assertEqual(caught.exception.record['cleanup'],'owned process tree closed')

    def test_file_picker_cancellation_and_failure_do_not_select(self):
        from runtime_file_picker import pick_existing
        with patch('runtime_file_picker.run_probe',return_value=('{}',{'exit_code':1})):
            with self.assertRaises(ProbeError):pick_existing()
        with patch('runtime_file_picker.run_probe',return_value=('{"path":null}',{'exit_code':0})):
            self.assertIsNone(pick_existing())

    def test_core_selection_no_model_prompt_and_same_factory_for_consumers(self):
        from workspace_core import WorkspaceApplication
        app=WorkspaceApplication(self.root,web=True)
        try:
            with patch('runtime_trust.signature',return_value=VALID),patch('runtime_manager.signature',return_value=VALID),patch('runtime_manager.engine_profile',return_value=CAPS):
                reply=app.response('runtime-select',{'kind':'llama-app','path':str(self.exe),'confirmed':True});self.assertTrue(reply['ok'])
                self.assertEqual(app.service.engine(),self.exe)
                self.assertEqual(app.service.device_execution.new_local().__class__.__name__,'LlamaAppEngine')
                self.assertTrue(app.service.host_engine()['installed'])
                self.assertFalse(list(app.service.models.glob('*.gguf')))
                result=app.response('run',{'action':'engine-start','model':'missing.gguf','context':2048,'mode':'cpu'})
                if result['ok']:
                    import time
                    for _ in range(100):
                        job=app.service.scheduler.snapshot(result['value']['id'])
                        if job['state'] not in ('running','queued'):break
                        time.sleep(.01)
                    self.assertEqual(job['state'],'failed');self.assertIn('模型',job['message'])
                self.assertEqual(app.service.runtime_manager.record['kind'],'llama-app')
                from types import SimpleNamespace
                with patch.object(app.service.local,'running',return_value=False):
                    app.service.device_execution.scopes['controlled']=SimpleNamespace(local=SimpleNamespace(running=lambda:True))
                    self.assertTrue(app.service.runtime_running())
                    app.service.device_execution.scopes.clear()
        finally:app.close()


if __name__=='__main__':unittest.main()

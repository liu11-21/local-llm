import json
from pathlib import Path
import tempfile
from threading import Event,Thread
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import unittest
from unittest.mock import Mock,patch
from llama_app_engine import LlamaAppEngine
from runtime_manager import RuntimeManager,MANIFEST
from runtime_trust import RuntimeTrust,sha256,BASELINE_SHA256


class RuntimeTests(unittest.TestCase):
    def test_dispatcher_security_flags_and_huggingface_source(self):
        engine=LlamaAppEngine()
        with patch('llama_app_engine.engine_profile',return_value={'help':'--no-agent --no-webui --no-cors-credentials'}):
            args=engine.command(Path('llama.exe'),['--model','hf://unsloth/Qwen3-4B-GGUF:Q4_0','--host','127.0.0.1'])
        self.assertEqual(args[1:4],['serve','-hf','unsloth/Qwen3-4B-GGUF:Q4_0'])
        self.assertIn('--cors-origins',args);self.assertIn('localhost',args);self.assertIn('--no-agent',args)
        self.assertEqual(engine.request_options(False,512),{})
        engine.supports_thinking=True
        self.assertEqual(engine.request_options(False,512)['reasoning_effort'],'none')
        for invalid in ['hf://owner/repo;command','hf://owner/repo:Q4 --host 0.0.0.0']:
            with self.assertRaises(ValueError):engine.resolve_model(invalid)

    def test_thinking_only_for_supported_template_and_bounded_budget(self):
        engine=LlamaAppEngine()
        self.assertEqual(engine.request_options(False,512),{})
        with self.assertRaises(ValueError):engine.request_options(True,512)
        engine.supports_thinking=True
        self.assertEqual(engine.request_options(True,512)['reasoning_budget_tokens'],170)

    def test_signature_does_not_imply_origin_hash_launch_or_sac(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'llama.exe';path.write_bytes(b'not executed')
            with patch('runtime_trust.signature',return_value={'status':'Valid','signer':'Hugging Face'}):
                report=RuntimeTrust().inspect(path)
            self.assertFalse(report['source_confirmed']);self.assertFalse(report['sha256_verified'])
            self.assertFalse(report['launch_success']);self.assertFalse(report['inference_success'])
            self.assertIn('NOT VERIFIED',report['sac']);self.assertEqual(len(BASELINE_SHA256),64)

    def test_selection_rejects_bad_signature_before_execution_and_preserves_old_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'llama.exe';exe.write_bytes(b'not executed')
            manager=RuntimeManager(root,lambda:root/'llama-server.exe')
            with patch('runtime_trust.signature',return_value={'status':'NotSigned'}),patch('runtime_manager.engine_profile') as probe:
                with self.assertRaises(ValueError):manager.select({'kind':'llama-app','path':str(exe),'confirmed':True})
                probe.assert_not_called()
            self.assertEqual(manager.record['kind'],'legacy');self.assertFalse(manager.file.exists())

    def test_switch_and_content_pin_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'llama.exe';exe.write_bytes(b'not executed')
            manager=RuntimeManager(root,lambda:root/'llama-server.exe')
            with patch('runtime_trust.signature',return_value={'status':'Valid','signer':'CN=Hugging Face'}),patch('runtime_manager.engine_profile',return_value={'version':'build 12360'}):
                manager.select({'kind':'llama-app','path':str(exe),'confirmed':True})
            restored=RuntimeManager(root,lambda:None);self.assertEqual(restored.executable(),exe)
            exe.write_bytes(b'changed')
            with self.assertRaises(ValueError):restored.executable()
            restored.select({'kind':'legacy','confirmed':True});self.assertIsNone(restored.executable())

    def test_error_redaction_preserves_useful_diagnosis(self):
        engine=LlamaAppEngine();engine.key='secret-123';engine.model=Path('C:/private/model.gguf')
        result=engine.safe_error({'message':'controlled reviewer failure secret-123 C:/private/model.gguf Bearer abc'})
        self.assertIn('controlled reviewer failure',result)
        for secret in ('secret-123','C:/private/model.gguf','Bearer abc'):self.assertNotIn(secret,result)

    def test_installer_conflict_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'runtimes'/MANIFEST['id'];target.mkdir(parents=True)
            path=target/'llama.exe';path.write_bytes(b'preserve')
            manager=RuntimeManager(root,lambda:None)
            with patch.dict('sys.modules',{'zstandard':Mock()}),patch('runtime_manager.os.name','nt'):
                with self.assertRaises(ValueError):manager.install(Event(),lambda **_:None)
            self.assertEqual(path.read_bytes(),b'preserve')


class ModelManagementTests(unittest.TestCase):
    def test_gguf_metadata_and_confirmed_delete_preserve_history(self):
        import struct
        from desktop_worker import Desktop
        from gguf_metadata import metadata
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);app=Desktop(root)
            try:
                app.models.mkdir(exist_ok=True);model=app.models/'fixture.gguf'
                text=lambda v:struct.pack('<Q',len(v))+v
                model.write_bytes(b'GGUF'+struct.pack('<IQQ',3,0,2)+text(b'general.architecture')+struct.pack('<I',8)+text(b'qwen3')+text(b'qwen3.context_length')+struct.pack('<II',4,8192))
                self.assertEqual(metadata(model)['context_length'],8192)
                with app.connect() as db:
                    db.execute('INSERT INTO chats(id,title) VALUES(?,?)',('a'*32,'preserve'))
                    db.execute('INSERT INTO messages VALUES(?,?,?)',('a'*32,'assistant','keep answer'))
                with self.assertRaises(ValueError):app.rpc('model-remove',{'model':model.name})
                self.assertTrue(model.exists())
                with patch.object(app.local,'running',return_value=True):
                    with self.assertRaises(ValueError):app.rpc('model-remove',{'model':model.name,'confirmed':True})
                result=app.rpc('model-remove',{'model':model.name,'confirmed':True})
                self.assertGreater(result['freed_bytes'],0);self.assertFalse(model.exists())
                self.assertEqual(app.history('a'*32)[0]['content'],'keep answer')
            finally:app.close()

    def test_3077_diagnostic_identifies_named_file_without_claiming_sac(self):
        from runtime_trust import launch_diagnostic
        with patch('runtime_trust.code_integrity',return_value={'events':[{'files':['C:/runtime/llama.exe','C:/runtime/blocked.dll']}]}):
            result=launch_diagnostic(OSError('blocked'),Path('C:/runtime/llama.exe'))
        self.assertEqual(result['code'],'CODE_INTEGRITY_3077');self.assertIn('C:/runtime/blocked.dll',result['blocking_files'])


class StreamingTests(unittest.TestCase):
    def test_real_loopback_sse_separates_thinking_and_reports_usage_and_empty_failure(self):
        requests=[];outputs=[True,False]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_POST(self):
                requests.append((self.headers.get('Authorization'),json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                events=[{'choices':[{'delta':{'reasoning_content':'private thought'}}]}]
                if outputs.pop(0):events.append({'choices':[{'delta':{'content':'final answer'},'finish_reason':'stop'}]})
                events.append({'choices':[],'usage':{'completion_tokens':8},'timings':{'predicted_per_second':12}})
                for event in events:self.wfile.write(('data: '+json.dumps(event)+'\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        engine=LlamaAppEngine();engine.process=Mock();engine.process.poll.return_value=None;engine.port=server.server_port;engine.key='test-secret';engine.supports_thinking=True
        try:
            self.assertEqual(''.join(engine.stream([{'role':'user','content':'Hi'}])),'final answer')
            self.assertEqual(engine.last_generation['reasoning'],'private thought')
            self.assertEqual(engine.last_generation['usage']['completion_tokens'],8)
            self.assertEqual(requests[0][0],'Bearer test-secret');self.assertEqual(requests[0][1]['reasoning_effort'],'none')
            with self.assertRaisesRegex(RuntimeError,'EMPTY_ANSWER'):''.join(engine.stream([{'role':'user','content':'Hi'}]))
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()

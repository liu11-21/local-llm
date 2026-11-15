import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile
import os
import subprocess
import sys
import time
import ctypes as ct
from web_environment import verify_distribution,verify_environment
from web_update import update,rollback,selected


class DistributionTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows Job Object needs Windows')
    def test_abrupt_host_exit_terminates_inherited_python_child(self):
        root=Path(__file__).resolve().parent
        code=f'import sys,subprocess,time;sys.path.insert(0,{str(root)!r});from web_process_guard import enable;enable();p=subprocess.Popen([sys.executable,"-I","-S","-c","import time;time.sleep(60)"]);print(p.pid,flush=True);time.sleep(60)'
        parent=subprocess.Popen([sys.executable,'-I','-S','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        handle=None;kernel=ct.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ct.c_uint32,ct.c_int,ct.c_uint32];kernel.OpenProcess.restype=ct.c_void_p
        kernel.WaitForSingleObject.argtypes=[ct.c_void_p,ct.c_uint32];kernel.CloseHandle.argtypes=[ct.c_void_p]
        try:
            line=parent.stdout.readline().strip()
            self.assertTrue(line.isdigit(),'Job-protected child did not start: '+parent.stderr.read() if not line else line)
            handle=kernel.OpenProcess(0x100000,False,int(line));self.assertTrue(handle)
            parent.kill();parent.wait(10)
            self.assertEqual(kernel.WaitForSingleObject(handle,10000),0,'Inherited child survived the host process')
        finally:
            if handle:kernel.CloseHandle(handle)
            if parent.poll() is None:parent.kill();parent.wait(10)
            parent.stdout.close();parent.stderr.close()

    def test_manifest_tamper_and_environment_extra_code_fail_closed(self):
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'module.py').write_bytes(b'original')
            (root/'WEB_MANIFEST.json').write_text(json.dumps({'files':{'module.py':hashlib.sha256(b'original').hexdigest()},'commit':'fixture'}))
            self.assertEqual(verify_distribution(root)['files'],1)
            (root/'module.py').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify_distribution(root)
            site=root/'Lib/site-packages';site.mkdir(parents=True)
            (root/'web-environment.json').write_text(json.dumps({'files':{}}))
            verify_environment(root);(site/'shadow.py').write_bytes(b'extra')
            with self.assertRaises(ValueError):verify_environment(root)

    def test_update_rejects_bad_digest_and_zip_slip(self):
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();archive=root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as out:out.writestr('../outside.txt','unsafe')
            with self.assertRaisesRegex(ValueError,'SHA-256'):update(root,archive,'0'*64)
            with self.assertRaises(ValueError):update(root,archive,hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertFalse((root.parent/'outside.txt').exists())

    def test_side_by_side_update_and_rollback_preserve_user_data(self):
        with TemporaryDirectory() as folder:
            root=Path(folder).resolve();(root/'user-model-marker').write_bytes(b'keep')
            archive=root/'candidate.zip';source=b'# controlled updater fixture, not executed\n'
            manifest={'version':'0.9.0','commit':'controlled fixture','files':{'web_launcher.py':hashlib.sha256(source).hexdigest()}}
            with zipfile.ZipFile(archive,'w') as out:
                out.writestr('LocalLLM-Web-0.9.0/app/web_launcher.py',source)
                out.writestr('LocalLLM-Web-0.9.0/app/WEB_MANIFEST.json',json.dumps(manifest))
            update(root,archive,hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertNotEqual(selected(root),root);self.assertEqual((root/'user-model-marker').read_bytes(),b'keep')
            rollback(root);self.assertEqual(selected(root),root)
            self.assertEqual((root/'user-model-marker').read_bytes(),b'keep')


if __name__=='__main__':unittest.main()

from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


class WorkerLockTests(unittest.TestCase):
    def test_second_worker_cannot_reset_live_tasks_and_lock_releases_on_exit(self):
        with TemporaryDirectory() as folder:
            command=[sys.executable,str(Path(__file__).with_name('desktop_worker.py')),'--data',folder]
            first=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            request=b'{"op":"colab","data":{}}\n'
            try:
                first.stdin.write(request);first.stdin.flush()
                self.assertTrue(json.loads(first.stdout.readline())['ok'])
                blocked=subprocess.run(command,input=request,capture_output=True,timeout=15,check=True)
                reply=json.loads(blocked.stdout)
                self.assertFalse(reply['ok'])
                self.assertIn('已有執行中的工作台',reply['error'])
                first.stdin.write(request);first.stdin.flush()
                self.assertTrue(json.loads(first.stdout.readline())['ok'])
            finally:
                first.stdin.close()
                first.wait(timeout=15)
                first.stdout.close();first.stderr.close()
            recovered=subprocess.run(command,input=request,capture_output=True,timeout=15,check=True)
            self.assertTrue(json.loads(recovered.stdout)['ok'])


if __name__=='__main__':unittest.main()

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest

from desktop_worker import Desktop
from device_execution import DispatchTarget
from device_resources import ResourceDemand


class DeviceExecutionTests(unittest.TestCase):
    def test_queued_model_change_is_rejected_before_starting_an_engine(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder))
            app.models.mkdir(exist_ok=True)
            path=app.models/'model.gguf'
            path.write_bytes(b'changed after confirmation')
            target=DispatchTarget('local','CPU',path.name,'llama.cpp',ResourceDemand(),1,1024**3,
                                  (('gguf',sha256(b'previously confirmed weights').hexdigest()),))
            try:
                with self.assertRaisesRegex(ValueError,'MODEL_CHANGED'):
                    with app.device_execution.scope(target,'controlled',Event()):self.fail('must not start')
                self.assertEqual(app.device_execution.scopes,{})
                self.assertFalse(app.local.running())
            finally:app.close()


if __name__=='__main__':unittest.main()

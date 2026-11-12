from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import patch
from desktop_worker import Desktop
from remote_media import descriptor,media_input
from remote_host import digest,ProtocolError


class RemoteRetentionTests(TestCase):
    def test_expiry_removes_only_registered_host_results_and_preserves_job_and_client_work(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder));host=app.remote_host
            app.remote_output.mkdir();path=app.remote_output/'a12345678901.webm'
            copyfile(Path(__file__).parent/'desktop/tests/media-fixtures/sample.webm',path)
            unrelated=app.remote_output/'unrelated.txt';unrelated.write_text('keep')
            app.outputs.mkdir();work=app.outputs/path.name;copyfile(path,work)
            artifact=descriptor(path,'wan21',{},'2020-01-01T00:00:00+00:00',Event(),owner='a'*32,host='b'*32,job='c'*32)
            try:
                host.records.writer('a'*32,'c'*32,b'signature','video','Wan','wan21')({'id':'task','state':'completed','created':'2020-01-01T00:00:00+00:00',
                    'finished':'2020-01-01T00:00:00+00:00','message':'completed','result':{'artifact':artifact}})
                with app.connect() as db:
                    host.cleanup_media(db)
                    saved=host.records.get(db,'a'*32,'c'*32)
                self.assertEqual(saved['state'],'completed');self.assertNotIn('artifact',saved)
                self.assertFalse(path.exists());self.assertTrue(work.exists());self.assertTrue(unrelated.exists())
            finally:app.close()

    def test_queued_media_reserves_host_storage_before_any_generation(self):
        with TemporaryDirectory() as folder:
            app=Desktop(Path(folder));host=app.remote_host
            host.id,host.state='b'*32,'ready'
            host.media=lambda:{'video':{'state':'ready','workflows':['wan21']}}
            with app.connect() as db:db.execute('INSERT INTO remote_host_grants VALUES(?,?,?)',('a'*32,'fixture',digest('x')))
            payload=media_input({'kind':'video','workflow':'wan21','prompt':'controlled'})
            try:
                with patch.object(host.scheduler,'_dispatch'),patch('remote_host.HOST_QUOTA',2*1024**3):
                    host.submit('a'*32,{'request':'c'*32,**payload})
                    with self.assertRaises(ProtocolError) as failure:host.submit('a'*32,{'request':'d'*32,**payload})
                    self.assertEqual(failure.exception.status,507)
            finally:
                for _,timer in host.jobs.values():timer.cancel()
                app.close()

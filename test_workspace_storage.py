from contextlib import closing
import hashlib
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from desktop_worker import Desktop
from workspace_storage import DATABASE, Upgrade, snapshot


class UpgradeTests(unittest.TestCase):
    def legacy(self,root):
        path=root/'desktop.sqlite3'
        with closing(sqlite3.connect(path)) as db,db:
            db.executescript('PRAGMA user_version=8; CREATE TABLE chats(id TEXT PRIMARY KEY,title TEXT,touched TEXT DEFAULT CURRENT_TIMESTAMP); CREATE TABLE messages(chat TEXT,role TEXT,text TEXT);')
            db.execute('INSERT INTO chats(id,title) VALUES(?,?)',('a'*32,'old chat'))
            db.execute('INSERT INTO messages VALUES(?,?,?)',('a'*32,'user','keep original'))
        return path

    def test_legacy_is_backed_up_and_adopted_without_modification(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);old=self.legacy(root);digest=hashlib.sha256(old.read_bytes()).hexdigest()
            app=Desktop(root)
            try:
                status=app.rpc('storage-status',{});self.assertEqual(status['integrity'],'PASS')
                self.assertEqual(app.history('a'*32)[0]['content'],'keep original')
                backup=Path(status['backup']);self.assertTrue(backup.is_file())
                self.assertEqual(hashlib.sha256(backup.read_bytes()).hexdigest(),status['backup_sha256'])
            finally:app.close()
            self.assertEqual(hashlib.sha256(old.read_bytes()).hexdigest(),digest)
            self.assertEqual(len(list((root/'backups').glob('*.sqlite3'))),1)
            second=Desktop(root);second.close()
            self.assertEqual(len(list((root/'backups').glob('*.sqlite3'))),1)
            with closing(sqlite3.connect(old)) as db,db:db.execute('UPDATE chats SET title="old program writes only old database"')
            third=Desktop(root)
            try:self.assertEqual(third.rpc('chats',{})[0][1],'old chat')
            finally:third.close()

    def test_future_schema_and_reader_refuse_writes_and_corrupt_source_is_preserved(self):
        for kind in ('schema','reader','corrupt'):
            with self.subTest(kind=kind),TemporaryDirectory() as folder:
                root=Path(folder);path=root/DATABASE
                if kind=='corrupt':path.write_bytes(b'not a database')
                else:
                    with closing(sqlite3.connect(path)) as db,db:
                        db.execute('PRAGMA user_version='+('999' if kind=='schema' else '14'))
                        if kind=='reader':
                            db.executescript("CREATE TABLE workspace_storage(id INTEGER PRIMARY KEY,version TEXT,minimum_reader TEXT); INSERT INTO workspace_storage VALUES(1,'9.0.0','9.0.0');")
                before=path.read_bytes()
                with self.assertRaisesRegex(ValueError,'保留|較新'):Desktop(root)
                self.assertEqual(path.read_bytes(),before)

    def test_failed_migration_preserves_partial_files_and_restores_verified_snapshot(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);old=self.legacy(root)
            with patch('desktop_worker.ClientMedia.initialize',side_effect=RuntimeError('injected migration failure')):
                with self.assertRaisesRegex(ValueError,'升級'):Desktop(root)
            self.assertTrue(list((root/'backups').glob('failed-upgrade-*')))
            with closing(sqlite3.connect(root/DATABASE)) as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],8)
                self.assertEqual(db.execute('SELECT text FROM messages').fetchone()[0],'keep original')
            recovered=Desktop(root);recovered.close()
            self.assertTrue(old.exists())

    def test_readonly_snapshot_includes_wal_and_disk_shortage_never_replaces_source(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);old=self.legacy(root)
            with closing(sqlite3.connect(old)) as db,db:
                db.execute('PRAGMA journal_mode=WAL');db.execute("INSERT INTO messages VALUES('wal','user','uncheckpointed')");db.commit()
                backup=root/'wal-backup.sqlite3';snapshot(old,backup)
                with closing(sqlite3.connect(backup)) as copied:self.assertEqual(copied.execute('SELECT count(*) FROM messages').fetchone()[0],2)
            with patch('workspace_storage.shutil.disk_usage',return_value=shutil._ntuple_diskusage(1,1,0)):
                with self.assertRaisesRegex(ValueError,'空間'):Desktop(root)
            self.assertFalse((root/DATABASE).exists())

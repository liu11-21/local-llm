"""Verified SQLite snapshots and forward-only Workspace database adoption."""
from contextlib import closing
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from uuid import uuid4
from download_recovery import exclusive, owned
from workspace_version import VERSION

DATABASE = 'workspace.sqlite3'
MAX_SCHEMA = 14


def reader(path):
    return closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=5))


def integrity(db):
    if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('資料庫完整性檢查失敗，原始資料未被覆蓋。請保留資料與備份後進行恢復。')


def compatible(db):
    schema=db.execute('PRAGMA user_version').fetchone()[0]
    if schema>MAX_SCHEMA:
        raise ValueError('資料庫由較新版本建立，本版拒絕寫入。請使用相容的新版本，勿直接降級。')
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='workspace_storage'").fetchone():
        row=db.execute('SELECT minimum_reader FROM workspace_storage WHERE id=1').fetchone()
        if row:
            try: minimum=tuple(int(part) for part in row[0].split('.'))
            except (ValueError,AttributeError):raise ValueError('資料庫相容性標記無法辨識，請保留資料並恢復備份。') from None
            if minimum>tuple(map(int,VERSION.split('.'))):
                raise ValueError('資料庫要求較新程式，本版拒絕寫入。請使用相容的新版本。')
    return schema


def snapshot(source,target):
    if not owned(source) or not owned(target) or target.exists():
        raise ValueError('資料庫備份路徑不安全，未覆蓋原始資料。')
    with reader(source) as original:
        integrity(original);compatible(original)
        with closing(sqlite3.connect(target)) as backup:
            original.backup(backup);integrity(backup)
            backup.execute('PRAGMA journal_mode=DELETE')
    with target.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


class Upgrade:
    def __init__(self,data):
        self.data=data;self.path=data/DATABASE;self.backup=None;self.created=not self.path.exists()
        self.report={'version':VERSION,'database':DATABASE,'status':'unchanged','backup':None}

    def prepare(self):
        legacy=self.data/'desktop.sqlite3'
        source=self.path if self.path.exists() else legacy if legacy.exists() else None
        for path in (self.data,self.path,legacy,self.data/'backups'):
            if not owned(path):raise ValueError('資料庫或備份目錄不安全，請保留原始資料並修正路徑。')
        if source is None:return
        with reader(source) as db:
            schema=compatible(db);integrity(db)
            table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='workspace_storage'").fetchone()
            previous=db.execute('SELECT version FROM workspace_storage WHERE id=1').fetchone() if table else None
        if source==self.path and previous and previous[0]==VERSION:return
        required=source.stat().st_size+(source.with_name(source.name+'-wal').stat().st_size if source.with_name(source.name+'-wal').exists() else 0)
        if shutil.disk_usage(self.data).free<required*3+256*1024**2:
            raise ValueError('升級備份所需磁碟空間不足。請保留原資料，釋出空間後重新啟動。')
        backups=self.data/'backups';backups.mkdir(exist_ok=True)
        name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:12]
        self.backup=backups/f'workspace-pre-{VERSION.replace(".","")}-{name}.sqlite3'
        digest=snapshot(source,self.backup)
        self.report.update(status='adopted-legacy' if source==legacy else 'upgraded',backup=str(self.backup),
                           backup_sha256=digest,source=source.name,source_schema=schema)
        self.backup.with_suffix('.json').write_text(json.dumps(self.report,indent=2)+'\n',encoding='utf-8')
        if source==legacy:
            staging=self.data/f'.upgrade-{uuid4().hex}.sqlite3'
            shutil.copyfile(self.backup,staging)
            os.replace(staging,self.path)

    def finish(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            integrity(db);compatible(db)
            db.execute('CREATE TABLE IF NOT EXISTS workspace_storage(id INTEGER PRIMARY KEY CHECK(id=1), version TEXT NOT NULL, minimum_reader TEXT NOT NULL)')
            db.execute('INSERT OR REPLACE INTO workspace_storage VALUES(1,?,?)',(VERSION,VERSION))
        self.report['integrity']='PASS'

    def failed(self):
        # Preserve all partial files, then restore a verified snapshot only for this adopted DB.
        if not self.path.exists():return
        if not self.backup and not self.created:return
        directory=self.data/'backups'/('failed-upgrade-'+uuid4().hex)
        directory.mkdir(parents=True)
        for suffix in ('','-wal','-shm'):
            source=self.path.with_name(self.path.name+suffix)
            if source.exists() and owned(source):os.replace(source,directory/source.name)
        if self.backup:
            shutil.copyfile(self.backup,self.path)
        self.report.update(status='failed-restored' if self.backup else 'failed-preserved',failed_files=str(directory))


def protected_initialization(initialize):
    @wraps(initialize)
    def wrapped(self,data):
        directory=Path(data).resolve();directory.mkdir(parents=True,exist_ok=True)
        with exclusive(directory/'.storage-upgrade.lock'):
            upgrade=Upgrade(directory)
            try:
                upgrade.prepare()
                initialize(self,directory)
                upgrade.finish()
                self.storage_status=upgrade.report
            except Exception as error:
                # Initializers can fail part-way through. Close only components already constructed.
                for name,method in [('comfy_resources','close'),('scheduler','close'),('device_execution','close'),
                    ('openvino','close'),('hardware_monitor','close'),('remote_host','stop'),('agent_tools','close'),('local','stop'),('comfy','stop')]:
                    component=getattr(self,name,None)
                    if component:
                        try:getattr(component,method)()
                        except Exception:pass
                upgrade.failed()
                raise ValueError(f'Workspace 資料升級或開啟失敗：{error} 請保留原資料與 backups；不要刪除資料夾或覆蓋唯一備份。') from error
    return wrapped

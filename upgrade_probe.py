"""Synthetic data preservation probe for clean-runner installer upgrade acceptance."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from workspace_version import VERSION

TABLES=('chats','messages','agent_reports','agent_plans','team_configs','team_runs','settings','model_sources',
        'media_weight_verification','benchmark_sessions','benchmark_runs','benchmark_measurements',
        'remote_host_identity','remote_host_grants','remote_client_hosts','remote_client_secrets','remote_tls','creations')


def database_ready(path, version=VERSION):
    if not path.is_file():return False
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.1)) as db:
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(TABLES+('dispatch_runs','recommendation_receipts','engine_runs'))<=tables:return False
            if path.name=='workspace.sqlite3':
                return 'workspace_storage' in tables and db.execute('SELECT version FROM workspace_storage WHERE id=1').fetchone()==(version,)
            return True
    except sqlite3.Error:return False


def initialize_worker(worker,data,version):
    result=subprocess.run([str(worker.resolve()),'--data',str(data.resolve())],
        input='{"op":"update-status","data":{}}\n',text=True,encoding='utf-8',capture_output=True,timeout=60,check=True)
    reply=json.loads(result.stdout)
    if not reply.get('ok') or reply['value'].get('version')!=version:
        raise ValueError('Installed baseline Worker version mismatch')
    database=data/'workspace.sqlite3' if (data/'workspace.sqlite3').exists() else data/'desktop.sqlite3'
    if not database_ready(database,version):
        raise ValueError('Installed baseline Worker did not finish database initialization')
    return {'status':'PASS','worker_version':version,'database_ready':True}


def fingerprint(path):
    result={}
    with closing(sqlite3.connect(path)) as db:
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise ValueError('corrupt upgrade fixture')
        for table in TABLES:
            rows=db.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            encoded=json.dumps(rows,sort_keys=True,default=lambda value:{'blob_sha256':hashlib.sha256(value).hexdigest()})
            result[table]={'rows':len(rows),'sha256':hashlib.sha256(encoded.encode()).hexdigest()}
    return result


def seed(data):
    from remote_client import protect
    path=data/'workspace.sqlite3' if (data/'workspace.sqlite3').exists() else data/'desktop.sqlite3';identity='a'*32
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('INSERT INTO chats(id,title) VALUES(?,?)',(identity,'Upgrade compatibility fixture'))
        db.execute('INSERT INTO messages VALUES(?,?,?)',(identity,'user','Synthetic migration prompt'))
        db.execute('INSERT INTO messages VALUES(?,?,?)',(identity,'assistant','Preserve this old answer'))
        db.execute('INSERT INTO agent_reports(id,role,model,prompt,answer,steps) VALUES(?,?,?,?,?,?)',(identity,'general','fixture.gguf','test','saved answer','[]'))
        for table in ('agent_plans','team_runs'):
            db.execute(f'INSERT INTO {table} VALUES(?,?,?)',(identity,1,json.dumps({'id':identity,'state':'completed','nodes':[]})))
        db.execute('INSERT INTO team_configs VALUES(?,?)',(identity,json.dumps({'id':identity,'name':'saved team'})))
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('theme','light'))
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('device_memory_mib','0'))
        db.execute('INSERT INTO model_sources VALUES(?,?)',('fixture.gguf',json.dumps({'verification':'unknown','source':'synthetic-upgrade-fixture'})))
        db.execute('INSERT INTO media_weight_verification VALUES(?,?)',('fixture-weight',json.dumps({'status':'detected'})))
        db.execute('INSERT INTO benchmark_sessions(id,schema,model,engine,state,created,config) VALUES(?,?,?,?,?,?,?)',
            (identity,1,'synthetic-migration-only','fixture','completed','2000-01-01T00:00:00Z','{}'))
        db.execute('INSERT INTO benchmark_runs(id,session,device,state,environment) VALUES(?,?,?,?,?)',(identity,identity,'fixture','completed','{}'))
        db.execute('INSERT INTO benchmark_measurements VALUES(?,?,?,?,?)',(identity,0,'fixture','fixture','{}'))
        # A saved peer without an auth secret is intentionally unconnected, never contacted.
        db.execute('INSERT INTO remote_client_hosts VALUES(?,?,?,?,?)',(identity,'192.168.1.2',9443,'Saved offline host','migration-fixture'))
        protected=protect(b'synthetic-upgrade-token-not-a-real-credential')
        db.execute('INSERT INTO remote_client_secrets VALUES(?,?)',(identity,protected))
        db.execute('INSERT INTO remote_host_grants VALUES(?,?,?)',(identity,'migration-only',hashlib.sha256(b'synthetic-grant').hexdigest()))
        db.execute('INSERT INTO remote_tls VALUES(?,?,?,?,?,?)',(1,'192.168.1.2',b'synthetic-certificate',b'synthetic-encrypted-key',protected,0))
        db.execute('INSERT INTO creations VALUES(?,?)',('abcdefabcdef.png',json.dumps({'schema':1,'model':'fixture','prompt':'saved prompt','lyrics':'saved lyrics','options':{'seed':1}})))
    models=data/'models';models.mkdir(exist_ok=True);(models/'preserve.txt').write_text('user model marker',encoding='utf-8')
    outputs=data/'outputs';outputs.mkdir(exist_ok=True)
    (outputs/'abcdefabcdef.png').write_bytes((Path(__file__).parent/'desktop/tests/media-fixtures/sample.png').read_bytes())
    return {'source_database':path.name,'source_version':'0.7.0' if path.name=='workspace.sqlite3' else '0.6.2','legacy_present':(data/'desktop.sqlite3').exists(),'legacy_tables':fingerprint(data/'desktop.sqlite3') if (data/'desktop.sqlite3').exists() else None,'tables':fingerprint(path),'files':{str(file.relative_to(data)):hashlib.sha256(file.read_bytes()).hexdigest()
            for file in (models/'preserve.txt',outputs/'abcdefabcdef.png')},'fixture_only':True}


def verify(data,record):
    expected=json.loads(record.read_text(encoding='utf-8'))
    assert fingerprint(data/'workspace.sqlite3')==expected['tables'],'Migrated table contents changed'
    if expected.get('legacy_present',True):assert fingerprint(data/'desktop.sqlite3')==(expected.get('legacy_tables') or expected['tables']),'Original legacy database changed'
    assert all(hashlib.sha256((data/name).read_bytes()).hexdigest()==digest for name,digest in expected['files'].items())
    assert list((data/'backups').glob('workspace-pre-'+VERSION.replace('.','')+'-*.sqlite3')),'No pre-upgrade backup'
    return {'status':'PASS','legacy_workspace':expected.get('source_version','0.6.2'),'workspace':VERSION,'tables':expected['tables'],'files':expected['files'],
            'original_legacy_preserved':True,'backup_verified':True,'fixture_only':True}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('seed','verify','ready','initialize'))
    parser.add_argument('--data',type=Path,required=True);parser.add_argument('--record',type=Path)
    parser.add_argument('--database',type=Path);parser.add_argument('--worker',type=Path)
    parser.add_argument('--expected-version',default=None)
    parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.operation=='ready':
        if args.database is None:parser.error('--database is required')
        raise SystemExit(0 if database_ready(args.database,args.expected_version or VERSION) else 2)
    if args.operation=='initialize':
        if args.worker is None:parser.error('--worker is required')
        value=initialize_worker(args.worker,args.data,args.expected_version or '0.7.0')
    else:
        if args.record is None:parser.error('--record is required')
        value=seed(args.data) if args.operation=='seed' else verify(args.data,args.record)
    target=args.record if args.operation=='seed' else args.output
    if target:target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','operation':args.operation}))

"""Versioned paired media contract and one bounded atomic transfer path."""
from hashlib import sha256
import json
import os
import re
import shutil
import struct
import zlib
from datetime import datetime,timezone,timedelta
from time import monotonic,time

from download_recovery import exclusive, owned
from media import FORMATS, MODELS, WORKFLOWS, workflow_options
from registries import work_file,media_metadata
from task_manager import timestamp

IMAGE_WORKFLOWS = ("sd15", "sd15-preview")
REMOTE_IMAGE_LIMIT = 32 * 1024**2
MEDIA_SCHEMA=2
MEDIA_LIMITS={'image':REMOTE_IMAGE_LIMIT,'video':2*1024**3,'audio':512*1024**2}
MEDIA_TYPES={'image':('image','.png','image/png'),'video':('video','.webm','video/webm'),'audio':('music','.flac','audio/flac')}
MEDIA_WORKFLOWS={'image':IMAGE_WORKFLOWS,'video':('wan21',),'audio':('ace-step',)}
STAGING_QUOTA=4*1024**3
HOST_QUOTA=8*1024**3
DISK_RESERVE=256*1024**2
RETENTION_DAYS=7
CHUNK = 256 * 1024


class ClientMedia:
    """Keep private generation inputs on the submitting device across restarts."""

    def __init__(self, connect):
        self.connect = connect

    @staticmethod
    def initialize(db):
        db.execute("""CREATE TABLE IF NOT EXISTS client_media_jobs (
                   host TEXT NOT NULL, job TEXT NOT NULL, workflow TEXT NOT NULL, model TEXT NOT NULL,
                   prompt TEXT NOT NULL, options TEXT NOT NULL, submitted TEXT NOT NULL,
                   state TEXT NOT NULL, work TEXT, PRIMARY KEY(host,job))""")
        columns={row[1] for row in db.execute('PRAGMA table_info(client_media_jobs)')}
        for column,declaration in (('kind',"TEXT NOT NULL DEFAULT 'image'"),('lyrics',"TEXT NOT NULL DEFAULT ''"),
                                   ('updated','TEXT'),('download_status',"TEXT NOT NULL DEFAULT 'pending'")):
            if column not in columns:db.execute(f'ALTER TABLE client_media_jobs ADD COLUMN {column} {declaration}')
        if db.execute('PRAGMA user_version').fetchone()[0]<14:db.execute('PRAGMA user_version=14')
        if db.execute("PRAGMA user_version").fetchone()[0] < 9:
            db.execute("PRAGMA user_version=9")

    def submit(self, host, job, payload):
        with self.connect() as db:
            kind=payload.get('kind','image')
            app_kind=MEDIA_TYPES[kind][0]
            db.execute("""INSERT INTO client_media_jobs(host,job,workflow,model,prompt,options,submitted,state,work,kind,lyrics,updated)
                          VALUES(?,?,?,?,?,?,?,'submitted',NULL,?,?,?)""",
                       (host, job, payload["workflow"], MODELS[app_kind][1], payload["prompt"],
                        json.dumps(payload["options"]), timestamp(),kind,payload.get('lyrics',''),timestamp()))

    def get(self, host, job):
        with self.connect() as db:
            row = db.execute("""SELECT workflow,model,prompt,options,submitted,state,work,kind,lyrics,updated,download_status
                                FROM client_media_jobs WHERE host=? AND job=?""", (host,job)).fetchone()
        if row is None:
            return None
        value = dict(zip(("workflow","model","prompt","options","submitted","state","work","kind","lyrics","updated","download_status"),row))
        value["options"] = json.loads(value["options"])
        return value

    def complete(self, db, host, job, artifact, work):
        db.execute("""UPDATE client_media_jobs SET state='saved',download_status='verified',updated=?,options=?,work=? WHERE host=? AND job=?""",
                   (timestamp(),json.dumps(artifact["options"]),work,host,job))

    def downloads(self,host,job,state):
        with self.connect() as db:db.execute('UPDATE client_media_jobs SET download_status=?,updated=? WHERE host=? AND job=?',(state,timestamp(),host,job))

    def state(self,host,job,state):
        with self.connect() as db:db.execute('UPDATE client_media_jobs SET state=?,updated=? WHERE host=? AND job=?',(state,timestamp(),host,job))

    def available(self, host, job, artifact):
        with self.connect() as db:
            db.execute("""UPDATE client_media_jobs SET state='ready',options=?
                          WHERE host=? AND job=? AND state!='saved'""",
                       (json.dumps(artifact["options"]),host,job))


def image_input(data):
    if data.get('kind','image')!='image':raise ValueError('只允許圖片工作流程。')
    return media_input(data)


def media_input(data):
    if not isinstance(data,dict):raise ValueError('媒體輸入格式無效。')
    kind=data.get('kind','image')
    kind='audio' if kind=='music' else kind
    workflow, prompt = data.get("workflow"), data.get("prompt")
    if (set(data) - {"request","kind","workflow","prompt","options","lyrics","schema"} or kind not in MEDIA_TYPES
            or workflow not in MEDIA_WORKFLOWS[kind] or type(data.get('schema',2)) is not int or data.get('schema',2) not in (1,2)
            or data.get('schema')==1 and kind!='image'
            or not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000):
        raise ValueError("只允許受管理的媒體流程、版本及提示詞。")
    lyrics=data.get('lyrics','')
    if not isinstance(lyrics,str) or len(lyrics)>12000 or kind!='audio' and lyrics:raise ValueError('此流程不接受歌詞。')
    options=workflow_options(MEDIA_TYPES[kind][0],workflow,data.get('options'))
    if kind=='video' and options['width']*options['height']*options['frames']>16*1024**2:
        raise ValueError('影片解析度與影格總量超過主機安全上限。')
    result={"kind":kind,"workflow":workflow,"prompt":prompt.strip(),"options":options}
    if kind=='audio':result['lyrics']=lyrics
    return result


def checksum(path, cancel):
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(CHUNK):
            if cancel.is_set():
                raise InterruptedError("作品驗證已取消。")
            digest.update(block)
    return digest.hexdigest()


def validate_content(path,kind,*,strict=True):
    app_kind,suffix,_=MEDIA_TYPES[kind]
    if path.suffix not in (suffix,'.part'):raise ValueError('媒體副檔名不符。')
    with path.open('rb') as stream:header=stream.read(64)
    if not header.startswith(FORMATS[app_kind][1]):raise ValueError('媒體內容格式不符。')
    if kind=='image' and (len(header)<24 or header[12:16]!=b'IHDR' or not any(header[16:24])):
        raise ValueError('PNG 內容格式不符。')
    if kind=='image' and strict:
        with path.open('rb') as stream:
            stream.seek(8);seen=set()
            for _ in range(4096):
                chunk=stream.read(8)
                if len(chunk)!=8:raise ValueError('PNG 區塊不完整。')
                size,tag=struct.unpack('>I4s',chunk)
                if size>REMOTE_IMAGE_LIMIT:raise ValueError('PNG 區塊過大。')
                crc=zlib.crc32(tag);remaining=size
                while remaining:
                    block=stream.read(min(CHUNK,remaining))
                    if not block:raise ValueError('PNG 區塊不完整。')
                    crc=zlib.crc32(block,crc);remaining-=len(block)
                checksum_bytes=stream.read(4)
                if len(checksum_bytes)!=4 or int.from_bytes(checksum_bytes,'big')!=crc:raise ValueError('PNG CRC 不符。')
                seen.add(tag)
                if tag==b'IEND':
                    if not {b'IHDR',b'IDAT'}.issubset(seen) or stream.read(1):raise ValueError('PNG 結尾無效。')
                    break
            else:raise ValueError('PNG 區塊數過多。')
    # Metadata parsers are bounded. Staging files deliberately have no trusted suffix.
    if kind=='audio':
        if len(header)<42 or header[4]&127!=0 or header[5:8]!=b'\x00\x00\x22':raise ValueError('FLAC STREAMINFO 無效。')
        packed=int.from_bytes(header[18:26],'big')
        if not packed>>44 or not packed&(2**36-1):raise ValueError('FLAC 時長或取樣率無效。')
    if kind=='video':
        from registries import webm_metadata
        with path.open('rb') as stream:metadata=webm_metadata(stream,path.stat().st_size)
        if b'webm' not in header or not metadata.get('width') or not metadata.get('height'):
            raise ValueError('WebM 標頭或影像軌無效。')


def descriptor(path, workflow, options, created, cancel, *, owner=None,host=None,job=None):
    from media_install import MODELS_FOR_INSTALL
    app_kind=WORKFLOWS[workflow][0]
    kind='audio' if app_kind=='music' else app_kind
    size = path.stat().st_size
    if not 24 <= size <= MEDIA_LIMITS[kind]:raise ValueError('遠端媒體超出可傳輸的大小。')
    validate_content(path,kind)
    expires=(datetime.fromisoformat(created)+timedelta(days=RETENTION_DAYS)).isoformat()
    return {"schema":2,"id":path.name,"media_id":path.stem,"job_id":job,"owner_client_id":owner,'host_id':host,'runtime_id':host,
            "bytes":size,"sha256":checksum(path,cancel),"kind":kind,'mime':MEDIA_TYPES[kind][2],'extension':MEDIA_TYPES[kind][1],
            "model":MODELS[app_kind][1],"model_id":{'image':'sd15','video':'wan21','audio':'ace-step'}[kind],
            'model_version':MODELS_FOR_INSTALL[app_kind].version,'model_revision':MODELS_FOR_INSTALL[app_kind].revision,
            "workflow":workflow,"options":options,"created":created,
            'updated':created,'completed':created,'status':'completed','download_status':'available',
            'retention':{'days':RETENTION_DAYS,'expires':expires}}


def validate_artifact(value):
    if not isinstance(value,dict):raise ValueError('遠端作品資訊無效。')
    kind=value.get('kind')
    schema=value.get('schema',1)
    if kind not in MEDIA_TYPES or type(schema) is not int or schema not in (1,2) or schema==1 and kind!='image':raise ValueError('媒體契約版本無效。')
    app_kind,suffix,mime=MEDIA_TYPES[kind]
    if (not re.fullmatch(r"[a-f0-9]{12}"+re.escape(suffix), str(value.get("id","")))
            or not re.fullmatch(r"[a-f0-9]{64}", str(value.get("sha256","")))
            or type(value.get("bytes")) is not int or not 24 <= value["bytes"] <= MEDIA_LIMITS[kind]
            or value.get("workflow") not in MEDIA_WORKFLOWS[kind]
            or schema==2 and (value.get('mime')!=mime or value.get('extension')!=suffix)):
        raise ValueError("遠端作品資訊無效。")
    if schema==2:
        if any(not re.fullmatch('[a-f0-9]{32}',str(value.get(key,''))) for key in ('job_id','owner_client_id','host_id','runtime_id')):
            raise ValueError('媒體擁有者或來源識別無效。')
        if value.get('media_id')!=value['id'].split('.')[0] or value.get('status')!='completed':raise ValueError('媒體識別或完成狀態無效。')
    return {**value,'schema':schema,'mime':mime,'extension':suffix,'app_kind':app_kind,
        "model":MODELS[app_kind][1],"options":workflow_options(app_kind,value["workflow"],value.get("options"))}


def fetch_image(client, request, artifact, output, staging, cancel, update):
    staging.mkdir(parents=True,exist_ok=True)
    if not owned(staging):raise ValueError('作品下載目錄不安全。')
    # One quota transaction across hosts, no partial reservations or overcommit.
    with exclusive(staging/'.quota.lock'):
        keep=sha256(f'{client.id}:{request}'.encode()).hexdigest()[:32]
        for path in staging.glob('*.part'):
            if re.fullmatch(r'[a-f0-9]{32}-[a-f0-9]{24}\.part',path.name) and not path.name.startswith(keep) and owned(path) and path.is_file() and path.stat().st_nlink==1 and time()-path.stat().st_mtime>RETENTION_DAYS*86400:
                path.unlink()
        return _fetch_media(client,request,artifact,output,staging,cancel,update)


def _fetch_media(client, request, artifact, output, staging, cancel, update):
    artifact = validate_artifact(artifact)
    if artifact.get('schema')==2 and (artifact.get('host_id')!=client.id or artifact.get('job_id')!=request):
        raise ValueError('媒體來源主機或任務不符。')
    key = sha256(f"{client.id}:{request}".encode()).hexdigest()
    output.mkdir(parents=True,exist_ok=True)
    staging.mkdir(parents=True,exist_ok=True)
    if not owned(output) or not owned(staging):
        raise ValueError("作品下載目錄不安全。")
    target = output / (key[:12]+artifact['extension'])
    part = staging / f"{key[:32]}-{artifact['sha256'][:24]}.part"
    size, expected = artifact["bytes"], artifact["sha256"]
    with exclusive(staging / f"{key[:32]}.lock"):
        if target.exists():
            path = work_file(output,target.name)
            if path.stat().st_size == size and checksum(path,cancel) == expected:
                return path
            raise ValueError("本機同名作品與遠端結果不一致。")
        if not owned(part) or part.exists() and (not part.is_file() or part.stat().st_nlink != 1):
            raise ValueError("作品下載暫存檔不安全。")
        offset = part.stat().st_size if part.exists() else 0
        occupied=sum(item.stat().st_size for item in staging.glob('*.part') if item.is_file() and not item.is_symlink())
        if occupied+max(0,size-offset)>STAGING_QUOTA:raise OSError('遠端媒體暫存配額不足。請完成或取消既有下載後再試。')
        if shutil.disk_usage(staging).free<max(0,size-offset)+DISK_RESERVE:raise OSError('作品下載磁碟空間不足。')
        if offset > size:
            part.unlink()
            offset = 0
        if offset < size:
            headers = {"Range":f"bytes={offset}-"} if offset else {}
            with client.request("GET", f"/v1/jobs/{request}/artifact", headers=headers) as response:
                if (response.status != (206 if offset else 200) or response.getheader("ETag") != f'"{expected}"'
                        or response.getheader("Content-Length") != str(size-offset)
                        or offset and response.getheader("Content-Range") != f"bytes {offset}-{size-1}/{size}"):
                    raise ValueError("遠端作品長度或續傳範圍不符。")
                if response.getheader('Content-Type') not in ((artifact['mime'],) if artifact['schema']==2 else (None,artifact['mime'])):raise ValueError('遠端媒體 MIME 不符。')
                with part.open("ab") as stream:
                    while offset < size:
                        if cancel.is_set():
                            raise InterruptedError("已停止下載，稍後可續傳。")
                        data = response.read(min(CHUNK,size-offset))
                        if not data:
                            raise ConnectionError("作品傳輸中斷。請重新查詢任務並續傳。")
                        stream.write(data)
                        offset += len(data)
                        update(message="下載遠端作品…",received=offset,total=size)
        if checksum(part,cancel) != expected:
            part.unlink(missing_ok=True)
            raise ValueError("遠端圖片內容未通過 SHA-256 或 PNG 格式驗證。")
        try:validate_content(part,artifact['kind'],strict=artifact['schema']==2)
        except ValueError:
            part.unlink(missing_ok=True)
            raise
        if cancel.is_set():
            raise InterruptedError("已取消發布作品。")
        if os.name == "nt":
            part.rename(target)
        else:
            os.link(part,target)
            part.unlink()
        return target


def await_image(client, request, cancel, update):
    deadline = monotonic() + 7200
    while not cancel.wait(0.45) and monotonic() < deadline:
        job = client.job(request)
        if job["state"] == "completed":
            return validate_artifact(job.get("artifact"))
        if job["state"] not in ("queued","running"):
            raise RuntimeError(str(job.get("message") or "遠端圖片任務已中止。")[:300])
        update(message=job.get("message") or "等待遠端主機…")
    if cancel.is_set():
        try:
            client.json("POST",f"/v1/jobs/{request}/cancel")
        except (OSError,ValueError):
            pass
        raise InterruptedError("已取消遠端圖片任務。")
    raise TimeoutError(f"等待遠端圖片逾時。請以任務識別碼 {request} 查詢。")

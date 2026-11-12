"""Bounded derived PNG cache; originals load only for the selected work."""
import base64
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from download_recovery import owned
from registries import work_file
from remote_media import validate_content

LIMIT=16*1024**2
ITEM_LIMIT=96*1024


class MediaPreviews:
    def __init__(self,output):
        self.output,self.root,self.lock=output,output/'.previews',Lock()

    def target(self,name):
        source=work_file(self.output,name);stat=source.stat()
        key=sha256(f'{name}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ino}'.encode()).hexdigest()[:12]
        if not owned(self.root):raise ValueError('預覽快取位置不安全。')
        return self.root/(key+'.png')

    def get(self,names):
        if not isinstance(names,list) or len(names)>24:raise ValueError('一次最多讀取 24 個預覽。')
        result={}
        with self.lock:
            for name in names:
                try:
                    target=self.target(name)
                    if not owned(target) or not target.is_file() or target.stat().st_size>ITEM_LIMIT:continue
                    result[name]='data:image/png;base64,'+base64.b64encode(target.read_bytes()).decode('ascii')
                except (OSError,ValueError,TypeError):continue
        return result

    def put(self,name,data):
        if not isinstance(data,str) or not data.startswith('data:image/png;base64,') or len(data)>ITEM_LIMIT*2:raise ValueError('預覽圖片格式無效。')
        decoded=base64.b64decode(data[22:],validate=True)
        if len(decoded)>ITEM_LIMIT or len(decoded)<24:raise ValueError('預覽圖片超出限制。')
        width,height=int.from_bytes(decoded[16:20],'big'),int.from_bytes(decoded[20:24],'big')
        if not 1<=width<=320 or not 1<=height<=320:raise ValueError('預覽尺寸超出限制。')
        with self.lock:
            target=self.target(name);self.root.mkdir(parents=True,exist_ok=True)
            if not owned(target):raise ValueError('預覽位置不安全。')
            temporary=None
            try:
                with NamedTemporaryFile(dir=self.root,suffix='.part',delete=False) as stream:
                    temporary=Path(stream.name);stream.write(decoded)
                validate_content(temporary,'image')
                temporary.replace(target)
                files=sorted((p for p in self.root.glob('*.png') if owned(p) and p.is_file()),key=lambda p:p.stat().st_mtime_ns)
                total=sum(p.stat().st_size for p in files)
                for path in files:
                    if total<=LIMIT:break
                    size=path.stat().st_size;path.unlink();total-=size
            finally:
                if temporary:temporary.unlink(missing_ok=True)
        return {'saved':True,'cache_limit_bytes':LIMIT}

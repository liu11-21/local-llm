"""Bounded GGUF browser uploads; never accept arbitrary destination paths."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4
from functools import wraps
from threading import RLock
from download_recovery import owned
from downloads import check_gguf


def locked(function):
    @wraps(function)
    def wrapped(self,*args,**kwargs):
        with self.lock:return function(self,*args,**kwargs)
    return wrapped


class Uploads:
    def __init__(self,application):self.application=application;self.items={};self.lock=RLock()

    @locked
    def expire(self):
        for identity,item in list(self.items.items()):
            if time.monotonic()-item['touched']>1800:
                item['path'].unlink(missing_ok=True);del self.items[identity]

    @locked
    def start(self,data,owner):
        self.expire();name=data.get('name');size=data.get('size')
        if (not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,169}\.gguf',name,re.I)
                or Path(name).stem.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))}
                or type(size) is not int or not 16<=size<=256*1024**3):raise ValueError('只接受有效名稱的 GGUF，16 bytes–256 GiB。')
        root=self.application.service.models;root.mkdir(exist_ok=True)
        if not owned(root) or not owned(root/name) or (root/name).exists():raise ValueError('模型名稱已存在或路徑不安全，未覆蓋。')
        if len(self.items)>=4 or any(item['owner']==owner for item in self.items.values()):raise ValueError('已有匯入工作，請完成或取消。')
        reserved=sum(item['size']-item['received'] for item in self.items.values())
        if shutil.disk_usage(root).free<reserved+size+256*1024**2:raise ValueError('磁碟空間不足，未開始匯入。')
        identity=uuid4().hex;path=root/('.web-upload-'+identity+'.part')
        with path.open('xb'):pass
        self.items[identity]={'path':path,'target':root/name,'size':size,'received':0,'hash':hashlib.sha256(),'owner':owner,'touched':time.monotonic()}
        return {'id':identity,'size':size}

    @locked
    def get(self,identity,owner):
        item=self.items.get(identity)
        if not item or item['owner']!=owner:raise ValueError('找不到屬於此工作階段的匯入工作。')
        if not owned(item['path']):raise ValueError('匯入暫存路徑已變更。')
        return item

    @locked
    def append(self,identity,owner,offset,block):
        item=self.get(identity,owner)
        if type(offset) is not int or offset!=item['received'] or not block or len(block)>4*1024**2 or offset+len(block)>item['size']:
            raise ValueError('匯入位移或大小不符，未重複寫入。')
        with item['path'].open('ab') as stream:stream.write(block)
        item['hash'].update(block);item['received']+=len(block);item['touched']=time.monotonic()
        return {'received':item['received']}

    @locked
    def finish(self,identity,owner):
        item=self.get(identity,owner)
        if item['received']!=item['size']:raise ValueError('匯入未完成。')
        check_gguf(item['path'])
        if not owned(item['target']) or item['target'].exists():raise ValueError('目的模型已存在，未覆蓋。')
        # An atomic hard-link creation fails if a concurrent writer created the target;
        # unlike replace/rename it never overwrites an existing model on Windows.
        os.link(item['path'],item['target']);item['path'].unlink();del self.items[identity]
        reply=self.application.response('model-imported',{'model':item['target'].name})
        if not reply['ok']:raise ValueError(reply['error'])
        return {'name':item['target'].name,'bytes':item['size'],'sha256':item['hash'].hexdigest(),'verification':'imported; local integrity hash, not upstream provenance'}

    @locked
    def cancel(self,identity,owner):
        item=self.get(identity,owner);item['path'].unlink(missing_ok=True);del self.items[identity]

    @locked
    def close(self):
        for item in self.items.values():item['path'].unlink(missing_ok=True)
        self.items.clear()

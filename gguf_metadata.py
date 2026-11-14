"""Bounded GGUF metadata inspection; no tensor load and no inference claims."""
from functools import lru_cache
from pathlib import Path
import struct


def metadata(path):
    path=Path(path)
    try:
        stat=path.stat();return dict(read(str(path),stat.st_size,stat.st_mtime_ns))
    except (OSError,ValueError,KeyError,struct.error,OverflowError):return {}


@lru_cache(maxsize=512)
def read(path,size,stamp):
    result={};limit=min(size,64*1024**2)
    with Path(path).open('rb') as f:
        def take(n):
            if n<0 or f.tell()+n>limit:raise ValueError('GGUF metadata limit')
            b=f.read(n)
            if len(b)!=n:raise ValueError('short GGUF')
            return b
        def skip(n):
            if n<0 or f.tell()+n>limit:raise ValueError('GGUF metadata limit')
            f.seek(n,1)
        def number(fmt):return struct.unpack('<'+fmt,take(struct.calcsize('<'+fmt)))[0]
        def text():
            n=number('Q')
            if n>1024*1024:raise ValueError('GGUF string limit')
            return take(n).decode('utf-8',errors='replace')
        formats={0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
        def value(kind,depth=0,keep=False):
            if depth>2:raise ValueError('GGUF nested array limit')
            if kind in formats:return number(formats[kind])
            if kind==8:
                if depth:
                    skip(number('Q'));return None
                return text()
            if kind==9:
                item,count=number('I'),number('Q')
                if count>2_000_000:raise ValueError('GGUF array limit')
                if item in formats:take_size=struct.calcsize('<'+formats[item])*count;skip(take_size)
                else:
                    for _ in range(count):value(item,depth+1)
                return None
            raise ValueError('GGUF type')
        if take(4)!=b'GGUF' or number('I') not in (2,3):return {}
        number('Q');count=number('Q')
        if count>50000:raise ValueError('GGUF field limit')
        for _ in range(count):
            key=text();item=value(number('I'))
            if key=='general.architecture' and isinstance(item,str):result['architecture']=item
            elif key.endswith('.context_length') and type(item) is int and item>0:result['context_length']=item
            elif key.endswith('.block_count') and type(item) is int:result['block_count']=item
            elif key=='general.file_type' and type(item) is int:result['file_type_id']=item
    return result

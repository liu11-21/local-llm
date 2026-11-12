"""Physical-RAM bounded process budgets; shared GPU memory is already system RAM."""
import json

GIB=1024**3
MIB=1024**2


def memory_policy(total, available=None, *, user_mib=0, required=None):
    if type(user_mib) is not int or user_mib<0 or user_mib>1048576:
        raise ValueError('記憶體上限必須為 0（自動）或有效 MiB。')
    known=type(total) is int and total>0
    reserve=max(GIB,total//10) if known else GIB
    capacity=max(0,total-reserve) if known else 0
    ceiling=min(capacity,user_mib*MIB) if user_mib else capacity
    # A reservation and the Job Object use the same rounded committed-memory cap.
    limit=((max(required,GIB)+MIB-1)//MIB)*MIB if type(required) is int and required>0 else None
    return {'schema':1,'physical_ram':total,'available_ram':available,'os_reserve':reserve,
            'safe_capacity':capacity,'user_limit_mib':user_mib,'ceiling':ceiling,
            'job_limit':limit,'feasible':bool(limit and limit<=ceiling),
            'admission_available':max(0,available-reserve) if type(available) is int else None,
            'shared_memory_included':True,'unknown_requirement':limit is None}


def configured(app):
    return getattr(app,'device_memory_mib',0)


def load(app):
    with app.connect() as db:
        row=db.execute("SELECT value FROM settings WHERE key='device_memory_mib'").fetchone()
    return int(json.loads(row[0])) if row else 0


def save(app,value):
    memory_policy(None,user_mib=value)
    with app.connect() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES('device_memory_mib',?)",(json.dumps(value),))
    app.device_memory_mib=value

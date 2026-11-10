"""Durable, owner-scoped remote jobs. Request bodies and credentials stay out of SQLite."""
import json

from task_manager import timestamp


class RemoteJobs:
    def __init__(self, connect):
        self.connect = connect

    @staticmethod
    def initialize(db):
        db.execute("""CREATE TABLE IF NOT EXISTS remote_jobs (
                   owner TEXT NOT NULL, request TEXT NOT NULL, signature BLOB NOT NULL, task TEXT NOT NULL,
                   kind TEXT NOT NULL, runtime TEXT NOT NULL, model TEXT NOT NULL, workflow TEXT,
                   state TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL, finished TEXT,
                   message TEXT NOT NULL, progress INTEGER, total INTEGER, answer TEXT, artifact TEXT,
                   PRIMARY KEY(owner, request))""")
        now = timestamp()
        db.execute("""UPDATE remote_jobs SET state='interrupted',updated=?,finished=?,
                   message='運算主機已重啟，未完成的任務已中斷。'
                   WHERE state IN ('queued','running','paused')""", (now,now))
        if db.execute("PRAGMA user_version").fetchone()[0] < 8:
            db.execute("PRAGMA user_version=8")

    def writer(self, owner, request, signature, kind, model, workflow=None):
        def write(value):
            state = value["state"]
            result = value.get("result") or {}
            artifact = result.get("artifact") if state == "completed" else None
            with self.connect() as db:
                db.execute("""INSERT INTO remote_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(owner,request) DO UPDATE SET
                           state=excluded.state,updated=excluded.updated,finished=excluded.finished,
                           message=excluded.message,progress=excluded.progress,total=excluded.total,
                           answer=excluded.answer,artifact=excluded.artifact
                           WHERE remote_jobs.task=excluded.task AND remote_jobs.state NOT IN
                           ('interrupted','completed','failed','cancelled')""",
                           (owner,request,signature,value["id"],kind,"local",model,workflow,state,value["created"],
                            timestamp(),value["finished"],value["message"],value.get("received"),value.get("total"),
                            value.get("answer") if state == "completed" else None,
                            json.dumps(artifact) if artifact else None))
        return write

    def get(self, db, owner, request):
        result = db.execute("""SELECT signature,task,kind,runtime,model,workflow,state,created,updated,finished,
                            message,progress,total,answer,artifact FROM remote_jobs WHERE owner=? AND request=?""",
                            (owner,request)).fetchone()
        if result is None:
            return None
        names = ("signature","task","kind","runtime","model","workflow","state","created","updated",
                 "finished","message","received","total","answer","artifact")
        row = {key:value for key,value in zip(names,result) if value is not None}
        if row.get("artifact"):
            row["artifact"] = json.loads(row["artifact"])
        return row

    def interrupt(self):
        now = timestamp()
        with self.connect() as db:
            db.execute("""UPDATE remote_jobs SET state='interrupted',updated=?,finished=?,
                       message='主機停止分享。請重新提交未完成的任務。'
                       WHERE state IN ('queued','running','paused')""", (now,now))

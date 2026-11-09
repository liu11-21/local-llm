"""Versioned local agent plans. SQLite is the authority for grants and audit events."""
from contextlib import contextmanager
import json
import re
from time import time
from uuid import uuid4

from task_manager import timestamp

PENDING = {"draft", "awaiting_approval"}
LIVE = {"approved", "running", "paused"}
TERMINAL = {"completed", "failed", "cancelled", "expired", "interrupted"}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("代理人計畫識別碼無效。")
    return value


def append_event(plan, kind, **details):
    plan["events"].append({"kind": kind, "at": timestamp(), **details})


class AgentPlans:
    def __init__(self, connect):
        self.connect = connect

    def initialize(self, db):
        db.execute("""CREATE TABLE IF NOT EXISTS agent_plans(
                      id TEXT PRIMARY KEY, created REAL NOT NULL, record TEXT NOT NULL)""")
        for (raw,) in db.execute("""SELECT record FROM agent_plans WHERE
                                    json_extract(record,'$.state') IN ('approved','running','paused')""").fetchall():
            plan = json.loads(raw)
            self.transition(plan, "interrupted", "工作台重開。中斷的操作需要重新預覽並核准。")
            self.write(db, plan)

    @staticmethod
    def read(db, plan_id):
        row = db.execute("SELECT record FROM agent_plans WHERE id=?", (identifier(plan_id),)).fetchone()
        if not row:
            raise ValueError("找不到代理人計畫。")
        return json.loads(row[0])

    @staticmethod
    def write(db, plan):
        db.execute("""INSERT INTO agent_plans VALUES(?,?,?)
                      ON CONFLICT(id) DO UPDATE SET record=excluded.record""",
                   (plan["id"], plan["created_at"], json.dumps(plan, ensure_ascii=False, allow_nan=False)))

    @staticmethod
    def transition(plan, state, message=None):
        current = plan["state"]
        edges = {
            "draft": {"awaiting_approval", "cancelled", "expired"},
            "awaiting_approval": {"approved", "cancelled", "expired"},
            "approved": {"running", "failed", "cancelled", "interrupted"},
            "running": {"paused", "completed", "failed", "cancelled", "interrupted"},
            "paused": {"running", "failed", "cancelled", "interrupted"},
        }
        if state == current:
            return
        if state not in edges.get(current, set()):
            raise ValueError("代理人計畫狀態已變更，請重新讀取。")
        plan["state"] = state
        if state in TERMINAL:
            plan["pending"] = None
        if message and state in {"failed", "interrupted"}:
            plan["error"] = message
        append_event(plan, state, **({"message": message} if message else {}))

    @contextmanager
    def edit(self, plan_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            plan = self.read(db, plan_id)
            yield plan
            self.write(db, plan)

    def create(self, options, previous=None, version=None):
        now = time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if previous:
                old = self.read(db, previous)
                if old["state"] not in PENDING or type(version) is not int or version != old["version"]:
                    raise ValueError("這份計畫的版本已變更，請重新預覽。")
                plan = {**old, **options, "state": "draft", "version": old["version"] + 1}
                append_event(plan, "revised", version=plan["version"])
            else:
                count = db.execute("""SELECT COUNT(*) FROM agent_plans
                    WHERE json_extract(record,'$.state')='awaiting_approval'
                    AND json_extract(record,'$.expires_at')>?""", (now,)).fetchone()[0]
                if count >= 32:
                    raise ValueError("待核准計畫已滿。請撤銷舊計畫。")
                plan = {**options, "id": uuid4().hex, "agent_id": uuid4().hex, "task_id": None, "version": 1,
                        "created_at": now, "events": [], "state": "draft", "evidence": [], "answer": None,
                        "pending": None, "error": None, "execution": None}
                append_event(plan, "draft")
            plan.update(expires_at=now + 900, approval=None)
            self.transition(plan, "awaiting_approval")
            self.write(db, plan)
            return self.public(plan)

    @staticmethod
    def public(plan):
        return {key: value for key, value in plan.items() if key != "execution"}

    def get(self, plan_id):
        with self.connect() as db:
            plan = self.read(db, plan_id)
        if plan["state"] in PENDING and plan["expires_at"] <= time():
            with self.edit(plan_id) as latest:
                if latest["state"] in PENDING and latest["expires_at"] <= time():
                    self.transition(latest, "expired")
                plan = latest
        return self.public(plan)

    def list(self):
        with self.connect() as db:
            ids = db.execute("SELECT id FROM agent_plans ORDER BY created DESC LIMIT 24").fetchall()
        return [{key: plan[key] for key in ("id", "state", "prompt", "model", "version", "task_id")}
                for (key,) in ids for plan in [self.get(key)]]

    def revoke(self, plan_id, version):
        with self.edit(plan_id) as plan:
            if type(version) is not int or plan["version"] != version or plan["state"] not in PENDING:
                raise ValueError("只能撤銷目前版本的待核准計畫。")
            self.transition(plan, "cancelled", "使用者撤銷計畫。")
        return self.public(plan)

    def sync_task(self, db, task):
        plan = self.read(db, task["plan_id"])
        state = task["state"]
        if not plan["task_id"]:
            if (state != "queued" or plan["state"] != "awaiting_approval" or plan["expires_at"] <= time()
                    or type(task.get("plan_version")) is not int or plan["version"] != task["plan_version"]):
                raise ValueError("計畫未核准、已失效或版本不符。請重新預覽。")
            plan["task_id"] = task["id"]
            plan["approval"] = {"at": timestamp(), "version": plan["version"], "tools": plan["tools"].copy()}
            self.transition(plan, "approved")
        elif plan["task_id"] != task["id"]:
            raise ValueError("這份計畫已交付給其他任務。")
        elif state in LIVE | TERMINAL and plan["state"] not in TERMINAL:
            self.transition(plan, state, task["message"] if state in {"failed", "interrupted", "cancelled"} else None)
        self.write(db, plan)

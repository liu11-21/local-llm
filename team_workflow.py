"""Role profiles, validated dependency graphs and durable team results."""
from contextlib import contextmanager
import json
import re
from time import time
from uuid import uuid4

from agent_runtime import Deadline
from task_manager import timestamp
from tool_registry import ToolError
from web_bridge import field

ROLES = {
    "coordinator": ("協調者", "Plan the work, resolve inconsistencies, and synthesize a practical answer."),
    "researcher": ("研究員", "Identify relevant facts, distinguish evidence from assumptions, and cite inputs."),
    "analyst": ("分析員", "Analyze the supplied evidence and explain tradeoffs and missing information."),
    "reviewer": ("審查者", "Find factual errors, omissions and weak reasoning. Suggest specific corrections."),
    "writer": ("撰寫者", "Write a coherent deliverable that addresses the user's actual task."),
    "custom": ("自訂", ""),
}
TEMPLATES = {
    "research": ("通用研究", "parallel", ("coordinator", "researcher", "analyst"), "要點、依據與待查問題"),
    "document": ("文件分析", "delegated", ("writer", "researcher", "analyst"), "摘要、重點、風險"),
    "code": ("程式碼審查", "review", ("writer", "reviewer"), "修正版與尚存問題"),
    "creative": ("創意企劃", "parallel", ("coordinator", "writer", "reviewer"), "提案與取捨"),
}
MODES = {"parallel", "delegated", "review", "custom"}
MAX_NODES = 16


def templates():
    return [{"id": key, "name": name, "mode": mode, "lead": "m1", "expected": expected, "nodes": [],
             "members": [{"id": f"m{i}", "name": ROLES[role][0], "role": role, "system": ROLES[role][1],
                          "goal": "", "model": "", "runtime": "local", "tools": [], "tokens": 384, "steps": 6}
                         for i, role in enumerate(roles, 1)]} for key, (name, mode, roles, expected) in TEMPLATES.items()]


def key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,31}", value):
        raise ValueError("成員或節點 ID 格式無效。")
    return value


def number(data, name, default, minimum, maximum):
    value = data.get(name, default)
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} 須介於 {minimum} 和 {maximum}。")
    return value


def profile(data, registry):
    if not isinstance(data, dict):
        raise ValueError("團隊成員設定無效。")
    role = field(data, "role", 20)
    if role not in ROLES:
        raise ValueError("團隊角色無效。")
    tools = data.get("tools", [])
    if (not isinstance(tools, list) or len(tools) > 4 or any(not isinstance(tool, str) for tool in tools)
            or len(set(tools)) != len(tools)):
        raise ValueError("團隊工具允許清單無效。")
    for tool in tools:
        registry.definition(tool, tools)
    arguments = data.get("tool_arguments", {})
    if not isinstance(arguments, dict) or arguments.keys() - set(tools):
        raise ValueError("工具參數必須對應已勾選的工具。")
    arguments = {tool: arguments.get(tool, {}) for tool in tools}
    for tool, args in arguments.items():
        registry.authorize(tool, args, tools)
    return {"id": key(data.get("id")), "role": role, "tools": tools.copy(),
            "tool_arguments": arguments,
            "name": field(data, "name", 60), "system": field(data, "system", 1200, optional=True) or ROLES[role][1],
            "goal": field(data, "goal", 1200, optional=True), "model": field(data, "model", 200, optional=True),
            "runtime": field(data, "runtime", 32), "tokens": number(data, "tokens", 384, 64, 1024),
            "steps": number(data, "steps", 6, 1, 12)}


def node(identifier, agent, label, task, deps=(), partial=False):
    return {"id": identifier, "agent": agent, "label": label, "task": task, "deps": list(deps), "partial": partial}


def default_graph(mode, members, lead):
    ids = [member["id"] for member in members]
    others = [agent for agent in ids if agent != lead]
    if mode == "parallel":
        drafts = [node(f"draft{i}", agent, f"獨立草稿 {i}", "Independently analyze the common task.")
                  for i, agent in enumerate(ids, 1)]
        return [*drafts, node("final", lead, "協調整合", "Compare the independent drafts and write one answer.",
                              [item["id"] for item in drafts], True)]
    if mode == "delegated":
        result = [node("brief", lead, "分工規劃", "Identify distinct work items for the team roles and constraints.")]
        for index, agent in enumerate(others, 1):
            deps = list(dict.fromkeys(["brief", result[-1]["id"]]))
            result.append(node(f"delegate{index}", agent, f"分工 {index}",
                               "Execute the assigned role using the plan and preceding work.", deps, True))
        return [*result, node("final", lead, "交付整合", "Combine the completed work into the final deliverable.",
                              [item["id"] for item in result[1:]], True)]
    reviewer = next((member["id"] for member in members if member["id"] != lead and member["role"] == "reviewer"),
                    others[0])
    return [node("draft", lead, "初稿", "Write an initial draft."),
            node("review", reviewer, "交叉審查", "Identify mistakes and propose concrete revisions.", ["draft"]),
            node("revision", lead, "修正版", "Revise the draft using the review and return the revised deliverable.",
                 ["draft", "review"]),
            node("final", lead, "最終交付", "Use the revised version if available. Surface any material open issues.",
                 ["draft", "review", "revision"], True)]


def validated_graph(raw, members, final):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_NODES:
        raise ValueError("工作流程須有 1 至 16 個節點。")
    by_agent = {member["id"]: member for member in members}
    counts = dict.fromkeys(by_agent, 0)
    graph = {}
    for value in raw:
        if not isinstance(value, dict):
            raise ValueError("工作節點資料無效。")
        ident, agent = key(value.get("id")), key(value.get("agent"))
        deps = value.get("deps", [])
        if (ident in graph or agent not in by_agent or not isinstance(deps, list) or len(deps) > MAX_NODES
                or len(set(map(key, deps))) != len(deps) or type(value.get("partial", False)) is not bool):
            raise ValueError("節點重複、成員不存在，或依賴定義無效。")
        counts[agent] += 1
        if counts[agent] > by_agent[agent]["steps"]:
            raise ValueError(f"{by_agent[agent]['name']} 的節點數超過個人步驟上限。")
        graph[ident] = node(ident, agent, field(value, "label", 60), field(value, "task", 1600), deps,
                            value.get("partial", False))
    if final not in graph or any(dep not in graph for item in graph.values() for dep in item["deps"]):
        raise ValueError("工作流程含有不存在的依賴或最終節點。")
    ordered, ready = [], set()
    while len(ordered) < len(graph):
        layer = [item for ident, item in graph.items() if ident not in ready and set(item["deps"]) <= ready]
        if not layer:
            raise ValueError("工作流程含有循環依賴。")
        ordered.extend(layer)
        ready.update(item["id"] for item in layer)
    return ordered


def specification(data, registry):
    values = data.get("members")
    if not isinstance(values, list) or not 2 <= len(values) <= 6:
        raise ValueError("團隊須有 2 至 6 位成員。")
    members = [profile(value, registry) for value in values]
    ids = {item["id"] for item in members}
    lead, mode = key(data.get("lead")), field(data, "mode", 20)
    if len(ids) != len(members) or lead not in ids or mode not in MODES:
        raise ValueError("團隊成員、協調者或工作模式無效。")
    if any(member["runtime"] != "local" for member in members) and any(member["tools"] for member in members):
        raise ValueError("有外部運算的工作流程不能啟用本機工具，以免工具資料隨草稿外傳。")
    final = key(data.get("final")) if mode == "custom" else "final"
    raw = data.get("nodes") if mode == "custom" else default_graph(mode, members, lead)
    return {"name": field(data, "name", 80), "mode": mode, "lead": lead, "members": members, "final": final,
            "expected": field(data, "expected", 300, optional=True),
            "nodes": validated_graph(raw, members, final), "seconds": number(data, "seconds", 360, 30, 900)}


def outcome(run):
    nodes = run["nodes"]
    warnings = [item["id"] for item in nodes if item["state"] in {"failed", "skipped"} or
                any("error" in fact for fact in item.get("evidence", []))]
    partial = [item["id"] for item in nodes if item.get("partial_dependencies") or
               (item.get("partial") and item["state"] == "completed" and any(
                   other["id"] in item["deps"] and other["state"] != "completed" for other in nodes))]
    unchecked = [item["id"] for item in nodes if run["spec"]["mode"] == "review"
                 and item["id"] in {"review", "revision"} and item["state"] != "completed"]
    return {"status": "unavailable" if not run["answer"] else
            "completed_with_warnings" if warnings or partial or unchecked else "complete",
            "warnings": warnings, "partial_nodes": partial, "unchecked": unchecked}


class TeamStore:
    def __init__(self, connect):
        self.connect = connect

    def initialize(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS team_configs(id TEXT PRIMARY KEY, record TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS team_runs(id TEXT PRIMARY KEY, created REAL NOT NULL, record TEXT NOT NULL)")
        for (raw,) in db.execute("""SELECT record FROM team_runs WHERE
            json_extract(record,'$.state') IN ('draft','queued','running')""").fetchall():
            run = json.loads(raw)
            run.update(state="interrupted", error="工作台重開，已保存完成的節點。")
            for item in run["nodes"]:
                if item["state"] in {"queued", "running"}:
                    item["state"] = "interrupted"
            self.write(db, run)

    @staticmethod
    def write(db, run):
        db.execute("""INSERT INTO team_runs VALUES(?,?,?)
                      ON CONFLICT(id) DO UPDATE SET record=excluded.record""",
                   (run["id"], run["created"], json.dumps(run, ensure_ascii=False, allow_nan=False)))

    @staticmethod
    def read(db, ident):
        row = db.execute("SELECT record FROM team_runs WHERE id=?", (ident,)).fetchone()
        if not row:
            raise ValueError("找不到團隊執行紀錄。")
        return json.loads(row[0])

    @contextmanager
    def edit(self, ident):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self.read(db, ident)
            yield run
            self.write(db, run)

    def save(self, spec, ident=None):
        with self.connect() as db:
            if ident is not None and not db.execute("SELECT 1 FROM team_configs WHERE id=?", (ident,)).fetchone():
                raise ValueError("找不到要更新的團隊設定。")
            config = {**spec, "id": ident or uuid4().hex}
            db.execute("INSERT OR REPLACE INTO team_configs VALUES(?,?)",
                       (config["id"], json.dumps(config, ensure_ascii=False)))
        return config

    def configs(self):
        with self.connect() as db:
            return [json.loads(raw) for (raw,) in db.execute("SELECT record FROM team_configs ORDER BY rowid DESC LIMIT 30")]

    def create_run(self, spec, prompt):
        ident = uuid4().hex
        record = {"id": ident, "spec": spec, "prompt": prompt, "created": time(), "state": "draft", "task_id": None,
                  "answer": None, "error": None, "nodes": [{**item, "state": "queued", "evidence": []} for item in spec["nodes"]]}
        with self.connect() as db:
            self.write(db, record)
        return ident

    def get(self, ident):
        with self.connect() as db:
            run = self.read(db, ident)
        return {**run, "outcome": outcome(run)}

    def list(self):
        with self.connect() as db:
            values = [json.loads(raw) for (raw,) in db.execute("SELECT record FROM team_runs ORDER BY created DESC LIMIT 20")]
        return [{key: item[key] for key in ("id", "state", "created", "task_id")} |
                {"name": item["spec"]["name"], "mode": item["spec"]["mode"],
                 "outcome": outcome(item)["status"]} for item in values]

    def sync_task(self, db, task):
        run = self.read(db, task["team_run_id"])
        if run["task_id"] not in (None, task["id"]):
            raise ValueError("團隊紀錄已交付給其他任務。")
        run.update(state=task["state"], task_id=task["id"], error=task.get("error"))
        if task["state"] in {"failed", "interrupted", "cancelled"}:
            for item in run["nodes"]:
                if item["state"] in {"queued", "running"}:
                    item["state"] = task["state"] if task["state"] != "failed" else "skipped"
        self.write(db, run)


def run_team(store, ident, registry, ask, cancel, update):
    run = store.get(ident)
    spec = run["spec"]
    agents = {member["id"]: member for member in spec["members"]}
    if any(member["runtime"] != "local" and member["runtime"] not in spec.get("external_grants", [])
           for member in agents.values()):
        raise ValueError("TEAM_EXTERNAL_NOT_GRANTED · 團隊外部運算未取得此次授權。")
    records = {item["id"]: item for item in run["nodes"]}
    deadline = Deadline(cancel, time() + spec["seconds"], "團隊", "TEAM_TIME_LIMIT")
    for item in run["nodes"]:
        deadline.check()
        deps = [records[dep] for dep in item["deps"]]
        available = [dep for dep in deps if dep["state"] == "completed"]
        if deps and (not available or (not item["partial"] and len(available) != len(deps))):
            item.update(state="skipped", error="必要的前置節點未完成。", finished=timestamp())
        else:
            item.update(state="running", started=timestamp(),
                        partial_dependencies=[dep["id"] for dep in deps if dep["state"] != "completed"])
            with store.edit(ident) as latest:
                latest["nodes"] = list(records.values())
            update(message=f"{item['label']} · {agents[item['agent']]['name']} 執行中")
            member = agents[item["agent"]]
            for tool in member["tools"]:
                deadline.check()
                args = member.get("tool_arguments", {}).get(tool, {})
                audit = {"tool": tool, "arguments": args, "approved": spec.get("tools_approved") is True}
                try:
                    output = registry.execute(tool, args, member["tools"], deadline, granted=audit["approved"])
                    item["evidence"].append({**audit, "output": output})
                except ToolError as error:
                    item["evidence"].append({**audit, "error": error.code})
                with store.edit(ident) as latest:
                    latest["nodes"] = list(records.values())
            try:
                text = ask(member, item, available, run["prompt"], spec["expected"], deadline)
                deadline.check()
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("模型未回傳有效文字。")
                item.update(state="completed", text=text.strip()[:10000])
            except Exception as error:
                deadline.check()
                message = (str(error).strip().splitlines() or ["節點執行失敗。"])[0]
                item.update(state="failed", error=message[:360])
            item["finished"] = timestamp()
        with store.edit(ident) as latest:
            latest["nodes"] = list(records.values())
    final = records[spec["final"]]
    if final["state"] != "completed":
        raise ValueError("TEAM_FINAL · 最終節點未完成，已保存可用的部分結果。")
    with store.edit(ident) as latest:
        latest["answer"] = final["text"]
    quality = outcome(store.get(ident))
    return {"answer": final["text"], "team_run_id": ident, "message":
            "已保存部分交付，請查看警告。" if quality["status"] == "completed_with_warnings" else "團隊流程已保存。"}

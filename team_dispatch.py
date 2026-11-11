"""Dependency orchestration using child tasks in the existing TaskManager."""
from time import monotonic,time

from agent_runtime import Deadline
from device_resources import ResourceDemand
from task_manager import timestamp
from team_workflow import outcome
from tool_registry import ToolError


def change(store,identity,node,**values):
    with store.edit(identity) as run:
        item=next(item for item in run["nodes"] if item["id"]==node)
        item.update(values)


def run_node(app,data,cancel,update):
    run=app.team_store.get(data["id"])
    spec=run["spec"]
    item=next(item for item in run["nodes"] if item["id"]==data["node"])
    member=next(member for member in spec["members"] if member["id"]==item["agent"])
    if member["runtime"] not in ("local","openvino") and member["runtime"] not in spec.get("external_grants",[]):
        raise ValueError("TEAM_EXTERNAL_NOT_GRANTED")
    deadline=Deadline(cancel,time()+max(0,data["deadline"]-monotonic()),"團隊","TEAM_TIME_LIMIT")
    change(app.team_store,data["id"],item["id"],state="running",started=timestamp())
    evidence=[]
    try:
        for tool in member["tools"]:
            deadline.check()
            args=member.get("tool_arguments",{}).get(tool,{})
            audit={"tool":tool,"arguments":args,"approved":spec.get("tools_approved") is True}
            try:
                output=app.agent_tools.execute(tool,args,member["tools"],deadline,granted=audit["approved"])
                evidence.append({**audit,"output":output})
            except ToolError as error:evidence.append({**audit,"error":error.code})
            change(app.team_store,data["id"],item["id"],evidence=evidence)
        item["evidence"]=evidence
        text=app.ask_team_agent(member,item,data["dependencies"],run["prompt"],spec["expected"],deadline,update)
        deadline.check()
        if not isinstance(text,str) or not text.strip():raise ValueError("模型未回傳有效文字。")
        change(app.team_store,data["id"],item["id"],state="completed",text=text.strip()[:10000],finished=timestamp())
        return {"text":text.strip()[:10000]}
    except Exception as error:
        change(app.team_store,data["id"],item["id"],state="cancelled" if cancel.is_set() else "failed",
               error=(str(error).splitlines() or ["節點失敗"])[0][:360],finished=timestamp())
        raise


def run_team(app,identity,cancel,update,parent_id):
    run=app.team_store.get(identity)
    spec=run["spec"]
    agents={member["id"]:member for member in spec["members"]}
    end=monotonic()+spec["seconds"]
    pending={}
    submitted=set()
    try:
        while True:
            if cancel.is_set():raise InterruptedError("團隊已取消。")
            if monotonic()>end:raise TimeoutError("TEAM_TIME_LIMIT · 團隊已達時間上限。")
            latest=app.team_store.get(identity)
            nodes={item["id"]:item for item in latest["nodes"]}
            for node,task in list(pending.items()):
                value=app.scheduler.snapshot(task)
                if value["state"] not in ("running","queued"):
                    if nodes[node]["state"] not in ("completed","failed","skipped","cancelled"):
                        change(app.team_store,identity,node,state="failed",error=value["message"][:360],finished=timestamp())
                    pending.pop(node)
            if len(submitted)==len(nodes) and not pending:break
            for node,item in nodes.items():
                if node in submitted:continue
                deps=[nodes[dep] for dep in item["deps"]]
                if any(dep["state"] in ("pending","queued","running") for dep in deps):continue
                available=[dep for dep in deps if dep["state"]=="completed"]
                if deps and (not available or not item["partial"] and len(available)!=len(deps)):
                    change(app.team_store,identity,node,state="skipped",error="必要的前置節點未完成。",finished=timestamp())
                    submitted.add(node);continue
                if len([task for task in app.scheduler.list() if task["state"] in ("queued","running","paused")])>=30:break
                member=agents[item["agent"]]
                payload={"id":identity,"node":node,"dependencies":available,"deadline":end,"runtime":member["runtime"]}
                change(app.team_store,identity,node,state="queued",partial_dependencies=[dep["id"] for dep in deps if dep["state"]!="completed"])
                try:
                    if member["runtime"] in ("local","openvino"):
                        options={"model":member["model"],"runtime":member["runtime"],"context":4096 if member["runtime"]=="local" else 1024,
                                 "execution":member.get("execution") or {"device":"CPU","confirmed":True}}
                        target=app.device_execution.prepare("team",options)
                        job=app.device_execution.submit("team-node",payload,target=target,parent_id=parent_id)
                    else:
                        claim=ResourceDemand(scope="remote",device=member["runtime"],engine="remote-text",exclusive=("remote:"+member["runtime"],))
                        job=app.scheduler.submit("team-node",payload,demand=claim,parent_id=parent_id)
                    pending[node]=job["id"]
                except Exception as error:
                    change(app.team_store,identity,node,state="failed",error=str(error)[:360],finished=timestamp())
                submitted.add(node)
            update(message=f"團隊節點 · {len(submitted)-len(pending)}/{len(nodes)} 已結束 · {len(pending)} 等候或執行中")
            cancel.wait(.1)
        result=app.team_store.get(identity)
        final=next(item for item in result["nodes"] if item["id"]==spec["final"])
        if final["state"]!="completed":raise ValueError("TEAM_FINAL · 最終節點未完成，已保留部分結果。")
        with app.team_store.edit(identity) as latest:latest["answer"]=final["text"]
        quality=outcome(app.team_store.get(identity))
        return {"answer":final["text"],"team_run_id":identity,"drafts":[{"name":item["label"],"text":item.get("text","")} for item in result["nodes"] if item["id"]!=spec["final"]],
                "message":"已保存部分交付，請查看警告。" if quality["status"]=="completed_with_warnings" else "團隊流程已保存。"}
    finally:
        for node,task in pending.items():
            app.scheduler.snapshot(task,cancel=True)
            change(app.team_store,identity,node,state="cancelled",error="父任務已停止。",finished=timestamp())

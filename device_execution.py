"""Per-task scopes over existing engines; all admission remains in TaskManager."""
from contextlib import ExitStack,contextmanager
from copy import copy
from dataclasses import dataclass
import json
from threading import Lock
from time import time
from uuid import uuid4

from agent_runtime import AgentRuntime,local_decision
from device_resources import ResourceDemand
from engine import LocalEngine
from engine_health import EngineHealth
from hardware import detect_hardware
from resource_contract import fresh_measure
from task_manager import PauseTask,timestamp
from resource_policy import configured,memory_policy


@dataclass(frozen=True)
class DispatchTarget:
    runtime: str
    device: str
    model: str
    engine: str
    demand: ResourceDemand
    threads: int
    memory: int
    hashes: tuple = ()
    binary_sha256: str | None = None
    recommendation: dict | None = None


class DeviceExecution:
    def __init__(self,app):
        self.app,self.lock,self.scopes = app,Lock(),{}
        self.new_local=LocalEngine
        with app.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS dispatch_runs(id TEXT PRIMARY KEY,task TEXT,state TEXT,details TEXT,created TEXT,finished TEXT)")
            db.execute("UPDATE dispatch_runs SET state='interrupted',finished=? WHERE state='running'",(timestamp(),))
            if db.execute("PRAGMA user_version").fetchone()[0]<12:db.execute("PRAGMA user_version=12")

    def snapshot(self):
        hardware=self.app.hardware_monitor.snapshot()
        physical=detect_hardware(self.app.data)
        policy=memory_policy(physical.ram_total,physical.ram_available,user_mib=configured(self.app))
        free=policy['admission_available']
        vram={item["id"]:item["vram_available"]["value"] for item in hardware["devices"] if
              item.get("memory_type")=="dedicated" and fresh_measure(item["vram_available"])}
        external=[]
        if self.app.comfy.running():
            _,claim=self.app.comfy_resources.snapshot()
            external.append(("comfyui-resident",claim or ResourceDemand(engine='ComfyUI')))
        active=self.app.active
        if self.app.local.running() and active and active[-1].get("layers",0)>0:
            external.append(("legacy-llama-resident",ResourceDemand(engine="llama.cpp",exclusive=("gpu:*",))))
        return {"ram_available":free,"vram":vram,"external":external}

    def prepare(self, task, data, *, confirmed=True):
        selection=data.get("execution")
        if not isinstance(selection,dict) or selection.get("confirmed") is not True or not confirmed:
            raise ValueError("請先確認所選 Runtime、裝置與資源需求。")
        runtime,device=data.get("runtime","local"),selection.get("device")
        if runtime not in ("local","openvino"):
            raise ValueError("外部 Runtime 使用既有目的地確認，不接受本機裝置派送。")
        query=self.app.device_recommendations.query({"task":task,"model":data.get("model"),"policy":data.get("policy","auto")})
        candidate=next((item for item in query["candidates"] if item["runtime"]==runtime and item["device"]==device),None)
        if candidate is None or candidate["availability"] in ("incompatible","needs-setup"):
            raise ValueError("DEVICE_UNAVAILABLE · 所選模型／設備不相容或尚未就緒，請重新檢查。")
        resource=candidate["resource"]
        ram=resource["ram_estimate"]
        if type(ram) is not int or ram<=0:raise ValueError("RAM_UNKNOWN · 缺少可靠的模型需求估計。")
        context=data.get("context",2048)
        if context not in (1024,2048,4096,8192):raise ValueError("上下文設定無效。")
        ram+=max(0,context-2048)*64*1024
        physical=resource["physical_device"]
        engine=candidate["engine"]
        cpu=device=="CPU"
        gpu=device.startswith(("GPU","Vulkan","CUDA"))
        npu=device.startswith("NPU")
        unified=(gpu or npu) and resource["memory_type"]!="dedicated"
        locks=["cpu:host" if cpu else "gpu:"+(physical or "*") if gpu else "npu:"+device,
               f"engine:{engine}:{device}"]
        if unified:locks.append("unified:accelerator")
        if npu:locks.append("provider:openvino-npu")
        pools=((physical,resource["vram_estimate"]),) if gpu and physical and resource["memory_type"]=="dedicated" and resource["vram_estimate"] else ()
        seconds=selection.get("seconds",600)
        if type(seconds) is not int or not 15<=seconds<=600:raise ValueError("裝置任務時間上限須為 15–600 秒。")
        capacity=detect_hardware(self.app.data)
        policy=memory_policy(capacity.ram_total,capacity.ram_available,user_mib=configured(self.app),required=ram)
        if not policy['feasible']:raise ValueError('RAM_CAPACITY · 需求超過實體 RAM 安全容量或使用者上限，請選擇較小模型／其他 Runtime。')
        memory=policy['job_limit']
        demand=ResourceDemand(device=physical or f"{engine}:{device}",engine=engine,ram=memory,vram=pools,
            shared_memory=memory if unified else 0,cpu_load=60 if cpu else 20,bandwidth=40 if cpu else 60 if unified and gpu else 50 if unified else 20,
            exclusive=tuple(locks),seconds=seconds,limitations=tuple(candidate["uncertainty"]))
        threads=max(1,min(8,(self.app.info()["hardware"]["cpu_threads"] or 2)//2)) if cpu else 2
        receipt=selection.get('recommendation_id')
        recommendation=self.app.recommendation_receipts.verify(receipt,runtime,device,data['model']) if receipt else None
        return DispatchTarget(runtime,device,data["model"],engine,demand,threads,memory,
            tuple(sorted(candidate["identity"].get("model_hashes",{}).items())),candidate["identity"].get("executable_sha256"),recommendation)

    def submit(self,action,data,*,target=None,**options):
        target=target or self.prepare("chat" if action=="chat" else action,data)
        return self.app.scheduler.submit(action,{**data,"runtime":target.runtime,"_dispatch":target},demand=target.demand,**options)

    @contextmanager
    def scope(self,target,task_id,cancel):
        physical=detect_hardware(self.app.data)
        if not memory_policy(physical.ram_total,user_mib=configured(self.app),required=target.memory)['feasible']:
            raise ValueError('RAM_POLICY_CHANGED · 排隊期間安全容量或使用者上限已變更。')
        if target.recommendation:
            self.app.recommendation_receipts.verify(target.recommendation['recommendation_id'],target.runtime,target.device,target.model)
        if target.hashes:
            if target.engine=="llama.cpp":
                actual={"gguf":self.app.device_recommendations.digest(self.app.model(target.model))}
            else:
                _,metadata=self.app.openvino.validate_model(target.model)
                actual=metadata["hashes"]
            if actual!=dict(target.hashes):raise ValueError("MODEL_CHANGED · 排隊後模型權重已變更，請重新選擇並確認。")
        if target.binary_sha256 and self.app.device_recommendations.digest(self.app.engine())!=target.binary_sha256:
            raise ValueError("ENGINE_CHANGED · 排隊後引擎已變更，請重新檢查與確認。")
        scoped=copy(self.app)
        scoped.execution_scoped=True
        scoped.execution_target=target
        scoped.local=self.new_local()
        scoped.llama_job_memory=None
        scoped.active,scoped.active_native=None,False
        scoped.llama_health=EngineHealth(scoped.local.running,scoped.local.health_probe)
        scoped.openvino=self.app.openvino.session()
        scoped.session_guards=ExitStack()
        scoped.agent_runtime=AgentRuntime(scoped.agent_plans,scoped.agent_tools,scoped.prepare_agent,
            lambda plan,state,cap,stop:local_decision(scoped.agent_engine(plan),scoped.agent_tools,plan,state,cap,stop))
        identity=uuid4().hex
        details={"runtime":target.runtime,"engine":target.engine,"model":target.model,"requested_device":target.device,
                 "model_hashes":dict(target.hashes),"engine_sha256":target.binary_sha256,
                 "resources":target.demand.public(),"recommendation":target.recommendation,
                 "dispatch_id":identity,"task_id":task_id,"execution_device_verified":False,"actual_device":"unknown"}
        with self.app.connect() as db:
            db.execute("INSERT INTO dispatch_runs VALUES(?,?,?,?,?,?)",(identity,task_id,"running",json.dumps(details),timestamp(),None))
        with self.lock:self.scopes[identity]=scoped
        state="failed"
        try:
            yield scoped,details
            state="completed"
        except PauseTask:
            state="paused"
            raise
        finally:
            if cancel.is_set():state="interrupted" if self.app.scheduler.closed else "cancelled"
            evidence=getattr(scoped.openvino,"last_evidence",None)
            if evidence:
                details.update(evidence=evidence,execution_device_verified=evidence.get("verified_inference") is True,
                               actual_device=evidence.get("execution_devices") or "unknown")
            if getattr(scoped.openvino,"last_job_memory",None):details["job_memory"]=scoped.openvino.last_job_memory
            elif scoped.llama_job_memory:details['job_memory']=scoped.llama_job_memory
            if scoped.active:details["configured_plan"]=scoped.active[-1]
            scoped.local.stop()
            scoped.openvino.close()
            scoped.session_guards.close()
            with self.lock:self.scopes.pop(identity,None)
            with self.app.connect() as db:
                db.execute("UPDATE dispatch_runs SET state=?,details=?,finished=? WHERE id=?",
                           (state,json.dumps(details),timestamp(),identity))

    def close(self):
        with self.lock:scopes=list(self.scopes.values())
        for scoped in scopes:
            scoped.local.stop()
            scoped.openvino.close()

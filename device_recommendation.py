"""Desktop inventory bridge for the existing runtime_recommendation engine."""
from hashlib import file_digest
from pathlib import Path
import platform
from statistics import mean
from threading import Lock
from time import time

from benchmark_core import TEXT_WORKLOADS,fingerprint
from benchmark_evidence import describe,evaluate,hardware_identity
from hardware import estimate_ram
from load_plan import engine_output
from resource_contract import fresh_measure
from runtime_contract import fresh,task_health
from runtime_recommendation import TASK_FORMAT,compare,recommend
from web_bridge import engine_path,field
from resource_policy import configured,memory_policy


class DeviceRecommendations:
    def __init__(self, app):
        self.app,self.cache,self.lock = app,{},Lock()

    def digest(self,path):
        path = Path(path)
        stat = path.stat()
        key = (str(path.resolve()),stat.st_size,stat.st_mtime_ns)
        with self.lock:
            saved = self.cache.get(key)
        if saved and time()-saved[0]<30:
            return saved[1]
        with path.open("rb") as stream:
            value = file_digest(stream,"sha256").hexdigest()
        if path.stat().st_mtime_ns!=stat.st_mtime_ns or path.stat().st_size!=stat.st_size:
            raise ValueError("模型或引擎正在變更，請完成下載後重新檢查。")
        with self.lock:
            if len(self.cache)>100:self.cache.clear()
            self.cache[key] = (time(),value)
        return value

    def models(self, info, engine, model):
        if engine=="llama.cpp" and model in info["models"]:
            path = self.app.model(model)
            return {"model":model,"model_hashes":{"gguf":self.digest(path)},"quantization":"encoded-in-GGUF-hash",
                    "format":"GGUF","bytes":path.stat().st_size,"kind":"text","ram":estimate_ram(path.stat().st_size)}
        if engine=="openvino" and any(item["id"]==model for item in info.get("openvino",{}).get("models",[])):
            _,metadata = self.app.openvino.validate_model(model)
            return {"model":model,"model_hashes":metadata["hashes"],"quantization":metadata.get("quantization"),
                    "format":"OpenVINO IR","bytes":metadata["bytes"],"kind":metadata["kind"],
                    "ram":metadata["bytes"]*2+512*1024**2,"npu_candidate":metadata.get("npu_candidate",False)}
        return None

    def identity(self, engine, device, info, descriptor):
        hardware = info.get("hardware_capabilities") or {"devices":[]}
        native = {}
        if engine=="openvino":
            checked=self.app.openvino.detected.get("checked_at",0)
            current_probe=type(checked) is int and 0<=time()-checked<=60
            native = dict(self.app.openvino.detected.get("identities",{}).get(device,{})) if current_probe else {}
            raw = native.get("properties",{}).get("DEVICE_LUID")
            mapping = {"state":"unknown","windows_id":None,"driver":None}
            if raw and len(raw)==16:
                try:
                    value = bytes.fromhex(raw)
                    luid = f"{int.from_bytes(value[4:],'little'):08x}_{int.from_bytes(value[:4],'little'):08x}"
                    matches = [item for item in hardware["devices"] if item["id"]==luid]
                    if len(matches)==1:
                        driver=matches[0]["driver"]
                        driver_checked=driver.get("checked_at",0)
                        driver_value=driver["value"] if type(driver_checked) is int and 0<=time()-driver_checked<=90 else None
                        mapping = {"state":"verified","windows_id":luid,"driver":driver_value}
                except ValueError:pass
            native.update(mapping=mapping,backend_version=self.app.openvino.detected.get("version") if current_probe and self.app.openvino.detected["state"]=="reported" else None)
        elif engine=="llama.cpp":
            executable = engine_path(self.app.data)
            if executable:
                digest = self.digest(executable)
                with self.lock:saved = self.cache.get(("version",digest))
                if saved is None:
                    lines = engine_output(executable,"--version").strip().splitlines()
                    saved = next((line.strip() for line in lines if line.strip()),None)
                    with self.lock:self.cache[("version",digest)] = saved
                native.update(backend_version=saved,executable_sha256=digest)
        inventory_at=hardware.get("inventory_at",0)
        identity_hardware=hardware if type(inventory_at) is int and 0<=time()-inventory_at<=90 else {"devices":[]}
        environment = {"environment":native,"hardware":identity_hardware,"cpu":platform.processor(),"machine":platform.machine()}
        return {**(descriptor or {}),"engine":engine,"device":device,"device_identity":hardware_identity(environment,engine,device),
                "backend_version":native.get("backend_version"),"executable_sha256":native.get("executable_sha256"),
                "driver":native.get("mapping",{}).get("driver"),"mapping":native.get("mapping",{}),
                "precision":"f32" if descriptor and descriptor["kind"]=="tensor" and device.startswith(("CPU","GPU")) else
                            "backend-default" if engine=="openvino" else "GGUF-native"}

    def history(self,model):
        return [self.app.benchmarks.store.get(item["id"]) for item in self.app.benchmarks.store.list(model=model)]

    def query(self,data):
        task,model = field(data,"task",20),field(data,"model",200,optional=True)
        if task not in {*TASK_FORMAT,"tensor","benchmark"}:
            raise ValueError("推薦任務類型無效。")
        info = self.app.rpc("info",{})
        records = self.app.runtime_capabilities(info)
        hardware = info.get("hardware_capabilities") or {"devices":[]}
        history = self.history(model) if model else []
        candidates = []
        profile = data.get("workload")
        selected = next((workload for workload in TEXT_WORKLOADS if workload["id"]==profile),None)
        params = {"context":data.get("context",2048),"max_tokens":data.get("max_tokens",512),"memory_mib":data.get("memory_mib",4096),
                  "batch":data.get("batch",1),"temperature":data.get("temperature",.4),"do_sample":data.get("temperature",.4)>0,"ignore_eos":False}
        usage = {"workload":profile,"workload_sha256":fingerprint(selected) if selected else data.get("workload_sha256"),"parameters":params}
        if data.get("reference") is True and selected:
            usage["parameters"] = {"context":2048,"max_tokens":32,"memory_mib":4096,"batch":1,"temperature":0,"do_sample":False,"ignore_eos":True}
            usage["reference_only"] = True
        descriptors = {}
        for record in records:
            runtime = record["id"]
            local = record["kind"]=="local"
            media = task in ("image","video","music")
            engine = "ComfyUI" if local and media else "openvino" if runtime=="openvino" else "llama.cpp" if local else record["provider"]
            if local and media and runtime!="local":continue
            if engine in ("llama.cpp","openvino"):
                descriptor = self.models(info,engine,model)
                descriptors[engine] = descriptor
                devices = ["CPU",*[entry[0] for entry in info["devices"]]] if engine=="llama.cpp" else info["openvino"]["devices"] or ["CPU"]
            else:
                descriptor = None
                devices = ["managed" if local else "remote"]
            for device in devices:
                reasons,risks,unknown = [],[],[]
                available,executable = "ready",True
                supported = task in record["tasks"] or task in ("benchmark","tensor") and engine=="openvino" or task=="benchmark" and engine=="llama.cpp"
                if task in ("agent","team") and "chat" in record["tasks"]:supported=True
                if not supported:
                    available,executable = "incompatible",False
                    reasons.append("此 Runtime 尚未支援這個任務。")
                expected_kind = "tensor" if task=="tensor" else None if task=="benchmark" else "text"
                if engine in ("llama.cpp","openvino") and (not descriptor or expected_kind and descriptor["kind"]!=expected_kind):
                    available,executable = "incompatible",False
                    reasons.append("模型未安裝或格式不適用此 Backend，不會自動轉換或下載。")
                if engine=="openvino" and (not info["openvino"]["installed"] or device not in info["openvino"]["devices"]):
                    if available!="incompatible":available="needs-setup"
                    executable=False;reasons.append("請安裝 OpenVINO Runtime 並明確查詢可用裝置。")
                if engine=="llama.cpp" and not info["engine"]:
                    if available!="incompatible":available="needs-setup"
                    executable=False;reasons.append("需要安裝 llama.cpp。")
                if device.startswith("NPU") and descriptor and descriptor["kind"]=="text" and not descriptor.get("npu_candidate"):
                    available,executable="incompatible",False
                    reasons.append("模型未通過 NPU 對稱 INT4 與壓縮條件，不會改成 CPU Fallback。")
                network = record["network"] is True
                if network and (not record["connected"] or not fresh(record)):
                    if available!="incompatible":available="needs-setup"
                    executable=False;reasons.append("端點離線或能力已過期，請重新連線。")
                if network and model and model not in record["models"] and not media:
                    available,executable="incompatible",False;reasons.append("端點未列出此模型。")
                if network and data.get("policy") in ("local","privacy"):
                    available,executable="incompatible",False;reasons.append("目前政策限制本機運算。")
                elif network and record["kind"]!="remote-host" and data.get("policy","auto")!="manual":
                    if available!="incompatible":available="needs-setup"
                    executable=False;reasons.append("外部 API 需要手動運算政策及此次資料傳送確認。")
                health = task_health(record,"chat" if task in ("agent","team","benchmark","tensor") else task)
                if health in ("offline","unhealthy"):
                    executable=False
                    if available!="incompatible":available="needs-setup"
                    reasons.append("Runtime 健康狀態不允許接收任務。")
                elif health=="busy":risks.append("設備正在工作，可能排隊。")
                required = descriptor["ram"] if descriptor else None
                if required is not None and device.startswith(("GPU","Vulkan","CUDA","NPU")):
                    required=max(required,2*1024**3)  # reserve native compiler/driver workspace as well as weights
                vram_required = None
                if media:
                    if local:
                        metadata = next((item for item in info["registry"].get("media_models",[]) if item["id"]==model or item["kind"]==task),None)
                        required = metadata.get("ram") if metadata else None
                        if not info.get("comfy_installed"):
                            available,executable="needs-setup",False;reasons.append("ComfyUI 尚未安裝。")
                        # Readiness checks nodes and managed weights, not mere filenames.
                        try:readiness = self.app.media_readiness({"kind":task,"workflow":model}) if model else {"state":"unavailable"}
                        except (ValueError,RuntimeError,OSError):readiness={"state":"unavailable"}
                        if readiness["state"]!="ready":
                            available,executable="needs-setup",False;reasons.append("創作權重、節點或服務需要準備，請使用既有一鍵安裝。")
                    elif task!="image" or record.get("media",{}).get("image",{}).get("state")!="ready" or model not in record.get("media",{}).get("image",{}).get("workflows",[]):
                        available,executable="incompatible",False;reasons.append("遠端影片／音樂尚未實作，或圖片能力未就緒。")
                incompatible = available=="incompatible"
                ram = record["resources"]["ram_available"]
                total_ram=record["resources"]["ram_total"]["value"]
                if local and required is not None and not media and not memory_policy(total_ram,user_mib=configured(self.app),required=required)['feasible']:
                    available,executable="incompatible",False
                    incompatible=True
                    reasons.append("需求超過實體 RAM 安全容量或使用者記憶體上限；請選擇較小模型或其他 Runtime。")
                if required is not None and fresh_measure(ram):
                    if ram["value"]<required:
                        available,executable="uncertain",False;risks.append("目前可用 RAM 低於需求估計，可等候釋放或改選較小模型。")
                    else:reasons.append("可用 RAM 達到估計，仍需由 Backend 實際載入驗證。")
                elif local:
                    unknown.append("需求或可用 RAM 尚未可靠確認。")
                    if available=="ready":available="uncertain"
                current = self.identity(engine,device,info,descriptor) if descriptor else {}
                if engine=="openvino" and not current.get("backend_version"):
                    unknown.append("裝置／版本查詢尚未更新，請到運算環境按「檢查 OpenVINO 裝置」。")
                mapping = current.get("mapping",{})
                matched = next((item for item in hardware["devices"] if item["id"]==mapping.get("windows_id")),None)
                memory_type = matched.get("memory_type") if matched else "unknown"
                if matched and memory_type=="dedicated":
                    vram_required = descriptor["bytes"]+512*1024**2 if descriptor else None
                    if vram_required and fresh_measure(matched["vram_available"]) and matched["vram_available"]["value"]<vram_required:
                        available,executable="uncertain",False;risks.append("所選單張 GPU 的可用專用顯存低於估計。")
                    elif not fresh_measure(matched["vram_available"]):
                        unknown.append("此 GPU 的可用顯存讀值過期或未知。")
                        if available=="ready":available="uncertain"
                elif device!="CPU" and local and not media:
                    unknown.append("統一／共享或未映射記憶體，不能把共享上限與專用 VRAM 當成可分配容量。")
                current["resources"]={"ram_available":ram,"vram_available":matched.get("vram_available") if matched else None}
                entries = []
                for session in history:
                    if session["engine"]!=engine:continue
                    for run in session["runs"]:
                        if run["device"]!=device:continue
                        effective = dict(usage)
                        if data.get("reference") is True and selected and engine=="openvino":
                            effective["parameters"]={**usage["parameters"],"context":1024}
                        entry = evaluate(session,run,current,effective)
                        if entry["eligible_for_ranking"]:
                            samples=[sample for sample in run["measurements"] if sample["phase"]=="measured" and sample["workload"]==profile]
                            performance=dict(entry["summary"])
                            preparation=run["environment"].get("preparation",{})
                            loading=[preparation[key] for key in ("read_model_ms","compile_ms","pipeline_load_ms") if isinstance(preparation.get(key),(int,float))]
                            performance["load_ms"]=sum(loading) if loading else None
                            cold=next((sample for sample in run["measurements"] if sample.get("session_cold") and sample["workload"]==profile),None)
                            performance["model_start_ms"]=sum(loading)+cold["latency_ms"] if loading and cold else None
                            entry["limitations"].append("Warm 延遲不含載入；模型啟動值僅包含已回報載入與首次推理，不含程序建立／IPC，OS 檔案快取未清空。")
                            for metric in ("ttft_ms","decode_tokens_per_s","peak_ram_bytes"):
                                values=[sample[metric] for sample in samples if sample.get(metric) is not None]
                                performance[metric]=(max(values) if metric=="peak_ram_bytes" else mean(values)) if values else None
                            entry["performance"]=performance
                        entries.append(entry)
                if incompatible:available,executable="incompatible",False
                candidates.append({"id":f"{runtime}|{engine}|{device}","runtime":runtime,"device":device,"engine":engine,
                    "model":model,"label":f"{record['label']} · {device}","availability":available,"executable":executable,
                    "network":network,"cost":record["cost"],"needs_consent":network,"reasons":reasons,"risks":risks,"uncertainty":unknown,
                    "resource":{"ram_estimate":required,"vram_estimate":vram_required,"memory_type":memory_type,
                                "physical_device":mapping.get("windows_id"),"ram_available":ram,"shared_memory_included_in_ram":True},
                    "identity":current,"evidence":entries})
        return recommend(candidates,preference=data.get("preference","auto"),objective=data.get("objective","latency"),usage=usage)

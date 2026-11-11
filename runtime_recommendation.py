"""Explain compatibility without submitting work or contacting providers."""
from runtime_contract import fresh, task_health
from resource_contract import fresh_measure, gpu_memory, memory_explanation, reading

PREFERENCES = {"auto","speed","low-memory","energy","privacy","local-first","cost"}


def recommend(candidates, *, preference="auto", objective="latency", usage=None):
    """Explain gates first, compare only qualified, condition-matched measurements."""
    if preference not in PREFERENCES or objective not in ("latency","ttft","decode"):
        raise ValueError("推薦偏好或效能目標無效。")
    results = []
    for original in candidates:
        item = {**original,"reasons":list(original.get("reasons",[])),"uncertainty":list(original.get("uncertainty",[])),
                "risks":list(original.get("risks",[])),"performance":None,"performance_group":None,
                "confidence":"unknown","evidence_level":"capability-only","recommended":False}
        if preference=="privacy" and item["network"]:
            item.update(availability="incompatible",executable=False)
            item["reasons"].append("隱私優先只允許本機，不傳送提示詞或工具結果。")
        if preference=="cost" and item["network"] and item["cost"]!="no-api-fee":
            item.update(availability="incompatible",executable=False)
            item["reasons"].append("節省費用排除可能計費或費用未知的端點。")
        if preference=="energy":
            item["uncertainty"].append("沒有可靠功耗資料，無法判定哪個設備最省電。")
        evidence = [entry for entry in item.get("evidence",[]) if entry["eligible_for_ranking"]]
        if evidence:
            entry = evidence[0]  # newest first, never cherry-pick the fastest run
            item.update(performance=entry.get("performance") or entry["summary"],performance_group=entry["condition_key"],
                        evidence_level="verified-benchmark" if entry["execution_device_verified"] else "backend-benchmark-limited",
                        confidence="limited" if entry["comparability"]!="equivalent" else "measured")
            item["uncertainty"].extend(entry["limitations"])
        elif item.get("evidence"):
            item["uncertainty"].append("歷史 Benchmark 已過期、不相容或證據不足，未用於效能排序。")
        else:
            item["uncertainty"].append("沒有此模型與工作量的 Benchmark，缺少資料不代表較慢。")
        if item["network"]:
            item["reasons"].append("只提供建議，實際傳送仍需此次任務的目的地與費用確認。")
        if item["cost"]=="unknown":
            item["uncertainty"].append("費用未知，不視為免費。")
        results.append(item)
    ready = [item for item in results if item["executable"] and item["availability"] in ("ready","uncertain")]
    # Default suggestions are local compatibility choices, not invented speed rankings.
    local = [item for item in ready if not item["network"]]
    pool = local or ready
    selected = next((item for item in pool if item["availability"]=="ready"),pool[0] if pool else None)
    comparison = None
    groups = {}
    field = {"latency":"mean_ms","ttft":"ttft_ms","decode":"decode_tokens_per_s"}[objective]
    for item in pool:
        performance = item["performance"] or {}
        if item["performance_group"] and isinstance(performance.get(field),(int,float)):
            groups.setdefault(item["performance_group"],[]).append(item)
    groups = [items for items in groups.values() if len(items)>1]
    if preference in ("auto","speed") and len(groups)==1:
        ordered = sorted(groups[0],key=lambda item:item["performance"][field],reverse=objective=="decode")
        selected = ordered[0]
        comparison = {"scope":"僅限指定模型與固定工作量、參數及 Backend。","objective":objective,
                      "ordered_candidates":[item["id"] for item in ordered],"condition_key":selected["performance_group"]}
        selected["reasons"].append("在同一固定 Benchmark 條件下，此指標較佳；不能代表其他提示詞或輸出長度。")
    if preference=="low-memory":
        measured = [item for item in pool if item["performance"] and item["performance"].get("peak_ram_bytes") is not None]
        if len(measured)>1 and len({item["performance_group"] for item in measured})==1:
            selected = min(measured,key=lambda item:item["performance"]["peak_ram_bytes"])
            selected["reasons"].append("相同 Benchmark 條件下，已量測的程序 RAM 工作集峰值較小；VRAM 未知時不推論總記憶體。")
        else:
            for item in pool:item["uncertainty"].append("缺少可比較的記憶體實測，僅檢查需求估計與容量。")
    if selected:
        selected["recommended"] = True
        if comparison is None:
            selected["reasons"].append("依相容性、可用性與本機優先提供建議，目前無法確定哪個設備最快。")
    return {"schema":1,"preference":preference,"objective":objective,"usage":usage,
            "recommended":selected["id"] if selected else None,"comparison":comparison,"candidates":results,
            "automatic_dispatch":False,"benchmark_started":False,
            "explanation":"推薦後由使用者選擇並確認；未比較的候選沒有被視為較慢。"}

TASK_FORMAT = {"chat": "GGUF", "agent": "GGUF", "team": "GGUF", "image": "safetensors",
               "video": "safetensors", "music": "safetensors", "notebook": None}


def compare(record, task, model, *, ram=None, vram=None, policy="auto", now=None, installable=False):
    reasons, risks, unknown = [], [], []
    incompatible = install = connect = False
    local = record["kind"] == "local"
    openvino = record["provider"] == "OpenVINO"
    network = record["network"] is True
    cost = record["cost"]
    if task not in record["tasks"]:
        incompatible = True
        reasons.append("這個環境沒有宣告支援此任務。")
    if network and policy in ("local", "privacy"):
        incompatible = True
        reasons.append("目前偏好限制資料留在本機。")
    if network and policy == "cost" and cost != "no-api-fee":
        incompatible = True
        reasons.append("節省費用偏好會排除可能收費或費用未知的環境。")
    if network and (record["connected"] is not True or not fresh(record, now)):
        connect = True
        unknown.append("需要重新連線或更新能力資料。")
    image = record.get("media",{}).get("image") if task=="image" and not local else None
    if image and image["state"]!="ready":
        risks.append("遠端 ComfyUI 或圖片權重尚未就緒。")
    health = task_health(record, task)
    if health in ("unhealthy", "offline"):
        risks.append("運算環境目前無法穩定接收工作。")
    elif health == "busy":
        risks.append("運算環境正在工作，可能需要排隊。")
    elif health == "unknown":
        unknown.append("運算環境健康狀態未知。")
    elif health == "setup":
        install = local
        risks.append("此環境尚未完成設定。")
    if local and task in record["tasks"]:
        engine = "OpenVINO" if openvino else "ComfyUI" if task in ("image", "video", "music") else "llama.cpp"
        if engine not in record["engines"]:
            install = True
            reasons.append(f"需要安裝 {engine}。")
    if model and task in record["tasks"]:
        format = "OpenVINO IR" if openvino else TASK_FORMAT[task]
        # External model IDs do not establish an underlying weight format.
        if format and record["formats"] and format not in record["formats"]:
            incompatible = True
            reasons.append(f"此環境未宣告支援 {format}。")
        if image:
            if model in image["workflows"]:
                reasons.append("遠端主機已列出此圖片流程。")
            elif not connect:
                incompatible = True
                reasons.append("遠端主機沒有此圖片流程。")
        elif local and format == "safetensors":
            unknown.append("創作權重是否可用，請以 ComfyUI 的預檢為準。")
        elif model not in record["models"]:
            if connect:
                unknown.append("連線或清單已過期，暫時無法確認模型。")
            elif local and installable:
                install = True
                reasons.append("這個模型可以下載。")
            else:
                incompatible = True
                reasons.append("這個環境目前沒有該模型，無法從這裡安裝。")
        else:
            reasons.append("已在運算環境的模型清單中找到此模型。")
    elif task != "notebook":
        unknown.append("尚未選擇要比較的模型。")
    if ram is not None or vram is not None:
        for requirement, key, label in ((ram, "ram_available", "RAM"), (vram, "vram_available", "VRAM")):
            if requirement is None:
                continue
            value = record["resources"][key]
            available = value["value"]
            if key=="vram_available":
                _, measured = gpu_memory(record.get("hardware"),now)
                available = measured["value"] if measured else None
                if available is None:
                    unknown.append(memory_explanation(record.get("hardware"),now))
            elif value.get("checked_at") is not None and not fresh_measure(value,now):
                available = None
            if available is None or connect:
                unknown.append(f"可用 {label} 未知。")
            elif available < requirement:
                risks.append(f"可用 {label} 低於目前的需求估計。")
            else:
                reasons.append(f"回報的可用 {label} 達到目前估計，實際載入仍需由後端驗證。")
    elif local or record["kind"] == "remote-host":
        unknown.append("這個模型的 RAM／VRAM 門檻未經驗證。")
    if cost == "unknown":
        unknown.append("費用未知。")
    elif cost == "may-charge":
        risks.append("可能產生費用。")
    if network:
        reasons.append("送出前須手動選擇並同意對外傳送。")
    state = ("incompatible" if incompatible else "needs-setup" if connect or install else
             "uncertain" if risks or unknown else "compatible")
    return {"id": record["id"], "label": record["label"], "state": state, "recommended": state == "compatible",
            "requirements":{"ram":reading(ram,"estimated",unit="bytes"),"vram":reading(vram,"estimated",unit="bytes")},
            "inference_verified":False,"benchmark_verified":False,
            "reasons": reasons, "risks": risks, "unknown": unknown, "needs_install": install, "needs_connection": connect,
            "needs_consent": network, "may_charge": None if cost == "unknown" else cost == "may-charge"}

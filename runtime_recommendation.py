"""Explain compatibility without submitting work or contacting providers."""
from runtime_contract import fresh, task_health
from resource_contract import fresh_measure, gpu_memory, memory_explanation, reading

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

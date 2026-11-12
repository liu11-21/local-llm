"""Derive first-use choices from actual local inventory and saved capabilities."""
from hardware import estimate_ram
from media import DEFAULT_WORKFLOWS
from runtime_contract import fresh, task_health
from runtime_provider import route

TASKS = {"chat", "agent", "team", *DEFAULT_WORKFLOWS}


def onboarding_plan(info, capabilities, task, policy):
    if task not in TASKS:
        raise ValueError("請選擇有效的入門任務。")
    if task in DEFAULT_WORKFLOWS:
        choices = []
        for record in capabilities:
            media = record.get("media", {}).get('audio' if task=='music' else task, {})
            if (record["kind"] != "remote-host" or task not in record["tasks"] or not record["connected"]
                    or not fresh(record) or media.get("state") != "ready" or not media.get("workflows")
                    or task_health(record,task) not in ("ready","busy")):
                continue
            try:
                route(policy, record["id"], True, paired=True)
            except ValueError:
                continue
            choices.append({"runtime":record["id"],"label":record["label"],"model":media["workflows"][0],
                            "reason":"已配對主機的創作流程已就緒，無需下載本機權重。送出前須核對目的地。",
                            "actions":[]})
        choices.append({"runtime":"local", "label":"本機 ComfyUI", "model":DEFAULT_WORKFLOWS[task],
                        "reason":"在創作頁檢查權重、節點與資源，並準備缺少的項目。", "actions":[]})
        return {"choices":choices,"media":True}
    local = info["hardware"]
    choices = []
    models = sorted(info["registry"]["models"], key=lambda item: (
        local["ram_available"] is not None and item["ram"] > local["ram_available"], item["bytes"]))
    for item in models[:2]:
        choices.append({"runtime":"local", "label":item["label"], "model":item["id"],
                        "bytes":item["bytes"], "ram":item["ram"],
                        "reason":"模型已安裝。可在本機使用，無需下載權重。",
                        "actions":[] if info["engine"] else [{"action":"engine-install","data":{}}]})
    if not models:
        suitable = [item for item in info["recommended"] if item["fit"] not in ("記憶體不足","磁碟空間不足")]
        suitable.sort(key=lambda item: (item["fit"] != "適合", "中文" not in item["description"], item["size"]))
        for item in suitable[:2]:
            actions = [] if info["engine"] else [{"action":"engine-install","data":{}}]
            actions.append({"action":"download","data":{"url":item["url"],"workers":4}})
            choices.append({"runtime":"local", "label":item["repo"].split("/")[1].removesuffix("-GGUF"),
                            "model":item["name"], "bytes":item["size"], "ram":estimate_ram(item["size"]),
                            "reason":item["description"] + "。CPU 可用，記憶體需求為估計。",
                            "actions":actions})
    for record in capabilities:
        if (record["kind"] != "remote-host" or task not in record["tasks"] or not record["models"]
                or not record["connected"] or task_health(record,task) not in ("ready","busy") or not fresh(record)):
            continue
        try:
            route(policy, record["id"], True, paired=True)
        except ValueError:
            continue
        choices.append({"runtime":record["id"], "label":record["label"], "model":record["models"][0],
                        "reason":"使用已配對主機。送出提示詞前仍需確認目的地。", "actions":[]})
        break
    return {"choices":choices, "media":False}

"""Colab Enterprise jobs for an existing Google Cloud project."""
import http.client
import json
import re
from urllib.parse import urlencode
from uuid import uuid4

PROJECT = re.compile(r"(?:[a-z][a-z0-9-]{4,28}[a-z0-9]|[0-9]{6,20})")
REGION = re.compile(r"[a-z]+(?:-[a-z0-9]+)+[0-9]")
BUCKET = r"[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]"
TEMPLATE = re.compile(r"projects/[^/]+/locations/([^/]+)/notebookRuntimeTemplates/[a-zA-Z0-9_-]+")


class ColabAdapter:
    def __init__(self):
        self.project = ""
        self.region = ""
        self.token = ""
        self.templates = {}

    def capabilities(self):
        return {"kind": "colab", "available": bool(self.token), "requires_authorization": True,
                "project": self.project, "region": self.region, "tasks": ["notebook"],
                "templates": list(self.templates.values())}

    def connect(self, project, region, token):
        if (not PROJECT.fullmatch(project) or not REGION.fullmatch(region) or len(region) > 32 or
                not 20 <= len(token) <= 4096 or not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", token)):
            raise ValueError("請輸入有效的 Google Cloud 專案、區域及 OAuth 存取權杖。")
        pending = ColabAdapter()
        pending.project, pending.region, pending.token = project, region, token
        items = pending.request("GET", "notebookRuntimeTemplates", query={"pageSize": 50})
        for item in items.get("notebookRuntimeTemplates", []):
            name = item.get("name", "")
            match = TEMPLATE.fullmatch(name)
            if match and match[1] == region:
                machine = item.get("machineSpec") or {}
                pending.templates[name] = {
                    "name": name, "label": item.get("displayName") or name.rsplit("/", 1)[-1],
                    "machine": machine.get("machineType", ""), "gpu": machine.get("acceleratorType", ""),
                    "count": machine.get("acceleratorCount", 0),
                }
        self.project, self.region, self.token = project, region, token
        self.templates = pending.templates
        return self.capabilities()

    def request(self, method, resource, payload=None, *, query=None):
        if not self.token:
            raise ValueError("請先連線至自己的 Colab Enterprise 專案。")
        url = f"/v1/projects/{self.project}/locations/{self.region}/{resource}"
        if query:
            url += "?" + urlencode(query)
        connection = http.client.HTTPSConnection(f"{self.region}-aiplatform.googleapis.com", timeout=15)
        try:
            connection.request(method, url, json.dumps(payload).encode() if payload is not None else None,
                               {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
            with connection.getresponse() as response:
                if response.status in (401, 403):
                    raise ValueError("Google 拒絕授權。請更新存取權杖，並核對 IAM 權限及 API 啟用狀態。")
                if not 200 <= response.status < 300:
                    raise ValueError(f"Google Cloud 回傳 HTTP {response.status}。請檢查專案、區域及配額。")
                raw = response.read(2 * 1024 ** 2 + 1)
                if len(raw) > 2 * 1024 ** 2:
                    raise ValueError("Google Cloud 回應超出工作台的大小限制。")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError("Google Cloud 回應格式不符。")
                return result
        finally:
            connection.close()

    def list_jobs(self):
        data = self.request("GET", "notebookExecutionJobs", query={"pageSize": 30})
        return [
            {"name": row.get("name"), "label": row.get("displayName"), "state": row.get("jobState"),
             "output": row.get("gcsOutputUri"), "created": row.get("createTime")}
            for row in data.get("notebookExecutionJobs", [])
        ]

    def submit(self, template, source, output, account, confirmed):
        if confirmed is not True:
            raise ValueError("請先確認 Notebook、執行身分與可能的 Google Cloud 費用。")
        if template not in self.templates:
            raise ValueError("請從已連線專案選擇執行範本。")
        if not re.fullmatch(rf"gs://{BUCKET}/[^\s?#]+\.ipynb", source):
            raise ValueError("請提供既有的 Cloud Storage .ipynb 網址。")
        if not re.fullmatch(rf"gs://{BUCKET}", output):
            raise ValueError("請填入既有的 Cloud Storage 輸出 bucket。")
        if not re.fullmatch(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com", account):
            raise ValueError("請填入有權讀取 Notebook 並寫入輸出 bucket 的服務帳戶。")
        job_id = f"local-llm-{uuid4().hex[:16]}"
        payload = {
            "displayName": job_id,
            "gcsNotebookSource": {"uri": source},
            "gcsOutputUri": output,
            "serviceAccount": account,
            "notebookRuntimeTemplateResourceName": template,
            "executionTimeout": "900s",
        }
        try:
            result = self.request("POST", "notebookExecutionJobs", payload,
                                  query={"notebookExecutionJobId": job_id})
        except (OSError, http.client.HTTPException):
            raise ConnectionError(f"Google Cloud 連線中斷。請先查詢 {job_id} 是否已建立，再決定是否重試。") from None
        return {"id": job_id, "operation": result.get("name"), "output": output}

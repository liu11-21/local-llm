"""Stable recovery guidance for synchronous IPC and asynchronous task failures."""
import re
import ssl
from urllib.error import HTTPError, URLError


def redact(text):
    text = re.sub(r'(?i)(Bearer\s+)[^\s,;\"\']+', r'\1[redacted]', str(text))
    text = re.sub(r'(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;\"\']+', r'\1[redacted]', text)
    return re.sub(r'(https?://[^\s?\"\']+)\?[^\s\"\']+', r'\1?[redacted]', text)[:1500]


def explain(error):
    detail = redact(str(error).strip() or type(error).__name__)
    lower = detail.lower()
    code, summary, recovery = 'WORK_FAILED', '工作無法完成。', '請查看任務詳情，確認設定後手動重試。'
    if getattr(error, 'winerror', None) == 4551 or '0xc0e90002' in lower:
        code, summary, recovery = 'POLICY_BLOCKED', 'Windows 應用程式控制阻擋了引擎。', '請查看系統事件與發行來源；保留安全政策，改用允許的 Runtime。'
    elif isinstance(error, ssl.SSLError) or any(word in lower for word in ('certificate','憑證','fingerprint','指紋')):
        code, summary, recovery = 'TLS_VERIFY_FAILED', '遠端憑證驗證失敗。', '請核對 Host 憑證指紋及系統時間，必要時重新配對；不要略過 TLS 驗證。'
    elif isinstance(error, PermissionError) or getattr(error,'code',None) in (401,403) or '權限' in detail or 'TEAM_EXTERNAL_NOT_GRANTED' in detail:
        code, summary, recovery = 'ACCESS_DENIED', '沒有執行這項工作的權限。', '請確認檔案權限、API 金鑰或 Host 配對與任務擁有者。'
    elif isinstance(error, TimeoutError) or 'timeout' in lower or '逾時' in detail:
        code, summary, recovery = 'TIMEOUT', '工作等候超過時間上限。', '請到任務中心確認原工作狀態；遠端任務不要直接重送，可先查詢或恢復下載。'
    elif '下載中斷' in detail:
        code, summary, recovery = 'DOWNLOAD_INTERRUPTED', detail, '已保留可恢復的下載資料，請檢查網路後從原任務重試下載。'
    elif getattr(error,'errno',None)==28 or '磁碟空間' in detail:
        code, summary, recovery = 'DISK_FULL', '磁碟空間不足，工作尚未完成。', '請釋出空間並保留原檔及下載片段，再從原任務重試。'
    elif any(word in lower for word in ('sha-256','sha256','校驗','損毀','corrupt')):
        code, summary, recovery = 'INTEGRITY_FAILED', '檔案完整性檢查失敗。', '請核對來源與磁碟，從下載頁恢復或重新下載；未驗證的檔案不會使用。'
    elif any(word in lower for word in ('ram','vram','out of memory','記憶體不足','顯存不足','安全容量')):
        code, summary, recovery = 'RESOURCE_LIMIT', '目前記憶體或顯存無法安全容納工作。', '請選較小模型、降低參數或等候其他任務結束，再檢查運算建議。'
    elif any(word in lower for word in ('不相容','unsupported','格式不符')):
        code, summary, recovery = 'INCOMPATIBLE', '模型、格式或 Runtime 不相容。', '請選擇支援這個任務及模型格式的 Runtime，並檢查工作流程準備狀態。'
    elif isinstance(error, FileNotFoundError) or any(word in lower for word in ('找不到','未安裝','不存在')):
        code, summary, recovery = 'NOT_INSTALLED', '必要的模型、引擎或檔案不存在。', '請在模型與應用或運算環境準備所需項目，更新清單後重試。'
    elif isinstance(error, (ConnectionError, URLError)) or any(word in lower for word in ('offline','離線','連線中斷','連線失敗')):
        code, summary, recovery = 'CONNECTION_LOST', '無法連線至運算來源。', '請確認網路與 Host 健康狀態；已提交的工作先查詢原 Job，避免重複生成。'
    elif '455' in lower and 'winerror' in lower:
        code, summary = 'ENGINE_START_FAILED', '引擎無法啟動。'
    elif isinstance(error, (ValueError, RuntimeError, InterruptedError)) and re.search(r'[\u4e00-\u9fff]', detail):
        summary = detail
    return {'code':code, 'summary':summary, 'recovery':recovery, 'detail':detail}


def user_message(info):
    return f"{info['summary']} {info['recovery']}"[:1500]

# 0.9.0 Desktop Retest — Session / Launcher

日期：2026-11-17（Asia/Taipei）。分支 dev/web-workspace，版本維持 0.9.0 Development。
基準產品 fe2a363；開始 checkout a7edf98，乾淨。沒有修改 main、Stable v0.6.2、Desktop 分支。

## P0 / P1

**PASS**：已修改程式，根因與修正檔案見 [Session Recovery](SESSION_RECOVERY_REPAIR.md)、[Python Launcher](PYTHON_LAUNCHER_REPAIR.md)。
修復前 fe2a363 的同頁 Session 卡死已用 Chrome／真 HTTP 重現；修復後已驗證重新初始化，不放寬 CORS／CSRF／Origin／Host。
新增 logout 與同源分頁狀態同步、port Cookie 隔離，SSE 連回既有任務且不重送寫入。
Start／Stop 等腳本共用實際版本／64-bit 檢查的 Python 選取器，保留官方簽章檢查。

| 驗收 | 狀態 |
|---|---|
| 實際 Windows 開發主機 | **PASS**：官方 Python 3.12.10 x64；Start／Stop CMD、重啟、清理、PATH／Registry 備援 |
| 真 Session / Chrome | **PASS**：初啟、reload、同頁重啟、期限過期、重新驗證、跨分頁、logout 清 Cookie、模型庫入口 |
| SSE / Cancel | **PASS**：真 HTTP、控制等待工作的 TaskManager，重連與取消；不是 AI 推理 |
| 安全邊界 | **PASS**：Session、CSRF、127.0.0.1、Origin／Host、DNS rebinding、未授權及跨來源寫入拒絕 |
| 資料保留 | **PASS**：自建合成資料的 SQLite hash 與作品／模型標記／Runtime 設定；沒有清空使用者資料庫 |
| Runtime 實機套件完整複測 | **NOT TESTED**：本輪未修改 Runtime 模組，不重做已通過的真安裝偵測／驗簽／設備列舉 |
| 使用者指定 QA 資料 | **BLOCKED**：D:\codex\local llm\LocalLLM-Web-QA-1115 不存在於目前主機；沒有寫入或重建該資料庫 |

測試 JSON：[Session](evidence/session-recovery/SESSION_RECOVERY_TESTS.json)、[Launcher](evidence/session-recovery/PYTHON_LAUNCHER_TESTS.json)。
控制 fixture 只用來測試錯誤／等待工作，真 HTTP／瀏覽器／CMD 已另實跑，沒有用 fixture 宣稱 GPU 可用。

## P2

**BLOCKED**：目前主機為 Intel Iris Xe，沒有 RTX 5070 Ti；指定 QA 目錄及 Qwen3-4B-Q4_0.gguf 也不可取得。
未下載替代 Runtime／模型，未以 Qwen3-0.6B、獨立 PowerShell 或歷史推理冒充本輪目標 GPU 驗收。

Workspace 模型匯入／載入、RTX Vulkan 繁中回答、Thinking ON/OFF、生成 SSE、取消／重新生成、Benchmark 三次及 VRAM／RAM：**NOT TESTED（受上述 BLOCKED 限制）**。
下一步是在原 RTX 桌機以新版 ZIP 啟動、重新驗證 Session，保留原 QA 資料，再依序做上述 P2；不需要重新安裝已驗證的 Runtime。

## 交付

本機單元、TypeScript／Vite 與完整 Chromium 已執行；Windows CI、最終 Commit、Artifact、SHA 在 CI 完成後補入此節。
沒有建立正式 Release／Tag，沒有更改 Windows 安全政策或防毒、簽章／憑證方案。

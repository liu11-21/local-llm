# 0.9.0 Desktop Retest — Session / Launcher

日期：2026-11-17（Asia/Taipei）。分支 dev/web-workspace，版本維持 0.9.0 Development。
基準產品 fe2a363；開始 checkout a7edf98，乾淨。沒有修改 main、Stable v0.6.2、Desktop 分支。

**PASS（維護者提供，本輪沿用）**：原 Artifact／manifest、官方 llama.exe 自動偵測／Hugging Face 簽章／CLI、
Runtime 選取及保存、RTX 5070 Ti／Intel Graphics Vulkan 列舉、API 防護與停止清理已由維護者確認。
本輪沒有把這些項目重標成失敗，也沒有重做整套真 Runtime 驗收；下方測試均標明本輪實際範圍。

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

修復提交：[`6bd567d`](https://github.com/liu11-21/local-llm/commit/6bd567d98ad7b15088a81dc40429955afb6c74ca)，
以及禁止 probe 自動安裝 Python 的 [`524b1f9`](https://github.com/liu11-21/local-llm/commit/524b1f9500ede507b5041dbab0b6b0282ec9bdd7)。
**最終 ZIP 產品來源為 524b1f9**。後續報告／下載連結／驗收腳本來源 metadata 的提交不變更本包產品程式。

| 最終項目 | 結果 |
|---|---|
| Windows CI | **PASS**：[44056914092](https://github.com/liu11-21/local-llm/actions/runs/44056914092)，19 個步驟成功 |
| Windows Python | **PASS**：264 tests，263 通過，僅 Desktop 封裝 EXE smoke 1 項略過；遠端 TLS 未略過 |
| 本機 Python | **PASS（有限範圍）**：初輪完整 262 tests、8 略過（既有 TLS 攔截 7 項＋Desktop EXE 1 項）；最終涉及變更的 21 項全部通過。最終完整 264 項由上述乾淨 CI 驗證 |
| TypeScript／Vite | **PASS**：Web production build；既有大 bundle 提示仍存在 |
| 完整 Chromium | **PASS**：Agent／Team／Benchmark／遠端及既有 Runtime 受控案例；不當作 GPU 實機測試 |
| Chrome／Edge HTTP | **PASS**：四尺寸、雙主題、12 頁、跨視窗與 restart；匯入是合成 GGUF header fixture，不是 Qwen3-4B |
| 全新 ZIP／升級／回滾 | **PASS**：官方 Python、純依賴驗證、真 0.8 來源升級、重複啟動、資料保留、停止／更新／回滾 |
| 最終 GitHub ZIP 的本機再驗證 | **PASS**：外層 GitHub digest、內層 SHA、BUILD Commit、437 個 manifest 檔案、兩個 CMD helper；PE／模型 payload 為 0 |
| 同一 GitHub ZIP／含空格路徑 | **PASS**：真 Start／Stop CMD、restart、PATH／Registry 備援、服務退出及 port 釋放；真 Chrome Session／SSE／cancel／跨分頁與 logout |
| 原 SDK 設定保存 | **PASS（本機）**：既有 SDK 的已保存設定 byte-for-byte 保留，不重新跑 Runtime CLI。CI 無 SDK 時此特定項明確 **NOT TESTED**，沒有冒充通過 |
| 目標 RTX QA／SAC／Qwen3-4B | **BLOCKED**：目前主機無目標硬體、目錄與模型；本輪 P2 全部 **NOT TESTED** |

[下載 Windows x64 Web Artifact](https://github.com/liu11-21/local-llm/actions/runs/44056914092/artifacts/14315909098)
（可能需登入 GitHub，保留 14 天）。外層解開後有真正的 Web ZIP、BUILD、SHA256SUMS、Python／部署／瀏覽器與 Session／Launcher JSON。

內層 `LocalLLM-Web-0.9.0-Windows-x64.zip`，1,583,127 bytes，SHA-256：

```text
56590bbfdbea08273567b4f5a1e455f4eafd82207e34ff2b330003e7bfccb673
```

GitHub 外層 Artifact ZIP SHA-256（不是更新命令所用的內層雜湊）：

```text
235b2554abed52c85377744053a54f30e0f80ab04b6500830ed57c97986ebdcd
```

[產物雜湊證據](evidence/session-recovery/ci-artifact.json)；本機最終同包實測的兩份 JSON 含 `package_build.commit=524b1f9...`。
CI 原始兩份 JSON 保存在 Artifact 與 [CI Session](evidence/session-recovery/CI_SESSION_RECOVERY_TESTS.json)、[CI Launcher](evidence/session-recovery/CI_PYTHON_LAUNCHER_TESTS.json)。
ZIP 內報告為建置前快照，最終 SHA／CI 結果以此 Repository 報告及外部 BUILD／SHA256SUMS 為準，不把 ZIP 自身雜湊寫回 ZIP。

## 原桌機下一步

先停止原服務，把新版解壓到另一個程式目錄，使用原本的 `--data` 參數或原預設資料目錄啟動。
`D:\codex\local llm\LocalLLM-Web-QA-1115` 是維護者提供的 QA 目錄，並未在此主機確認它是程式目錄或真正 SQLite 所在；
不要直接把解壓目錄當成資料目錄，也不要重建資料庫。
再次執行 Start 可取得目前服務的 127.0.0.1 登入連結；其他同源分頁會恢復。
確認 Session／模型庫／聊天可進入後，再沿用已驗證的 Runtime 與既有 Qwen3-4B 做 P2 GPU 驗收。

沒有建立正式 Release／Tag，沒有更改 Windows 安全政策或防毒、簽章／憑證方案。

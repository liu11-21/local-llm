# Local LLM 0.9.0 Web Workspace — 交付

基準 0.8.0 `90af62b`，工作分支 dev/web-workspace；不改 main、Stable v0.6.2、Desktop 分支，不建立 Release／Tag。
停止推進 SignPath／憑證；保留 Tauri 原始碼與已核准第一方 MIT，第三方／素材範圍不變。

已實作：共用 WorkspaceApplication 與 IPC／HTTP Transport、同源驗證／CSRF／Host／Origin、SSE／取消、
原排程與核心功能、官方 Runtime 簽章與內容 pin、GGUF 匯入、作品下載／Range、Benchmark 匯出、
服務管理與閒置／子程序保護、官方 Python 啟動器、純 Python 固定依賴、ZIP 更新／回滾、PWA。

首階段提交 `d65421b`；[真實原型](evidence/v090/prototype-real.json) 使用官方簽章 Python／llama.exe，
Qwen3-0.6B 真實繁體 HTTP／SSE、取消、SQLite、React 與關閉清理通過。
基本聊天沒有 cryptography import，沒有執行自製 EXE；Uvicorn／h11／click／colorama 精確 SHA 見鎖定檔。

事後另將 **同一個最終 CI ZIP** 解壓，以其官方 Python 啟動流程跑完真實工作鏈，
服務握手的 `application_build.commit` 精確為 78f8f7c：
[完整原生結果](evidence/v090/native-final-zip.json)、[CPU／Intel Vulkan 原始 Benchmark](evidence/v090/benchmark-final-zip.json)、
[Chrome 真實聊天](evidence/v090/chrome-chat-real.json)、[畫面](ui-preview/v090/web-chat-real.png)。
這次原生與簡易 Agent 均有真正 models 工具 request／result 審計、Team 四節點及整合回答已保存，
Thinking ON／OFF、實際串流後取消、取消回答不入庫與關閉清理均通過。
原生 Agent 回答可帶小模型產生的控制標記雜訊，功能驗收不等於輸出品質保證。

## 版本與提交

| Commit | 範圍 |
|---|---|
| d65421b | 0.9.0 基準、共用應用邊界、HTTP／SSE 最小原型與真實推理 |
| f44b516 | 完整 Web transport、檔案／服務管理、官方 Python 啟動器、純 wheel 環境、ZIP／更新／回滾及 CI |
| b332fc9 | Windows 合法 DOS 短路徑正規化、實際連結仍拒絕；新增回歸 |
| e4fc3bd | 聊天裝置／上下文選單的明確無障礙名稱；Chrome 真實聊天驗證 |
| 78f8f7c | 官方 Python 精確 CN／O 發行者比對與負例回歸；最終候選程式來源 |

最終安裝候選來源 **`78f8f7c10d2c0a9c3bedce6868a2d7093e992d2f`**。
後續文件／證據／選用驗收工具提交不改變這個 ZIP。ZIP 內文件是建置當時快照，事後驗收與雜湊以本文件為準。

## 下載與首次啟動

[Windows x64 Web Workspace Artifact](https://github.com/liu11-21/local-llm/actions/runs/43685022914/artifacts/14150375872) ·
[最終 CI Run 43685022914](https://github.com/liu11-21/local-llm/actions/runs/43685022914)，**SUCCESS／18 steps**。
Actions 可能需要登入 GitHub，保留 14 天，未建立正式 Release／Tag。

1. 安裝官方 Python 3.12 x64（3.12.10 或較新 3.12，保留 Launcher）。
2. 解開 Artifact，取出 **`LocalLLM-Web-0.9.0-Windows-x64.zip`** 並完整解壓。
3. 雙擊 **Start-Web-Workspace.cmd**，瀏覽器自動開啟；不需 Node／Rust／自製 Worker EXE。
4. 到運算環境確認選擇官方已簽章 llama.exe，再匯入 GGUF 或使用 HF 下載。

Web ZIP：1,550,067 bytes；包含應用原始碼、預建 React、四個未修改的純 Python wheels、鎖定檔、Notices、manifest 與啟動／管理腳本。
不含 EXE／DLL／PYD／模型權重。官方 Python 本身仍有原生標準庫元件；Web ZIP 零 PE 不等於所有執行依賴已通過 SAC。

內層 Web ZIP SHA-256（也是 Update 腳本要求的值）：

`9649c947035f8547965035925542b2462859bfdab0c4fd5a805a58b31fe2b94d`

GitHub 下載的外層 Artifact ZIP SHA-256：

`5fad32c35c61d49bea8df643a62170329af065f0428a64264114add2cdadb280`

已核對 GitHub artifact digest、BUILD 來源／版本、內層 ZIP／SHA256SUMS 與內容 manifest。
這是來源／完整性核對，沒有 Windows 程式碼簽章或 SignPath 保證。
[核對記錄](evidence/v090/candidate-verification.json) · [BUILD](evidence/v090/BUILD.json) ·
[CI 步驟與原始測試計數](evidence/v090/windows-ci-validation.json) · [ZIP 部署](evidence/v090/DEPLOYMENT.json) ·
[0.8 升級前](evidence/v090/UPGRADE-BEFORE.json) · [升級後](evidence/v090/UPGRADE-AFTER.json) ·
[Chrome／Edge 矩陣](evidence/v090/BROWSER-TESTS.json)。
[文件／去識別資料／內外 ZIP／430 個 manifest 檔案／無 PE 與 MIT 範圍的最後核對](evidence/v090/documentation-validation.json) PASS。

## 驗收結果與界線

| 範圍 | 結果 |
|---|---|
| Python | 最終乾淨 Windows **235 項，234 通過、1 skipped**。唯一 skip 是未建置的自製封裝 Worker；Web 不執行或需要它。本機原有 7 個 TLS 限制案例在 CI 全實跑。 |
| 共用核心／Desktop | 完整既有 UI／IPC、Agent／Team、ComfyUI／OpenVINO、Remote 媒體、作品、推薦、版本混搭拒絕回歸通過；受控協定／媒體測試不冒充模型生成。 |
| Chrome／Edge | 實際解壓 ZIP 啟動 HTTP 服務；兩種瀏覽器各跑四尺寸×深淺模式×12 頁，16 組矩陣；GGUF 匯入、多視窗同步、PWA manifest／service worker 就緒、停止／重啟保留檔案 PASS。 |
| 資料升級 | 真正 `90af62b` 0.8.0 Python Worker 初始化資料，加入合成使用者資料，再由 Web ZIP 啟動升級；18 表／檔案指紋、校驗備份、保留模型／作品及 minimum_reader 0.8.0 PASS。未用手改版號假裝舊版。 |
| 更新／回滾 | 實際候選 ZIP 的 SHA／manifest、另一版本目錄啟動、切回先前指標及資料保留 PASS；拒絕錯誤 hash／zip-slip／不允許的執行檔。 |
| 本機安全 | Session／CSRF、Origin／Host／DNS rebinding、大小／方法／JSON、檔案範圍／不覆蓋、停止確認及信任負例回歸 PASS；Windows 強制結束測試父 Host 後，其官方 Python 子程序被 Job Object 回收。 |
| 真實模型 | 官方 Python／llama.app Valid、Qwen3 Thinking、SQLite、簡易／原生 Agent、混合 Team、CPU／Intel Vulkan Benchmark、Chrome 表單與 SSE、開始生成後取消分別記錄於下方實機證據；模型選擇與品質不作保證。 |

第一次 CI 發現合法 8.3 TEMP 路徑誤判後已修正；最後三個程式候選 CI 均通過，僅以上最終 SHA 作本次下載。
保留原有 bundle-size 建議警告。沒有為 Web 建置 Rust／PyInstaller／NSIS EXE；保留的 Tauri 原始碼與版本一致性有檢查，不宣稱重新驗收新的 Desktop 二進位檔。

## 主要修改位置

共用邊界：[workspace_core.py](../workspace_core.py)、[desktop_worker.py](../desktop_worker.py)。
HTTP／SSE／檔案：[workspace_web.py](../workspace_web.py)、[web_files.py](../web_files.py)。
啟動／環境／更新：[web_launcher.py](../web_launcher.py)、[web_environment.py](../web_environment.py)、
[web_update.py](../web_update.py)、[web_optional.py](../web_optional.py)、[web_process_guard.py](../web_process_guard.py)。
前端：[transport.ts](../desktop/src/transport.ts)、[WebService.tsx](../desktop/src/WebService.tsx)、App／Chat／ModelLibrary／Creation／Benchmark／Runtime／Settings；沿用原樣式與 Logo。
發行：[build_web_workspace.py](../build_web_workspace.py)、[CI](../.github/workflows/web-workspace.yml)、[部署驗收](../web_smoke.py)、
[選用真實模型工具](../web_native_acceptance.py)。RuntimeManager／遠端 TLS 延後原生依賴，SQLite schema 不重寫。

## 尚未驗證／限制

**NEEDS HARDWARE**：RTX 5070 Ti／4B 本輪重測、CUDA、NPU、其他／多 GPU、實體兩機 Remote、完整影音模型 GPU 生成。
**NEEDS AUTH**：付費雲端／Colab；未呼叫付費 API。
**NOT VERIFIED**：SAC／WDAC 啟用模式下全部 Python／腳本／DLL／PYD 的相容性、各防毒產品、PWA 互動式 OS 安裝。
維護者另一台已簽章 llama.exe／RTX／SAC 的觀察保留為來源明確的既有基準，不代替本輪完整鏈驗收。

0.6B 量化模型的原生工具選擇有波動，曾未選工具或達到核准步數／Token 上限；失敗／部分結果如實記錄，不修改核准與限制來假裝成功。
[觀察界線](evidence/v090/model-observation-boundary.json) 不將不同提示／條件的實驗轉為模型成功率。
正式模型品質、多語言服從度、所有模型 template、雲端供應商與瀏覽器擴充／同帳戶惡意程式不在已驗證範圍。
基本聊天不需 cryptography／zstandard；應用內 Runtime 下載需選用 zstandard，私人 TLS Host 需選用 crypto；其原生檔仍可能受政策阻擋。

使用者仍需：安裝／確認官方 Python、選擇官方 Runtime、下載或匯入自己的模型，及對雲端／工具／遠端提供當次必要核准。
停止服務與背景回收方式見安裝文件；不需要審批簽章方案，沒有申請 SignPath、付費憑證或降低 Windows 政策。

[架構](WEB_ARCHITECTURE.md) · [首次安裝](WEB_INSTALLATION.md) · [安全](WEB_SECURITY.md) · [相容性](WEB_COMPATIBILITY.md)

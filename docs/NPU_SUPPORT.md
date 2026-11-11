# GPU／NPU 支援範圍

## E3-A、E3-B 的目前能力

版本 0.6.2，基準 `14a8fff`。本輪完整交付 E3-A、E3-B。OpenVINO Runtime 2025.4.1、GenAI／Tokenizers 2025.4.1.0、Python 3.12.10 固定於獨立環境，依賴下載 84,376,901 bytes，安裝前要求 600 MiB 可用空間。模型另外匯入，最多 8 GiB，輸入與輸出有大小限制。

| 範圍 | 狀態與證據 |
|---|---|
| Windows GPU／RAM 資源契約 | 已支援。含單位、來源、時間、狀態、證據。共享上限、專用餘量估計及後端池容量分列，未知類型或過期資料不作確定容量判斷 |
| Intel OpenVINO Adapter | 已實作。可選安裝、移除、裝置查詢、匯入校驗、指定裝置、推理、取消、逾時及程序釋放，沿用 TaskManager |
| OpenVINO IR 張量模型 | 真實 CPU／Intel GPU 推理通過，驗證固定輸出及 `EXECUTION_DEVICES`，記錄 profiling。這是功能驗收，尚未做跨模式 Benchmark |
| OpenVINO IR 文字模型 | 真實 CPU 文字串流、聊天和保存通過。需模型、Tokenizer、Detokenizer 的 XML／BIN 與 config.json。輸入上限 1024 Token，每次最多輸出 512 Token，採貪婪解碼 |
| Intel NPU | 已實作待硬體驗收，NEEDS NPU。本機 OpenVINO 回報 CPU、GPU，未回報 NPU。張量與文字流程均明確指定裝置，沒有隱式 AUTO 路由 |
| AMD／Qualcomm | 僅完成候選契約，沒有可執行 Adapter。原有 CPU、llama.cpp 和 ComfyUI 仍可使用 |
| ONNX／GGUF 匯入 | 這個 Adapter 尚未支援。既有 GGUF 繼續使用 llama.cpp。IR 轉換與權重量化由使用者另行準備 |
| 單模型 HETERO／智慧分工 | 尚未實作，E3-D。介面未提供可選模式 |

從「運算環境 → 使用本機 → 可選 OpenVINO 引擎」核對下載摘要，確認後安裝。按「檢查 OpenVINO 裝置」，展開「匯入相容模型」輸入既有 IR 資料夾。文字模型可按「使用 OpenVINO 聊天」，張量模型則在進階區提供依模型輸入順序排列的 JSON 陣列。工作中可在原區域或任務中心取消。移除 Runtime 會保留模型、對話與已保存執行紀錄。

張量流程使用 OpenVINO `Core.read_model`、指定裝置編譯、`InferRequest.infer`、`EXECUTION_DEVICES` 和 profiling。只有數值推理成功且回報裝置符合要求時，紀錄才標為指定裝置已驗證。若回報 CPU 而要求 NPU，會保留其他裝置／fallback 的證據。GenAI 2025.4 的此介面沒有公開的逐子圖裝置查詢，成功生成後仍保留未驗證。 [OpenVINO 執行裝置屬性](https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/query-device-properties.html) · [GenAI Python 介面](https://docs.openvino.ai/2025/api/genai_api/_autosummary/openvino_genai.LLMPipeline.html)

Intel NPU 官方條件包含 Windows 11 22H2 以上與另裝相容驅動。2025.4 的 NPU 文字模型需對稱 INT4／NF4 及指定壓縮條件，本輪先允許可辨識的 INT4 symmetric、group size -1／128、ratio 1.0 候選。這仍須由實際裝置編譯確認算子、精度和記憶體相容性。NF4 與任意未知量化尚未開放。 [官方系統需求](https://docs.openvino.ai/2025/about-openvino/release-notes-openvino/system-requirements.html) · [NPU GenAI 模型條件](https://docs.openvino.ai/2025/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html)

在有 Runtime 的電腦可執行 `python openvino_acceptance.py --data "<應用程式資料夾>" --device NPU --output npu-evidence.json`。腳本借用既有 Runtime，使用獨立暫存資料庫、模型副本與編譯快取。預設建立小型、可核對輸出的 IR 合約測試模型，透過實際 TaskManager 執行。這項測試不代表大型文字或生成模型相容。加上 `--model <已匯入模型ID>` 可驗收文字生成契約，裝置分配另行標示。

執行紀錄保存模型檔案雜湊、後端、指定裝置、回報裝置、算子資訊、時間和狀態。程序最高 8 GiB、每次工作最長 180 秒，安裝程序最長 120 秒。大型模型及編譯可能超出這些界限而失敗。正式 Benchmark、冷／暖比較、TTFT、吞吐與峰值記憶體屬 E3-C，尚未交付。 [實測紀錄](TEST_REPORT.md) · [資料保護](PRIVACY_STORAGE.md)

## E1、E2 階段的偵測基礎（歷史紀錄）

Batch 4E＋NPU 本輪交付 E1、E2，程式版本 0.6.2。NPU 裝置偵測、Provider 列舉與模型實際執行各自有不同的證據。NPU Engine Adapter、模型相容性執行、異質派送和推理 Benchmark 屬 E3 後續工作。

| 狀態 | 能力 | 實際限制 |
|---|---|---|
| 已支援 | Windows DXGI GPU 清單、PDH 使用率與專用／共享記憶體，CIM 驅動及裝置狀態 | Intel Iris Xe 實測。驅動未提供的計數器顯示未知。GPU 資料按 LUID 配對，多 GPU 分別顯示 |
| 已實作待驗證 | NVIDIA／AMD／其他 Intel GPU 的同一套 Windows 監控 | NEEDS GPU，尚無各廠牌實體驗收 |
| 已實作待驗證 | Intel AI Boost／NPU、AMD IPU／NPU、Qualcomm Hexagon／NPU 的 Windows PnP 識別 | NEEDS NPU。單元測試採受控裝置資料，CPU 型號不參與推測。泛用 ComputeAccelerator 保留候選身分 |
| 已支援 | 可選 OpenVINO／ONNX Runtime 的獨立程序能力查詢 | 只檢查目前工作程序環境已安裝的套件，記錄版本、裝置和 Provider。此電腦兩套均未安裝 |
| 僅完成契約 | 硬體／Provider 版本、來源、未知值、時間與格式候選欄位 | 此契約可供 E3 使用，尚未新增 NPU Engine Registry 執行 Adapter |
| 實驗性，未實作 | 同模型 HETERO、跨 CPU／GPU／NPU 算子分配與效能比較 | NOT RUN。尚未開放選取或排程 |
| 不支援 | 直接把任意 GGUF 交給 NPU 執行、將 CPU fallback 記為 NPU 驗證、保證所有裝置都有 NPU 使用率／獨立記憶體 | 現有 GGUF 走原有 llama.cpp，創作走原有 ComfyUI |

硬體紀錄含 `schema`、清單時間、取樣時間、每裝置身分、廠牌、驅動、裝置錯誤碼、量測數值、來源及支援狀態。`verified_inference` 在本輪探測維持 false。NPU 使用率與專用記憶體目前標記未支援，UI 會顯示相應說明。CIM 查詢失敗時 NPU 是否存在為未知。

GPU 使用率以每張 GPU 最忙的引擎顯示，同一引擎各程序的計數器先相加。專用顯存總量取自 DXGI，已用量取自對應的 Windows GPU Adapter Memory 計數器。共享記憶體另列，不加進專用顯存。無法配對或互相矛盾的數值保留未知。計數器和清單的來源分別見 Windows 官方介面。 [PDH 陣列](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhgetformattedcounterarrayw) · [語系中立計數器](https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhaddenglishcounterw) · [DXGI 記憶體欄位](https://learn.microsoft.com/en-us/windows/win32/api/dxgi/ns-dxgi-dxgi_adapter_desc1) · [PnP 裝置](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-pnpentity)

Provider 查詢可在運算環境的「GPU 與 NPU → 進階」手動執行。OpenVINO 用 `Core.available_devices`，ONNX Runtime 用 `get_available_providers()`。初始化程序最長 25 秒，錯誤採固定診斷訊息。這兩個 API 的列舉結果尚未證明模型算子分配或 NPU 推理。OpenVINO IR、ONNX 是後端的候選格式，量化及模型支援要以 E3 的相容性測試為準。 [OpenVINO NPU](https://docs.openvino.ai/2025/openvino-workflow/running-inference/inference-devices-and-modes/npu-device.html) · [ONNX Runtime Provider](https://onnxruntime.ai/docs/execution-providers/)

後續 E3 的廠牌適配候選為 Intel OpenVINO、AMD Ryzen AI 的 Vitis AI EP，以及 Qualcomm QNN EP。需要分別準備相容模型、版本和驅動，測試算子分配、CPU fallback 和輸出，才可加入實際派送與推薦。 [AMD 官方模型執行](https://ryzenai.docs.amd.com/en/latest/modelrun.html) · [QNN 官方契約](https://onnxruntime.ai/docs/execution-providers/QNN-ExecutionProvider.html)

在專案根目錄執行 `python hardware_acceptance.py --providers --output hardware-evidence.json` 可保存真實裝置清單、三次取樣、取樣耗時與既有 Provider。檔案只驗收偵測和監控，`npu_inference` 明確為 `NOT RUN`。本輪 Intel Iris Xe 三次取樣耗時中位數 2.20 ms，取樣不包含背景裝置清單查詢。WMI／CIM 在背景執行，最多 20 秒，每次清單更新至少間隔 60 秒，關閉工作台可取消查詢。 [測試紀錄](TEST_REPORT.md)

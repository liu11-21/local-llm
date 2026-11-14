# llama.app Runtime integration — 0.8.0 Development

Architecture baseline: e2ba347 (0.7.0), inspected 2026-11-14. No uncommitted user changes existed.

| Area | Existing call chain and reuse |
|---|---|
| UI / native bridge | React ChatWorkspace / RuntimeWorkspace → api.rpc → Tauri Worker IPC; frontend never needs a Runtime API key |
| Worker / lifecycle | Desktop.perform → prepare → load_model → LocalEngine.start; EngineHealth handles readiness and stop |
| Scheduling | TaskManager → DeviceExecution admission / per-task copy → bound local engine; ResourceDemand reserves host / accelerator capacity |
| Agent / Team | desktop_agent + AgentRuntime + local_decision; TeamStore / team_dispatch depend on the same bound engine interface and retained tool grants |
| Benchmark | BenchmarkService → LlamaBenchmark → completion_events; saves raw usage / timings and evidence |
| Remote | RemoteClients / Host call existing scheduled worker actions; no new public llama listener is needed |
| Models / storage | catalog + downloads + registries; pinned HF revisions, resumed downloads and hashes; SQLite workspace.sqlite3 and protected upgrade snapshots retained |
| Other backends | OpenVINOAdapter / ComfyResources remain separate adapters; llama.app is text inference, not an image/video/music generator |

Legacy `llama-server.exe` takes server flags directly. New `llama.exe` is a dispatcher:
`version`, `serve ...`, `serve --help`, `serve --list-devices`; do not prepend the
same arguments blindly. Both use an OpenAI-compatible local API, but supported flags,
chat templates, thinking and cache behavior must be checked rather than assumed.
The official installer script was read, not executed. It selects CPU/Vulkan/CUDA/ROCm
artifacts and creates a WindowsApps alias; an alias is not evidence of the final process image.

Official sources: [installer](https://github.com/ggml-org/llama-install.sh),
[script](https://llama.app/install.ps1),
[server API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

The maintainer-reported remote hardware baseline is build 12360 / commit 2d8a32502,
Vulkan RTX 5070 Ti, Qwen3-4B Q4_0, prompt 160.92 and generation 215.09 token/s.
Those are supplied observations, not tests rerun on this development host. CUDA,
all auxiliary signatures, SAC, GPU utilization/power and other physical hosts remain unverified.

## Implemented adapter and application path

`RuntimeManager` persists the user's confirmed adapter and content pin separately from model data.
`LlamaAppEngine` adds the `serve` dispatcher and verified required CLI capabilities; `LocalEngine`
remains the legacy server adapter. Desktop, per-task DeviceExecution, model_team and LlamaBenchmark
all use the selected backend. Runtime changes are rejected while tasks are active and unload the
resident model before replacing the engine binding. Remote Host continues through the same worker.

Both adapters share bounded startup, local authentication, SSE, cancellation, health and tree cleanup.
New-server `/props` template capabilities determine thinking support; unknown models receive no forced
reasoning options. Supported templates use reasoning_effort:none when thinking is off; thinking on
uses the server's verified budget field and only passes effort levels actually declared by the template.
Prompt tokenization uses the same thinking-template choice. Agent native tool calls retain the existing
allowlist, human grants and audits; llama.app's own shell/file agent tools remain disabled.

The lower-level adapter accepts local GGUF or `hf://owner/repository:quantization` for explicit CLI-style
use. The application deliberately downloads pinned HF revisions through its existing resumable,
multithreaded/hash-verifying Model Registry before scheduled loading: unknown-size network downloads
must not bypass resource admission. Native llama.app HF caching is not presented as application-verified
storage. Existing GGUF files are not moved. Context/architecture is read from bounded cached metadata;
confirmed deletion refuses loaded/busy models and preserves chat/work records.

New source files: runtime_manager.py, runtime_trust.py, llama_app_engine.py, llama-app-runtime.json,
gguf_metadata.py; existing engine.py / desktop_worker.py / DeviceExecution / Benchmark integrations reused.
See [trust](RUNTIME_TRUST.md), [GPU support](GPU_RUNTIME_SUPPORT.md), [benchmark](LLAMA_BENCHMARK.md)
and [delivery](V080_DELIVERY.md).

# Runtime Capability v1

`runtime_contract.validate` is the Python contract boundary for both IPC and Host records. Tauri passes JSON through without translating it. The desktop can call `runtime-capabilities` to retrieve records and a freshness flag. Refreshing a configured legacy provider explicitly queries its model list.

| Fields | Meaning |
|---|---|
| `schema`, `id`, `label`, `kind`, `provider`, `version` | Integer schema version and runtime identity |
| `connected`, `health`, `error` | Connection, ability to accept work, and safe diagnostic |
| `tasks`, `formats`, `engines`, `models` | Bounded arrays of declared identifiers |
| `resources` | CPU threads, GPU names, RAM and VRAM bytes, and active jobs |
| `model_ram` | Optional CPU-memory estimates in bytes, keyed by the model ID on that Host |
| `features` | Stream, cancel, model load, unload, and download |
| `network`, `destination`, `auth`, `cost` | Transfer boundary, authentication and price classification |
| `source`, `checked_at` | Record provenance and Unix time in seconds |

A resource is an object with `value` and `source`. Provenance is `detected`, `reported`, `estimated`, `configured`, or `unknown`. Unknown values are null. A feature can be true, false, or null for unknown. The validator drops unfamiliar fields within the supported version and rejects unsupported schema versions. The desktop treats records older than 60 seconds as stale. `no-api-fee` describes an API billing policy and does not include electricity or network charges.

Colab Enterprise declares Notebook support. Generic OpenAI-compatible remote endpoints have unknown hardware and cost. Consumer Colab has no connector in this contract version.

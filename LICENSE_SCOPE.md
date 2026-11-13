# License scope — Local LLM Workspace

On 2026-11-13 the maintainer explicitly approved A1–A4 for the first-party scope
reviewed at `d74bb27f7cba65c0bb291e0a50a5fc143fef4062`. The standard MIT grant in
[LICENSE](LICENSE) applies to the following material, to the extent the maintainer
has rights to license it:

- First-party Python, TypeScript/React, CSS, Rust and first-party web source.
- First-party tests, fixture generator source, build/maintenance scripts,
  workflows and original configuration content.
- First-party technical documentation, excluding embedded third-party texts,
  quotations, external evidence and separately handled assets.

Attribution: **Copyright (c) 2026 劉仲軒**.

The project is maintainer-directed and primarily Codex/AI-assisted. This describes
provenance; it does not assert copyright in every AI output or guarantee absence
of third-party rights. The scope statement identifies covered material and does
not add restrictions to the MIT grant for that material.

## Material not relicensed by the project MIT grant

- Third-party source, dependencies, copied portions, notices, license texts and
  schemas retain their respective terms, even inside first-party directories.
- Downloaded or bundled runtimes and tools, including Python, llama.cpp,
  ComfyUI, OpenVINO, CUDA and related components, retain their own terms.
- Model weights, model cards, datasets, user data and generated user works are
  not relicensed by the project.
- Product logos/icons (`logo.png`, `logo.ico`, `docs/logo.png`,
  `desktop/src/logo.png`, `desktop/src-tauri/icons/icon.ico`), the review-only
  `docs/legal/logo-candidate-v1.png`, brand assets, UI screenshots and binary
  synthetic media fixtures remain separately handled. No new permission for
  those assets or claim of trademark ownership is made here. The fixture
  generator code is covered by MIT; its media outputs are excluded for now.
- SPDX metadata retains its stated CC0-1.0 data license; upstream schema and
  original evidence/Notices keep their original attribution and terms.

See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) and
[docs/THIRD_PARTY_LICENSES.md](docs/THIRD_PARTY_LICENSES.md). Existing notices and
applicable source-availability obligations must be preserved.

This code-license decision does not clear the whole Windows distribution or
establish SignPath eligibility. Product assets, actual bundled-component
obligations and Foundation acceptance remain separate release gates.

Approval record: [docs/MIT_FINAL_APPROVAL_CHECKLIST.md](docs/MIT_FINAL_APPROVAL_CHECKLIST.md).
Previous license-status notice: [LICENSE_STATUS.md](LICENSE_STATUS.md).

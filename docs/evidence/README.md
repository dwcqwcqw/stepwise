# Evidence

`preview-v1/` preserves the earlier retrieval-only implementation's receipts and screenshots. It is historical evidence, not a live model run.

The upgraded implementation uses full official rubrics, actual Gemini assessment/generation and separate target-blind assessment. Fresh runtime receipts are captured with `make run` / `make verify`, then `make evidence`. The `verification.json` receipt, model response IDs/usage, sample outputs, source/index manifests and screenshots identify the implementation actually exercised. No access tokens or raw training corpus should be committed.

## Current verified run

Implementation commit: `c4522d75b45c2ae32a73b0b5c133ccfcb5e43a71`; model `gemini-3.8-flash`; index `2da4e8eda6a331b5`. `verification.json` records 12 passing workflow checks and actual scores. `rag_verification.json` records all 40 Task 2 criterion-band queries, complete source coverage and zero loaded adaptation candidates. `unit-tests.txt` records 18 local tests. Sample essays are authored demonstration fixtures; do not replace them with private learner submissions. Model response IDs, token usage and latency are retained without authentication tokens.

PNG screenshots show the upgraded running application. Files ending in `-detail.png` are unaltered crops for PDF readability; full images are retained beside them. Historical preview evidence and its placeholder behavior stay under `preview-v1/`.

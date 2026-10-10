# Evidence

`preview-v1/` preserves the earlier retrieval-only implementation's receipts and screenshots. It is historical evidence, not a live model run.

The upgraded implementation uses full official rubrics, actual Gemini assessment/generation and separate target-blind assessment. Fresh runtime receipts are captured with `make run` / `make verify`, then `make evidence`. The `verification.json` receipt, model response IDs/usage, sample outputs, source/index manifests and screenshots identify the implementation actually exercised. No access tokens or raw training corpus should be committed.

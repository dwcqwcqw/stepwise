# Evidence

`preview-v1/` preserves the earlier retrieval-only implementation's receipts and screenshots. It is historical evidence, not a live model run.

The upgraded implementation uses full official rubrics, actual Gemini assessment/generation and separate target-blind assessment. Fresh runtime receipts are captured with `make run` / `make verify`, then `make evidence`. The `verification.json` receipt, model response IDs/usage, sample outputs, source/index manifests and screenshots identify the implementation actually exercised. No access tokens or raw training corpus should be committed.

## Current verified run

Implementation commit: `c4522d75b45c2ae32a73b0b5c133ccfcb5e43a71`; model `gemini-3.8-flash`; index `2da4e8eda6a331b5`. `verification.json` records 12 passing workflow checks and actual scores. `rag_verification.json` records all 40 Task 2 criterion-band queries, complete source coverage and zero loaded adaptation candidates. `unit-tests.txt` records 18 local tests. Sample essays are authored demonstration fixtures; do not replace them with private learner submissions. Model response IDs, token usage and latency are retained without authentication tokens.

PNG screenshots show the upgraded running application. Files ending in `-detail.png` are unaltered crops for PDF readability; full images are retained beside them. Historical preview evidence and its placeholder behavior stay under `preview-v1/`.

## Public production deployment

`public-deployment.json` records the verified fixed Vercel URL, source commit, Cloud Run revision/image digest, restricted invoker, official index, observed UI results and production HTTP request logs. `public-feedback.png`, `public-model-essay.png` and `public-model-essay.txt` were captured directly from the live fixed URL on 11 October 2026. The sample received 8.0; the target-7.0 generated essay contained 305 words and was separately assessed 9.0. These results verify the deployed workflow and expose target overshoot; they do not establish grading calibration. `deployment-unit-tests.txt` records 21 passing tests.

## Evidence-reference repair

`evidence-reference-tests.txt` records 29 passing local tests after the reference-contract repair. The server supplies exact essay spans with short IDs, resolves selected spans without autocorrection, and binds the retrieved awarded/next-band and detail records. Unknown references, missing details and fabricated quotes remain rejected. A retry receives the failed answer and validation reason. Diagnostic logs exclude essay text.

`reference-regression-input.json` is an authored public fixture with deliberate spelling/grammar issues, curly punctuation and doubled spaces, not a private student submission. Production regression receipts and screenshots are kept separately from the earlier Compose and production records so their implementation versions remain explicit.

## Complete band matching — current release

`band-paragraph-audit.json` verifies exact preservation of all 80 cells and 238 PDF paragraphs, including 119 Task 2 standards. `band-matching-tests.txt` records 46 passing unit tests. `band-matching-integration.json` records the 13-call real container run against the 369-point index, with model response IDs, all-criterion coverage and exact arithmetic. It names its v4 source honestly; v4.1 public browser checks are separate.

`band-matching-production-ui.json` records final fixed-URL draft and model-essay checks, source commits, revision and exact source/essay evidence checks. `band-matching-feedback.png` is a legible detail from the live band-specific feedback panel; `band-matching-overview.png` preserves surrounding feedback context. Earlier receipts retain their original source/index versions.

## Latency and live progress

`speed-and-progress.json` records before/after Cloud Run timings, model usage, response IDs and every received server event. Both optimized assessments pass all 119 statement checks. `speed-progress-production-ui.json` and `loading-review.png` / `loading-generation.png` record the fixed public URL displaying actual loading steps before completion. Unit coverage is 54 Python tests and five Node tests, including non-buffering gateway forwarding and incomplete-stream rejection. Earlier receipts remain tied to their original revisions.

## Selected-band generation

`target-band-7.json` and `target-band-6.5.json` record real Vertex calls from Cloud Shell using source `c1ae9372c42ec2efc9d0cd4bfe0386641f0fefbc`, model `gemini-3.5-flash` and index `339dcf75a711802b`. Both independently match the selected overall band and verify all 119 official Task 2 statements. They retain the actual candidate histories and model response IDs. `target-band-loading.png` shows the fixed public URL displaying the additional target-confirmation stage and automatic rewrite progress. Historical target-7 → score-9 screenshots above predate this fix.

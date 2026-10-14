# Evidence

`preview-v1/` preserves the earlier retrieval-only implementation's receipts and screenshots. It is historical evidence, not a live model run.

The upgraded implementation uses full official rubrics, actual Gemini assessment/generation and separate target-blind assessment. Fresh runtime receipts are captured with `make run` / `make verify`, then `make evidence`. The `verification.json` receipt, model response IDs/usage, sample outputs, source/index manifests and screenshots identify the implementation actually exercised. No access tokens or raw training corpus should be committed.

## Earlier verified container run

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

`target-band-5.json`, `target-band-7.json` and `target-band-6.5.json` record real Vertex calls from Cloud Shell using source `c1ae9372c42ec2efc9d0cd4bfe0386641f0fefbc`, model `gemini-3.5-flash` and index `339dcf75a711802b`. They independently match their selected overall bands and verify all 119 official Task 2 statements, retaining actual candidate histories and Google response IDs. These are historical host runs, not HTTP checks of a subsequent release.

`target-band-deployment.json` identifies the actual production backend source/revision, frontend deployment and public UI verification status. The frontend automatically resumes one assessed candidate per gateway request using opaque single-use server state; the assessor never receives the target. Current source has 103 passing Python tests and six Node tests. These contract tests do not measure success rates across real prompts.

v4.5 diagnostics showed that prompt-only focused rewrites changed unrelated criteria and exhausted five candidates. v4.6 applies validated exact before/after replacements, preserving every unedited character, paragraph breaks for language-only changes and the learner's protected position. Fresh independent assessment still determines success. The frozen production embedding cache is loaded offline to avoid a verified Hugging Face cold-start rate-limit failure.

The final v4.7 public check succeeded on source `bd305502d516cf30bc72d1c99d35a45cf9a97355`, revision `stepwise-api-00025-gub`, using 3.5 Flash MINIMAL: target 7.0, assessed 7.0, scores 7/8/6/7, 263 words. `target-band-public-ui.json` and `target-band-result.png` preserve the visible result and official page links. `target-band-progress.json` and `target-band-loading.png` record real cross-request progress. `target-band-patch-host.json` is a separate real host success on preceding source 0a2, with 9 → 6.5 → 7 and verified 119 citations/quotes. All historical receipts retain their own source/model versions.

## Compact generated-essay grading

`compact-model-grading.json` preserves the v4.9 one-call versus four-call same-essay comparison. `compact-schema-verification.json` separately records source `e1d6782`'s normal-essay pass and failed artificial fragmented-essay robustness case. Both keep source-specific timings and real Google receipts where available. `model-request-reliability.json` separates the reported error, real timeout recovery, first compact rollout's HTTP 400 and subsequent deployment status. See [design and verification](../compact-model-grading.md).

`compact-paired-verification.json` records the subsequent two-group host pass, including its real timeout and 93.013-second total. `compact-public-ui.json` records each public rollout separately; prior errors must not be interpreted as final successful generation. `compact-paired-progress.png` shows the actual paired-assessment stage on revision 00037.

The final source `0af3080`, revision 00041, completed the public target-5.5 check: 292 words, 6/5/5/5, mean 5.25 → 5.5. `compact-targeted-public-dom.json` and `compact-targeted-result.png` record the completed page; `compact-public-ui.json` records the 205-second generation/calibration total and verification boundaries.

## Decision-first grading and direct essay revision — 14 October 2026

- `decision-first-host.json`: actual Flash response IDs/usage; 119 standards, 20 skills, 17.74s screening and 68.89s total.
- `decision-first-lite-probe.json`: separate faster but materially different scoring profile; not adopted.
- `decision-first-public.json`: completed 307-word target-5.5 public result, 7/5/4/6 → 5.5, 81s overall, source419 / revision00045.
- `decision-first-public-details.json`: four inspected criterion panels, actual next steps/examples and descriptor links.
- `decision-first-result.png`: completed public page.

The earlier source7d public run failed the old local-edit writer protocol and is not counted as success. Source419 replaces normal calibration with complete-essay revisions. See `../decision-first-grading.md` for the exact failure chronology, implementation and verification boundaries.

## Closest assessed example — user-selected policy

`closest-example-public.json` and `closest-example-result.png` preserve the original target-7.5 request completing on source `a68b794`, revision 00047, in 42 seconds. Actual scores 8/8/8/9 give 8.5; the page truthfully identifies the target mismatch and closest result from three assessed drafts. This replaces the former five-attempt exact-match rejection policy. Raw candidate history was not exported; controlled tests cover minimum-distance selection and private retention.

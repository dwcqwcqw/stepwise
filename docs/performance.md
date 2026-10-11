# Latency and actual processing progress

## Changes

- The four criterion calls continue to run in parallel and check all 119 Task 2 paragraph standards and all applicable bold limits.
- Model payloads retain exact standards, band/criterion boundaries, conditional rules and limiter IDs. Duplicate parent-cell text, vector IDs, hashes and URLs remain on the server for validation/citations. The serialized complete rubric payload fell from 110,662 to 44,902 bytes (59.4%); this byte comparison is not an inference-latency claim.
- Short model JSON keys are losslessly expanded before the existing strict validation. No band, check, explanation or essay evidence is removed. Decimal score averaging and half-up rounding are unchanged.
- A shared Vertex HTTP connection pool avoids creating a fresh TLS connection for every criterion. Metadata access tokens and Vercel's Cloud Run invocation identity are reused only until shortly before expiry; credentials remain in process memory.
- Identical verified feedback can be reused within the current browser tab. The three-entry cache disappears on reload and never uses persistent storage. Changed inputs and model-essay generation still make new requests.

## Progress protocol

`POST /api/feedback/stream` and `POST /api/model-essay/stream` accept the same validated bodies as their existing JSON counterparts. Each sends request-scoped `application/x-ndjson` events:

```json
{"type":"progress","phase":"retrieval","status":"done","message":"All 119 Task 2 standards retrieved","statements":119}
{"type":"progress","phase":"assessment","status":"done","criterion":"CC","message":"Coherence and Cohesion checked"}
{"type":"progress","phase":"validation","status":"running","message":"Verifying all evidence, citations and score arithmetic"}
```

A `result` event carries only the fully validated final contract. An `error` terminates the operation without returning unchecked scores. A `heartbeat` reports elapsed time only. No progress database, polling endpoint, public job ID or saved learner essay is introduced. Both gateways forward chunks rather than buffering the whole response. The browser updates criterion chips from backend completion events, handles fragmented UTF-8, rejects incomplete streams and restores inputs after failures.

Files: `shared/compact.py`, `shared/progress.py`, `shared/assessment.py`, `shared/gemini.py`, `services/api/main.py`, `api/gateway.mjs`, `services/web/main.py`, and `services/web/static/progress.js`.

## Verification

54 Python tests and five Node tests cover full evidence validation after compact transport, preservation of exact standards/limits, incremental progress before completion, no unchecked result after failures, fragmented streams, identical-input reuse and immediate gateway forwarding with expiring identity reuse.

```bash
uv run --directory services/api --group dev pytest ../../tests/unit -q
npm ci --ignore-scripts
npm test
npm run build
```

Real-call measurements use the same authored sample and generation requirements. Run the following in the authorized Cloud Shell; credentials are read at runtime and never saved in receipts:

```bash
python3 scripts/benchmark_latency.py \
  --url https://stepwise-api-238092527041.us-central1.run.app \
  --output runtime/artifacts/speed-after.json
```

The script verifies all 119 statements, verbatim essay evidence, correct official source/pages, all four criterion completion events and exact score arithmetic. Timing includes request/stream transport; Google latency and token usage are recorded separately. A single before/after pair is an observed sample, not a p95 or a guaranteed speedup. Cold starts, provider load, essay length and validation repairs can still change elapsed time.

## Observed cloud results — 11 October 2026

| Same sample workflow | Before | After | Model input tokens before → after | First progress event after |
|---|---:|---:|---:|---:|
| Draft review | 19.668 s | 18.647 s | 61,441 → 27,710 | 1.139 s |
| Generation + separate assessment | 25.685 s | 23.031 s | 75,389 → 31,841 | 0.195 s |

Both final assessments retain all 119 statement checks. The calls complete without validation repairs (four assessment calls; five generation-plus-assessment calls). These single-pair observations show about 5%/10% elapsed-time improvement and 55%/58% fewer input tokens; they do not establish a repeatable latency percentile. The model-generated essays can differ between runs. The backend still scales to zero, so an idle service can take longer to start.

[Raw events, Google usage and response IDs](evidence/speed-and-progress.json) identify backend source `74731a3d206ed243652e1ff0c9c7d238c5765352`, revision `stepwise-api-00005-wez` and the exact inputs. The production frontend source is `acfe076f6680e65025610f6e118214958fb4fa52`.

The public browser test also verified that an unchanged draft reuses its validated result immediately in the same tab, while a new generation opens the writing stage and then independent review. Screenshots: [Review loading](evidence/loading-review.png) and [Generation loading](evidence/loading-generation.png). [Browser observations](evidence/speed-progress-production-ui.json) retain the actual visible stage changes and final source/evidence checks.

## Subsequent target-matching update

The v4.4 update adds independently checked target matching and bounded rewrites. Its latency must be measured separately from the single-candidate timings above. During verification, Gemini 3.8 Flash repeatedly returned HTTP 429; the deployed model was changed to Gemini 3.5 Flash. See [target-band verification](target-bands.md) for the actual candidate counts, timings and model receipts. Earlier measurements remain tied to their original source and model.

A later real 3.8 Flash capacity check succeeded in 2.283 seconds after its earlier 429 failures. The production model override was restored to `gemini-3.8-flash` on revision `stepwise-api-00015-juh`; the image still uses source `4b6b4a52897691dc0dd83bae2c9686ed2ec34493`. A public 3.5 request had timed out while independently assessing the first candidate. The 3.5 host receipts remain valid historical observations, not production timing promises. Model/provider latency and intermittent availability remain separate from the target-matching and per-round continuation logic.

## Cold-start and provider availability follow-up

Production cold starts previously tried Hugging Face metadata/download requests despite a shipped model cache; HTTP 429 delayed retrieval. Bundled retrieval now explicitly uses `local_files_only=True`, verified with a real offline 384-dimensional query. This changes neither the corpus nor embeddings.

Public tests of v4.6 with Gemini 3.8 encountered HTTP 429 before generation and, on a separate retry, after the first assessed candidate. The original inputs were preserved and no unmatched essay was returned. The Gemini client now accepts an operator-configured thinking level (default LOW); MINIMAL reduces optional internal reasoning while retaining the same complete official rubric, schema and strict server validation. Actual production model and final UI outcome are recorded in `evidence/target-band-deployment.json`. These availability failures must not be counted as successful target matches.

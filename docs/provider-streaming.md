# Incremental Vertex responses

## Failure confirmed

Production revision `stepwise-api-00053-ban` logged `ReadTimeout` at 75,010 ms, then 151,097 ms, and finally 180,011 ms on 16 October 2026. The former client waited for a complete `generateContent` response before it could consume the large structured result.

## Implementation

`shared/gemini.py` calls `streamGenerateContent?alt=sse` and consumes server-sent events incrementally. The existing 75-second read timeout now measures inactivity between response chunks. Complete output is assembled privately and passed through the same JSON schema, exact-evidence and official-rubric checks. No partial score or essay is shown. Truncated attempts are discarded before a bounded retry; thinking text is excluded. Usage, model response IDs, first-response time and transport attempts are retained in receipts. Progress events report actual response activity without exposing generated text.

The four independent criterion calls, all 119 official Task 2 statements, the two-PDF 359-point index and qualitative-only model-essay commentary are retained. No scoring threshold was loosened.

Official references: [streamGenerateContent](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.publishers.models/streamGenerateContent), [GenerateContentResponse](https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/GenerateContentResponse).

## Verification

159 deterministic tests pass, including stream fragmentation, thought-text exclusion, final usage metadata, truncation recovery, finish reasons and shared deadlines. `scripts/verify-model-stream.py` performs real HTTP checks with the public repository sample essay and records full provider receipts; it never substitutes a mocked model response.

## Model availability and configuration

A complete streamed 3.5 Flash test still exhausted its 180-second budget on Task Response, although the other three criteria completed. Streaming fixes full-response waiting but cannot fix a provider that sends no response. Configure primary `gemini-3.8-flash` and `GEMINI_FALLBACK_MODEL=gemini-3.5-flash` so transient timeout/429/5xx retries can use another full Flash model. Every attempt uses the same payload, schema and validation; receipts name the model that actually answered. Authentication errors are not hidden by fallback.

`GEMINI_THINKING_LEVEL=MINIMAL` maps to supported LOW for 3.8 and remains MINIMAL for 3.5. A real 3.8 connection probe rejected MINIMAL with HTTP 400, then succeeded with LOW in 1.282 seconds. These connection-probe timings are separate from essay-workflow timings.

## Complete live workflow check

The 3.8 Flash streamed candidate completed the repository sample review in 23.152 seconds, checking all 119 Task 2 statements, followed by target-6.5 generation plus qualitative commentary in 22.908 seconds (319 words). All four review calls and both generation/commentary calls completed in one transport attempt. This is one measured run, not a guaranteed latency bound. The sample review returned 8.5; this run checks transport and evidence integrity, not calibration against an examiner label.

## Final production release

Source `65c36d1`, Cloud Run revision `stepwise-api-00057-niz`, 100% production traffic. Primary model: `gemini-3.8-flash`; fallback: `gemini-3.5-flash`. The final v6.3 release repeated all 119 statement checks in 25.641 seconds, with four first-attempt 3.8 responses. The existing user browser session then successfully retried its preserved 302-word draft at target 6.5: 277 generated words, four qualitative feedback sections, 21 seconds on the visible timer (18,888 ms server progress), and no error. Learner text is not included in these receipts. See `docs/evidence/provider-failover-release.json` and associated provider receipts.

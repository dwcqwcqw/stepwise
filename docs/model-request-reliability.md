# Google model request reliability

## Reported failure — 12 October 2026

The public app displayed `Google model request could not complete; please retry.` while generating a target-5.5 essay. The selected target and requirements remained in the page. Vercel's runtime-error query for the recent one-hour window returned no errors.

In the deployed v4.7 client, that message is raised for HTTPX transport errors, including a read timeout. HTTP status errors such as Google HTTP 429 use a different message. The precise historical transport subtype is not yet established: the existing client did not log that subtype. After sign-in was restored, Cloud Run showed consecutive model-essay stream requests of 59.230248373 and 244.054112633 seconds on revision `stepwise-api-00025-gub`. The latter is consistent with the old 240-second read timeout plus surrounding work, but the log does not expose the exception subtype. Do not label this specific incident as a confirmed 429 or a confirmed read timeout without further evidence.

## Patch

- Retry HTTPX timeout, network and interrupted-protocol failures, rather than failing immediately on read/write/pool timeouts.
- Retry transient HTTP 408, 429, 500, 502, 503 and 504 responses with bounded exponential backoff and jitter. Authentication/permission errors remain immediate failures.
- Limit a single attempt's read wait to 75 seconds and a model-call retry sequence to a 180-second budget. Streamed operations share a 235-second deadline checked before calls/retries, leaving time to return a checked error before the gateway's 270-second timeout. HTTPX timeouts are I/O inactivity limits, not a strict process cancellation timer.
- Copy the request context into all four criterion executor threads so the deadline and retry progress apply consistently to parallel assessment calls.
- Show real automatic-retry events in the existing progress message. Record `transport_attempts` in successful model receipts.
- Log model name, attempt, elapsed time and exception **type**; never log prompts, essays, tokens or raw exception text.
- Return distinct timeout/connection messages after retries are exhausted. Preserve the existing full-rubric validation, target-blind assessment and exact target matching.

This follows Google's guidance to retry transient inference errors with exponential backoff: [Vertex inference errors](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/api-errors), [retry strategy](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/retry-strategy).

## Verification boundary

120 Python unit tests pass, including 15 new transport/context cases and two length-repair regression cases. Coverage includes read/write timeout recovery, bounded retry exhaustion, HTTP 504, non-retryable 403, deadline expiry, deadline propagation to all four criteria, progress events and private-data exclusion from logs. One existing Starlette AnyIO deprecation warning remains.

The new parallel-criterion test uses the complete 40-statement compact **unit fixture**, not the 119-statement production corpus. It verifies unchanged validation of that fixture; the production rubric pipeline remains unchanged.

Harvard sign-in was restored and the transport/length patches were deployed. A real public retry recovered to a subsequent candidate; browser control detached before the final outcome, so that run is not counted as a successful generation. Earlier target-7.0 success screenshots verify the earlier deployed source, not this transport patch. Do not replace their original source/revision metadata or count unit fixtures as real Google calls.

## Real diagnostic follow-up

A real Cloud Shell diagnostic on source `79335148cf39e83aa1dfd5886f0c5a3f61926198` captured `ReadTimeout` after 75,077 ms, emitted an automatic retry, and then received a writer response. This verifies a real timeout/retry recovery on that source, separately from the controlled unit failures. The writer returned a 218-word revised essay; the old generic length retry produced only 223 words and failed. This exposed a separate, reproducible length-repair problem.

The length repair now receives the measured word count and the failed candidate, preserves the requested proficiency and stance, and asks focused editors for edits against their original base rather than a whole-essay response. Safe logs record mode, count and position-check status. Public verification of this subsequent source is recorded separately.

The subsequent compact-assessment rollout on revision `stepwise-api-00034-wew` passed a real host assessment with all 119 exact-evidence checks but its first public target-5.5 generation exhausted transport retries during combined assessment. A bounded timeout was displayed and requirements stayed intact. Therefore retry recovery is verified in earlier runs, while this specific public attempt remains a failure. See the compact grading report and deployment receipt for version-specific outcomes.

## Final public outcome

The subsequent source `0af3080`, revision `stepwise-api-00041-wag`, completed the public target-5.5 workflow: 292 words, independent scores 6/5/5/5, exact mean 5.25 rounded to 5.5. The page displayed 205 seconds for generation plus calibration and scoring. This verifies a successful completed outcome, not a guaranteed latency bound or a speedup benchmark. See `evidence/compact-public-ui.json` and its screenshot. Total unit coverage is now 139 passing Python tests.

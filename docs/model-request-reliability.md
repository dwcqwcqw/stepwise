# Google model request reliability

## Reported failure — 12 October 2026

The public app displayed `Google model request could not complete; please retry.` while generating a target-5.5 essay. The selected target and requirements remained in the page. Vercel's runtime-error query for the recent one-hour window returned no errors.

In the deployed v4.7 client, that message is raised for HTTPX transport errors, including a read timeout. HTTP status errors such as Google HTTP 429 use a different message. The precise historical transport subtype is not yet established: the existing client did not log that subtype, and the Google Cloud session currently requires HarvardKey sign-in before backend logs can be inspected. Do not label this specific incident as a confirmed 429 or a confirmed read timeout without further evidence.

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

118 Python unit tests pass, including 15 new transport/context regression cases. Coverage includes read/write timeout recovery, bounded retry exhaustion, HTTP 504, non-retryable 403, deadline expiry, deadline propagation to all four criteria, progress events and private-data exclusion from logs. One existing Starlette AnyIO deprecation warning remains.

The new parallel-criterion test uses the complete 40-statement compact **unit fixture**, not the 119-statement production corpus. It verifies unchanged validation of that fixture; the production rubric pipeline remains unchanged.

**Deployment and real target-5.5 browser retest are pending Google Cloud sign-in.** Earlier target-7.0 success screenshots verify the earlier deployed source, not this transport patch. Do not replace their original source/revision metadata or count unit fixtures as real Google calls.

# Faster assessment of generated model essays

## Current design

Generated essays use two parallel target-blind Gemini calls: TR/CC and LR/GRA. The paired design introduced in `dba036f` replaces the earlier single combined call; current source `0af3080` additionally implements targeted numerical-feedback repair after public timeout observations. Both groups receive only the question, essay and their official standards; the full four-criterion result must pass the same server validator. Request budgets propagate into both threads.

The earlier one-call design assessed all four criteria together. The assessor receives the question, actual essay, exact evidence spans and the full official band ladder. It receives no requested target, writer plan, prior score or calibration history.

All 119 Task 2 paragraph standards and all bold limiting features remain checked. Instead of writing an explanation and repeating the official identifier for every hidden band, the model returns ordered M/N/A decisions, exact evidence IDs and limiter flags. The server restores identifiers from the immutable official ordering and verifies exact lengths, ordinary-requirement applicability, verbatim quotes, bold caps and the highest supported integer band using the existing validator.

Detailed model explanations are required for every statement in the awarded band and next band, plus every present limiter. Hidden bands use explicitly labelled server decision captions, not invented model reasoning. Each displayed criterion still includes a rationale, next-band gap, concrete improvement, original/revised example and all qualitative skill checks. Equal weighting and Decimal half-up averaging are unchanged. Calibration still rewrites prose and independently reassesses when the overall estimate differs from the requested target; no score is overridden.

Implementation: `shared/model_assessment.py`; generation routes through `assessment.assess_model_essay`. The frontend contract remains the same. Progress reports two pairs in parallel and marks completion only after all checks pass. The same request budgets and transient-error retries apply.

## Real same-input comparison — 12 October 2026

Both methods ran sequentially in Cloud Shell against exactly the same public demonstration essay (SHA256 `714fb75c6b2f34d9a78d18416a89bea7274a6f896ca5d6d10d0d51b493f9cc6b`), model `gemini-3.5-flash`, thinking MINIMAL, source `fedc783294e1361f9c258e34b6d385b59695913f`, official index `339dcf75a711802b`.

| Assessment method | Model calls | Wall time | Input tokens | Output tokens | TR / CC / LR / GRA |
|---|---:|---:|---:|---:|---|
| Earlier parallel criterion calls | 4 | 28.398 s | 27,746 | 11,786 | 7 / 7 / 6 / 6 |
| Compact combined call | 1 | 24.159 s | 20,664 | 4,826 | 7 / 7 / 6 / 6 |

This pair shows 14.9% less wall time, 25.5% fewer input tokens and 59.1% fewer output tokens. Both independently returned overall 6.5 and verified all 119 exact quotes and official descriptor pages 7–9. These are observed sample measurements, not a p95 or a promised speedup. Four earlier calls were already parallel, so merging them does not imply four-times-faster wall time.

[Raw model receipts and Google response IDs](evidence/compact-model-grading.json) retain both methods' actual usage and timings. This is a host benchmark, separately identified from the public deployed generation check.

139 Python tests pass. Nineteen compact-assessment cases cover one-call execution, all four distinct criteria, complete ordered matching, exact evidence, unsupported scores, bold caps, required awarded/next-band explanations and failed-repair rejection. The compact unit fixture has 40 standards; the real benchmark validates the full production 119.

## Provider schema complexity fix

The first public v4.9 generation reached combined assessment but Google returned HTTP 400. The service was rolled back to revision `stepwise-api-00029-nin` while the issue was investigated. Removing repeated evidence-ID enums alone (source `26b581f`) still failed a many-sentence stress case. Source `e1d678229d1a337f3acdd8995943c028aa2b6a6c` additionally removes fixed array-size constraints from the provider schema. Exact collection counts, ID membership and complete official coverage remain strict server validation gates. This follows [Google's structured-output guidance](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/control-generated-output) on schema complexity.

The timing comparison above belongs to v4.9. It must not be presented as a new measurement of the later schema fix.

## Schema-fixed real check

On source `e1d678229d1a337f3acdd8995943c028aa2b6a6c`, the same demonstration essay passed all 119 statement, exact-evidence and citation checks in **21.687 seconds**, with the same 7/7/6/6 criterion profile and 6.5 overall. One call used 16,440 input and 5,186 output tokens; Google response ID `HNrMaoP2NriG1e8PzdSI8A8`. Relative to the earlier baseline this single observation is 23.6% less elapsed time, 40.7% fewer input tokens and 56.0% fewer output tokens. Provider latency varies; these are not repeated-sample averages.

An intentionally fragmented many-sentence stress fixture no longer returned a provider HTTP 400 but failed the full evidence/score consistency gate after repair (101.065 seconds). It is retained as a failed robustness case, not counted as a passing assessment or a speed result.

## Public rollout boundary

Revision `stepwise-api-00034-wew` (source `e1d6782`, image SHA256 `c82b36a2117dc3ec28646625c6cf97babad33a3b73724b099934982a9b7a1de5`) was promoted after the real normal-essay pass. Its first target-5.5 public run reached combined assessment but exhausted three transport attempts and returned the checked timeout message. Cloud Run recorded ReadTimeout at 75,003 and 151,317 ms; no unchecked scores or candidate were displayed. This is separate from the 21.687-second host success and must not be counted as a successful end-to-end public generation.

## Follow-up selection

A Flash-Lite trial failed strict evidence/limiter explanation validation after repair and was not selected for production. The first paired prototype (`442c78a`) exposed an unknown evidence ID, so source `dba036f` restores exact evidence-ID enums in the smaller paired provider schema. Large fixed array-length grammars remain removed; complete counts and official decisions are still checked on the server.

## Final paired host check

Source `dba036f1add398baa0b3009074eb04f8881762ba` passed all 119 standards with scores 7/7/6/6 and overall 6.5. TR/CC completed in 11.578 s; LR/GRA required a real transport retry and completed in 92.332 s. Total wall time was **93.013 s**. This run does **not** demonstrate a wall-time speedup over the 28.398-second baseline. Two successful logical responses reported 20,170 input and 5,369 output tokens (54.4% less successful output than the earlier baseline); usage for the timed-out attempt is unavailable, so these totals are not an all-attempt cost measurement.

[Actual paired and rejected Lite receipts](evidence/compact-paired-verification.json) preserve this boundary. The paired release is revision `stepwise-api-00037-zek`, image SHA256 `d67bfd34ff861d1b0c7dc225a653e81aa4a26efce07b4ec465012bebed0f3e1f`.

## Validation refinement

The v4.11 public target-5.5 run returned a checked evidence-validation failure. Its exact rule was not logged, so the cause is not asserted. Independently, the Lite trial reproduced rejection of extra limiter explanations: a valid official limiter explained as absent can be harmless even when it is outside the awarded/next-band focus. Source `c46e4eb` permits such extra explanations only for known official limiter IDs, rejects duplicates/unknown IDs, and still requires every focus/present limiter explanation. All flags, evidence IDs, score caps, paragraph matches and exact arithmetic remain mandatory. Three regression cases cover this boundary. New safe diagnostics record validation rules while excluding generated received-ID values and learner text.

## Targeted numerical consistency repair

The source `c46e4eb` public run completed earlier candidate assessments and then failed twice on the same rule: `Criterion LR score inconsistent with complete descriptor matches: expected 5`. This establishes the actual failure for that rollout; it is separate from provider timeout failures and the earlier optional-limiter reproduction.

Source `0af30800589d1a224ab9d37686aa1c274aa39620` repairs only the offending criterion's explanation and numeric field. It freezes every original ordered statement decision, evidence ID and limiter flag; the score constraint is derived from those full official matches, not the learner's requested target. The repair schema excludes decision arrays and constrains the criterion score to the derived integer. The server combines the repaired feedback with the unchanged decisions and re-runs the full original validator, including official citations and exact arithmetic. Attempts to alter the immutable classifications are rejected.

A single numerical mismatch now uses two initial paired calls plus one small feedback-only repair, rather than repeating both full paired calls. Other types of invalid evidence retain the bounded complete repair. Controlled regression tests verify target-blind inputs, the fixed score schema, three-call execution, exact decision preservation and tampering rejection. Actual wall-time improvement for this final repair remains subject to live verification.

## Final public verification

The fixed Vercel URL completed a real target-5.5 generation on revision `stepwise-api-00041-wag`, source `0af3080`, image SHA256 `365b4e99a55958fc1ceb91143dfabb3dd68d2688a90467a8356751f65430fdc1`. The 292-word essay was independently assessed **6/5/5/5**, exact mean **5.25 → 5.5**, matching the requested band. Current/next-band statements linked to the official Band Descriptors PDF. The frontend showed a second candidate adjustment before completion.

The displayed total was **205 seconds**, and the final request's last server event was at 99,693 ms. This is complete generation, target calibration and scoring, not a scoring-only latency measurement, and does not establish an overall wall-time improvement. The source reduces repeated scoring output and limits numeric-feedback repairs; provider latency and multiple calibration rounds remain material.

[Public receipt](evidence/compact-public-ui.json), [DOM evidence](evidence/compact-targeted-public-dom.json) and [success screenshot](evidence/compact-targeted-result.png) preserve the completed result. Full public model-call receipts were not exported; the final optional Cloud log check was unavailable after Harvard sign-in expired again. No further login was needed to complete the deployed public workflow. The real triggering of the new feedback-only repair is not independently established for this successful run; its behavior is covered by the controlled tests above.

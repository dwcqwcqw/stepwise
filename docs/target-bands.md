# Matching the selected model-essay band

## Regression and correction

Previously, generation received the requested band but only checked the essay's length. `target_met` used `assessed >= requested`, so a request for Band 7 could return a separately assessed Band 9 as a successful result. The generation prompt also favoured polished prose regardless of the requested proficiency.

The generator now receives an integer criterion profile whose equally weighted mean equals the selected overall target, plus the exact official descriptors for each intended criterion level and its adjacent boundaries. A half-band target combines published integer criterion rows; no half-band descriptor is invented. The generation plan identifies the level's demonstrated strengths and limitations before producing the essay. Position and ideas remain content requirements. The first candidate identifies a verbatim sentence expressing the requested position; every rewrite must retain that exact sentence, and the server checks its presence before assessment. This prevents score adjustment from making the learner's stance undecided. The sentence check enforces preservation; it is not an independent semantic evaluation of the first candidate.

Every candidate is assessed afresh using the existing complete, target-blind four-criterion pipeline: all 119 official Task 2 statements, applicable limiting features, exact essay evidence, official page citations and Decimal half-up averaging. The assessor receives only the question and candidate essay. It does not see the selected target, generation plan, prior assessment or revision instructions. Scores are never overwritten, clamped to the target or assigned from the generation profile.

If the independent overall estimate differs from the selected target, the generator receives the observed evidence-based mismatch and rewrites the candidate. For a large mismatch, the next writing profile compensates separately for each observed criterion error: current writing level + desired criterion score - observed criterion score, bounded to published levels 2–9. These are instructions for the writer, never scores assigned to the essay. For a mismatch of one band or less, the server finds the nearest integer score combination whose true half-up overall equals the target, adjusts the existing writer control levels by the observed error, then requests small edits only for the necessary criteria. This preserves the existing argument and other skills instead of repeatedly rebuilding the whole essay. All candidates are scored afresh without revealing the target to the assessor. The process allows at most five assessed candidates. A result is returned only when `assessment.overall_band == requirements.target_band`; a persistent mismatch produces a clear retry error with the original requirements intact. Matching an automated practice estimate is a generation constraint, not evidence of agreement with human examiner ratings.

## UI and verification

Generation progress now includes “Confirm your selected band”. A rewrite resets the criterion chips and pending validation steps; users can see the actual adjustment attempt. The result says the independent assessment **matches** the chosen band.

Files: `shared/targeting.py`, `shared/assessment.py`, `shared/gemini.py`, `services/web/static/progress.js` and `services/web/static/app.js`.

103 Python tests and six Node tests pass. Regression coverage includes all eleven supported whole/half-band profiles, overshoot and undershoot revisions, fresh target-blind assessment, adjacent official descriptor selection and rejection of repeated Band 9 overshoot without a successful result event.

Real model verification is separate from these mocked contract tests. Run inside the authorized Cloud Shell after deploying the candidate:

```bash
python3 scripts/verify_target_bands.py \
  --url https://target-candidate---stepwise-api-t37cje4wva-uc.a.run.app \
  --bands 4 5 6.5 7 8.5 9 \
  --output runtime/artifacts/target-band-verification.json
```

The script runs one request at a time by default (use `--workers 2` only when model capacity allows) and records real candidates, individual criterion scores, retries, Google response IDs and progress events. It verifies exact target equality, all 119 citation/evidence checks and score arithmetic. Credentials are read only at runtime. Rewriting can add latency and model cost compared with the earlier single-candidate flow; attempts are bounded.

## Real verification — 11 October 2026

Backend source: `c1ae9372c42ec2efc9d0cd4bfe0386641f0fefbc`; model: `gemini-3.5-flash`; official index: `339dcf75a711802b`. These sequential checks ran in Cloud Shell with real Vertex model calls and the same frozen index/code as the deployed image. They are not HTTP deployment tests; the public browser check is recorded separately.

| Requested | TR / CC / LR / GRA | Mean | Assessed overall | Assessed candidates | Elapsed |
|---|---|---:|---:|---:|---:|
| 5.0 | 5 / 5 / 5 / 4 | 4.75 | 5.0 | 2 | 573.357 s |
| 7.0 | 8 / 7 / 6 / 7 | 7.0 | 7.0 | 2 | 162.240 s |
| 6.5 | 7 / 7 / 7 / 5 | 6.5 | 6.5 | 3 | 340.743 s |

[Band 5 receipt](evidence/target-band-5.json), [Band 7 receipt](evidence/target-band-7.json) and [Band 6.5 receipt](evidence/target-band-6.5.json) retain candidate score histories, essay hashes, final essays and Google response IDs. All three verify all 119 Task 2 statements, official Band Descriptors pages 7–9 and verbatim essay evidence. The observed candidate paths were 7.5 → 5.0, 8.5 → 7.0 and 9.0 → 6.0 → 6.5. These examples verify successful target adjustment; they do not establish a success rate across prompts or agreement with human examiners. Multi-candidate generation took minutes in these observations and remains a latency improvement opportunity.

## Free-tier request duration

The production Vercel Hobby plan rejects `maxDuration=800`; its limit remains 300 seconds. Generation therefore performs one candidate plus fresh independent assessment per streamed request. An opaque, single-use random token resumes subsequent candidates automatically from the same page. The server binds each token to the original requirements, retains unmatched candidates privately in process memory for at most 15 minutes, limits pending sessions to eight and removes state when consumed. No unmatched essay or internal calibration feedback is returned to the browser. The five-candidate limit and original target-blind scoring remain unchanged. This deployment uses one Cloud Run instance/worker; a restart, expiry or changed requirements gives a retry error. Shared durable encrypted storage would be needed before scaling across instances. The gateway retains its 270-second per-request timeout; unusually slow individual model rounds can still fail, while several normal rounds can now exceed five minutes in total without one long gateway invocation.

A public test of source c1ae reached a third candidate but rejected an ordinary Lexical Resource standard marked `not_applicable` twice. The validator still rejects skipped requirements. Its repair message now identifies the exact statement ID and band, and explicitly requires `meets` or `not_met`; it does not alter the model's answer or bypass validation.

## v4.5 focused controller correction

A real public test of the v4.4 source with restored 3.8 Flash exhausted all five candidates without matching Band 7. The focused revision path had reset writer instructions to the desired *assessed* profile, discarding the lower control levels learned after an earlier overshoot. v4.5 applies `current_writer_level + desired_assessed_score - observed_score` in both whole and focused revisions. In a focused edit, unchanged criteria keep their prior writing control level exactly; only required criteria move. A regression test covers 9.0 → 6.5 → requested 7.0: the next profile keeps TR/CC/GRA at their calibrated levels and changes only LR. Returned scores still come exclusively from a new target-blind assessment.

## v4.6 exact local patches

Real 3.8 diagnostics on the v4.5 source showed 9.0 → 6.5 → 8.0 → 6.0. The first focused revision needed only LR to rise from 6 to 7, but the model had only 48.7% word-sequence similarity to the previous candidate and all four estimated criteria rose to 8. Instructions to preserve the rest of the essay were insufficient.

Focused revisions now return 1–8 exact before/after replacements, rather than a replacement essay. The server checks unique existing spans, non-overlap, a maximum 25-word before span and 35-word after span, the exact protected position and a total before+after budget of 20% of essay words when one or two criteria are focused (50% when three or four are focused). LR/GRA edits must preserve paragraph breaks. All unedited text is preserved programmatically. Patch prompts use the desired assessed criterion's actual official row and adjacent boundaries; previously calibrated control levels remain available for whole rewrites. Invalid edits receive one repair opportunity and cannot bypass independent assessment or the exact target check. All four criteria are still independently reassessed after applying each patch; no prior score is reused.

## Frozen embedding cache

Bundled production images load `BAAI/bge-small-en-v1.5` with `local_files_only=True`. A real offline Cloud Shell query returned the expected 384-dimensional vector from the shipped cache. This removes cold-start Hugging Face metadata/download requests that previously received HTTP 429; the index and semantic retrieval remain unchanged. Compose ingestion can still download the model when preparing its cache.

## v4.7 actionable patch repair

A real 3.5 Flash MINIMAL diagnostic found a focused LR patch with 179 before+after words against a 54-word budget. The editor now receives the explicit integer budget, a preference for short word/phrase replacements and its failed edits with the precise validation error on retry. Successful candidates clear stale repair instructions before the next calibration round. A regression test verifies the failed edits and integer budget reach the repair call. Scores and the independent assessor are unchanged.

Production uses `GEMINI_MODEL=gemini-3.5-flash` and `GEMINI_THINKING_LEVEL=MINIMAL` after repeated 3.8 capacity errors. The code defaults to LOW unless the operator configures another supported level. The complete assessment contract and target-blind inputs are identical. The latest source/revision and observed public result are recorded in [deployment receipt](evidence/target-band-deployment.json).

## Final public UI check — 12 October 2026

The fixed URL `https://stepwise-one.vercel.app/` completed a real target-7.0 request on backend source `bd305502d516cf30bc72d1c99d35a45cf9a97355`, revision `stepwise-api-00025-gub`, Gemini 3.5 Flash MINIMAL. The final 263-word essay was independently assessed TR 7 / CC 8 / LR 6 / GRA 7: exact mean 7.0, displayed overall 7.0. The browser displayed Target 7.0 · Assessed 7.0 and official Band Descriptors page-7 links. [Visible UI receipt](evidence/target-band-public-ui.json), [result screenshot](evidence/target-band-result.png) and [real progress](evidence/target-band-progress.json) preserve this observed result. This is one public sample, not a success-rate estimate across all bands.

A separate real host diagnostic on the preceding `0a2ce7d5a12c4ba9131a0ca5f0f0854864255bcf` source, with the same model/thinking level, observed 9.0 → 6.5 → 7.0 and final scores 7/7/7/7. Its [receipt](evidence/target-band-patch-host.json) includes Google response IDs and verified 119 exact quotes/official pages. It is explicitly separate from the final HTTP/browser check.

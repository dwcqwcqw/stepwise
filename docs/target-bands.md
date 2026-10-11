# Matching the selected model-essay band

## Regression and correction

Previously, generation received the requested band but only checked the essay's length. `target_met` used `assessed >= requested`, so a request for Band 7 could return a separately assessed Band 9 as a successful result. The generation prompt also favoured polished prose regardless of the requested proficiency.

The generator now receives an integer criterion profile whose equally weighted mean equals the selected overall target, plus the exact official descriptors for each intended criterion level and its adjacent boundaries. A half-band target combines published integer criterion rows; no half-band descriptor is invented. The generation plan identifies the level's demonstrated strengths and limitations before producing the essay. Position and ideas remain content requirements. The first candidate identifies a verbatim sentence expressing the requested position; every rewrite must retain that exact sentence, and the server checks its presence before assessment. This prevents score adjustment from making the learner's stance undecided. The sentence check enforces preservation; it is not an independent semantic evaluation of the first candidate.

Every candidate is assessed afresh using the existing complete, target-blind four-criterion pipeline: all 119 official Task 2 statements, applicable limiting features, exact essay evidence, official page citations and Decimal half-up averaging. The assessor receives only the question and candidate essay. It does not see the selected target, generation plan, prior assessment or revision instructions. Scores are never overwritten, clamped to the target or assigned from the generation profile.

If the independent overall estimate differs from the selected target, the generator receives the observed evidence-based mismatch and rewrites the candidate. For a large mismatch, the next writing profile compensates separately for each observed criterion error: current writing level + desired criterion score - observed criterion score, bounded to published levels 2–9. These are instructions for the writer, never scores assigned to the essay. For a mismatch of one band or less, the server finds the nearest integer score combination whose true half-up overall equals the target, then requests small edits only for the necessary criteria. This preserves the existing argument and other skills instead of repeatedly rebuilding the whole essay. All candidates are scored afresh without revealing the target to the assessor. The process allows at most five assessed candidates. A result is returned only when `assessment.overall_band == requirements.target_band`; a persistent mismatch produces a clear retry error with the original requirements intact. Matching an automated practice estimate is a generation constraint, not evidence of agreement with human examiner ratings.

## UI and verification

Generation progress now includes “Confirm your selected band”. A rewrite resets the criterion chips and pending validation steps; users can see the actual adjustment attempt. The result says the independent assessment **matches** the chosen band.

Files: `shared/targeting.py`, `shared/assessment.py`, `shared/gemini.py`, `services/web/static/progress.js` and `services/web/static/app.js`.

89 Python tests and five Node tests pass. Regression coverage includes all eleven supported whole/half-band profiles, overshoot and undershoot revisions, fresh target-blind assessment, adjacent official descriptor selection and rejection of repeated Band 9 overshoot without a successful result event.

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
| 7.0 | 8 / 7 / 6 / 7 | 7.0 | 7.0 | 2 | 162.240 s |
| 6.5 | 7 / 7 / 7 / 5 | 6.5 | 6.5 | 3 | 340.743 s |

[Band 7 receipt](evidence/target-band-7.json) and [Band 6.5 receipt](evidence/target-band-6.5.json) retain candidate score histories, essay hashes, final essays and Google response IDs. Both verify all 119 Task 2 statements, official Band Descriptors pages 7–9 and verbatim essay evidence. The observed candidate paths were 8.5 → 7.0 and 9.0 → 6.0 → 6.5. These examples verify successful target adjustment; they do not establish a success rate across prompts or agreement with human examiners. Multi-candidate generation took minutes in these observations and remains a latency improvement opportunity.

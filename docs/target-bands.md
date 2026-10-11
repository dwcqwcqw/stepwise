# Matching the selected model-essay band

## Regression and correction

Previously, generation received the requested band but only checked the essay's length. `target_met` used `assessed >= requested`, so a request for Band 7 could return a separately assessed Band 9 as a successful result. The generation prompt also favoured polished prose regardless of the requested proficiency.

The generator now receives an integer criterion profile whose equally weighted mean equals the selected overall target, plus the exact official descriptors for each intended criterion level and its adjacent boundaries. A half-band target combines published integer criterion rows; no half-band descriptor is invented. The generation plan identifies the level's demonstrated strengths and limitations before producing the essay. Position and ideas remain content requirements.

Every candidate is assessed afresh using the existing complete, target-blind four-criterion pipeline: all 119 official Task 2 statements, applicable limiting features, exact essay evidence, official page citations and Decimal half-up averaging. The assessor receives only the question and candidate essay. It does not see the selected target, generation plan, prior assessment or revision instructions. Scores are never overwritten, clamped to the target or assigned from the generation profile.

If the independent overall estimate differs from the selected target, the generator receives the observed evidence-based mismatch and rewrites the candidate. The process allows at most three assessed candidates. A result is returned only when `assessment.overall_band == requirements.target_band`; a persistent mismatch produces a clear retry error with the original requirements intact. Matching an automated practice estimate is a generation constraint, not evidence of agreement with human examiner ratings.

## UI and verification

Generation progress now includes “Confirm your selected band”. A rewrite resets the criterion chips and pending validation steps; users can see the actual adjustment attempt. The result says the independent assessment **matches** the chosen band.

Files: `shared/targeting.py`, `shared/assessment.py`, `shared/gemini.py`, `services/web/static/progress.js` and `services/web/static/app.js`.

78 Python tests and five Node tests pass. Regression coverage includes all eleven supported whole/half-band profiles, overshoot and undershoot revisions, fresh target-blind assessment, adjacent official descriptor selection and rejection of repeated Band 9 overshoot without a successful result event.

Real model verification is separate from these mocked contract tests. Run inside the authorized Cloud Shell after deploying the candidate:

```bash
python3 scripts/verify_target_bands.py \
  --url https://target-candidate---stepwise-api-t37cje4wva-uc.a.run.app \
  --bands 4 5 6.5 7 8.5 9 \
  --output runtime/artifacts/target-band-verification.json
```

The script runs two concurrent requests and records real candidates, individual criterion scores, retries, Google response IDs and progress events. It verifies exact target equality, all 119 citation/evidence checks and score arithmetic. Credentials are read only at runtime. Rewriting can add latency and model cost compared with the earlier single-candidate flow; attempts are bounded.

# Decision-first model essay grading

## Incident — 14 October 2026

Cloud Run revision `stepwise-api-00041-wag` rejected the public target-5.5 request twice at 02:02:56 and 02:03:09 UTC with `Band matches do not support any score within the applicable limits`. This is a descriptor-decision consistency failure, not a transport timeout. The old log did not identify the failing criterion or retain the raw essay/decisions, so the exact conflicting statements cannot be reconstructed from that log.

## Simplified process

1. Generate a candidate from the learner's question, stance, ideas and target.
2. Independently compare all 119 official Task 2 statements and all bold limiting conditions. Four small criterion requests run in parallel. The assessor receives no target, writer plan or calibration history, and returns no numeric score, detailed skills, examples or per-statement explanations.
3. The server validates exact counts, allowable matches, real evidence references and conditional rules. It derives the highest fully supported integer score subject to caps for each criterion, then averages and rounds half up (e.g. 6/5/5/5 → 5.25 → 5.5). Only the failing criterion is retried once.
4. A candidate that misses the target goes directly to calibration. It does not generate the expensive final feedback.
5. Only a target-matching essay receives detailed feedback. The server fixes its score and exact assessed/next-band explanation slots before asking for advice, all 20 qualitative skill checks and examples. Feedback cannot output or modify score decisions. Only the failed feedback criterion is retried once. The existing complete assessment validator runs again before any result is returned.

The prompt explicitly distinguishes a lower proficiency threshold from a requirement to exhibit its weaknesses. Stronger writing can exceed a low row; absence of a low-level weakness must not produce a false cap. Explicit special eligibility conditions retain their original checks. No score is substituted from the user's requested target.

## Implementation

- `shared/model_assessment.py`: compact decisions, per-criterion retry, server-derived scoring and final-only feedback.
- `shared/band_matching.py`: same complete band rules, with explicit derivation before a model-supplied numeric score is required. Existing review paths still check score consistency by default.
- `shared/assessment.py`: calibrate candidates using decisions; complete detailed feedback only after exact target match.
- `tests/unit/test_model_assessment.py` and `tests/unit/test_targeting.py`: full compact fixture coverage, false refs, conditional skips, caps, immutable scores, isolated repairs and final-only feedback.

## Verification

138 Python unit tests pass. The tests use the complete 40-statement unit fixture, not the 119-statement production corpus. Real provider and public deployment verification are recorded separately; unit results alone do not establish live reliability or latency.

## Real host verification

Source `7d97df9766840556bcb57e1ef7459a43dfaeb7bf`, Gemini 3.5 Flash MINIMAL, index `339dcf75a711802b`: all 119 official statements and 20 qualitative skill checks passed, scores 7/5/6/6 and overall 6.0. Decision-only screening took 17.74 seconds including retrieval; final feedback completed at 68.89 seconds total. All eight logical calls succeeded on their first transport attempt. One CC feedback call took 50.874 seconds while the other three took 4.943–6.472 seconds, so provider latency remains variable. This is a real provider test on a previously saved 292-word public essay, not a whole-generation benchmark or a stable speedup claim. [Model response IDs, usage and timings](evidence/decision-first-host.json).

## Additional end-to-end failure and simplification

The first public run of the decision-first scorer (`7d97df9`, revision 00043) passed descriptor matching but later failed the existing local-edit writer protocol: `Each before span must occur exactly once and change`, followed by a real Google read timeout and ultimately `Model essay failed content or length checks`. This is retained as a failed run, not a successful public verification.

Source `4193eae` removes that brittle protocol from normal calibration: every revision returns a complete essay, with the original protected position sentence and requested ideas. It retains measured word-count checks, independent scoring, calibrated criterion control levels, five bounded candidates, private continuation and exact target matching. Local edit utilities remain available for historical checkpoints/tests; new requests no longer request replacement spans or edit-size budgets. Regression tests verify full-essay revision, preservation of the exact stance and length-repair inputs. All 138 Python tests pass.

## Faster model probe

A real `gemini-3.5-flash-lite` MINIMAL probe on the same saved essay passed structural/evidence checks in 7.95 seconds (screening 4.33 seconds), but produced a materially different 3/4/5/4 profile and overall 4.0, versus Flash's 7/5/6/6 and 6.0. This single example does not establish which scores are accurate; it demonstrates that format validation alone is insufficient for choosing a scoring model. Flash-Lite was not adopted as the assessor. Production retains Gemini 3.5 Flash MINIMAL. Google's [Flash-Lite documentation](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-5-flash-lite) describes its low-latency use cases; the probe here records actual project behavior separately from those product claims.

## Completed public verification

The fixed public URL completed target **5.5 → assessed 5.5** on source `4193eae45ede197c8083fbfec0f6b6c54e23507d`, revision `stepwise-api-00045-vos`, image `sha256:3d065d708e27e2f60cba7718e1cd9e96cf9e73a41a1078b3dfbf5311139993b6`. The 307-word essay received **7/5/4/6**, exact mean **5.50**, displayed overall **5.5**. The retained progress timer showed **81 seconds** for the entire generation/calibration/final-feedback run.

All four visible criterion panels were inspected: each contained an actionable next step, a before/after example, official band-descriptor links, and 5/5/6/4 qualitative checks. Assessed-band links pointed to the official descriptor PDF pages 7/8/9/8 respectively. [Public DOM receipt](evidence/decision-first-public.json), [criterion panel receipts](evidence/decision-first-public-details.json) and [completed screenshot](evidence/decision-first-result.png) preserve the actual outcome. The server contract enforces all 119 checks before returning this result; raw public model receipts were not exported.

This successful 81-second run is separately identified from the earlier failed local-edit run and from the 68.89-second host assessment. It is not a repeatable latency guarantee or a measured scoring-accuracy benchmark.

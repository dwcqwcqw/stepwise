# Closest independently assessed example

## Why the previous request failed

The public app reported that a requested Band 7.5 had not been matched after five independently assessed drafts. The previous policy rejected every non-identical overall score and discarded all usable candidates on exhaustion. This screenshot establishes target mismatch, not an inference/API outage; no historical per-candidate scores are inferred from the message.

The user explicitly selected the new behavior: show the closest already assessed example, with separate requested and actual scores.

## Current behavior

- Write toward the learner's selected target, preserving their stance and ideas.
- Independently assess the complete official rubric without showing the assessor the target or writing history. Four criterion scores and half-up averaging remain unchanged.
- Return an exact match immediately, if found.
- Otherwise retain the closest assessed candidate privately; allow at most two adjustments (three assessed drafts in total).
- If there is still no exact match, generate detailed feedback for the closest retained candidate and display its actual score. Never replace that score with the requested target.
- A later, worse draft cannot replace a closer earlier draft. Equal-distance candidates retain the earlier one. A later content/length failure can return the prior valid assessed candidate.
- `target_met` and `target_match.exact_match` remain false for an approximate result. The response identifies the selected attempt, distance from target and actual attempt history.
- All evidence/source checks remain mandatory. If final feedback fails validation, no unchecked result is returned.

Private continuation retains the best candidate in bounded, temporary server memory. The browser receives only an opaque continuation token until the final assessed example is ready.

## Verification

142 Python tests and six JavaScript tests pass. Regressions cover exact early matches, three-candidate exhaustion, truthful mismatched scores, preservation of a better earlier draft across continuation requests, invalid later content, and rejection of failed final feedback. Live production evidence is recorded separately.

## Real public verification

The original user input was preserved, the page refreshed to the new frontend, and the same public-transport prompt/stance/ideas were submitted with target **7.5**. Source `a68b7940b6def3498115326c33e561a5fdc2dba3`, Cloud Run revision `stepwise-api-00047-pib`, image `sha256:bee7a3a30aece16aeb1cca4648be945a10a9f8984a2d37d70f1ae7760bf3c33e`, Vercel deployment `dpl_J7Jyru6qBW19EhypfJA5RKcktrUB`.

The app returned a **292-word example**, separately assessed **8/8/8/9 → raw mean 8.25 → overall 8.5**, rather than a target-mismatch error. The notice explicitly states **target 7.5 / actual 8.5**, closest from **three assessed drafts**. The retained progress timer showed **42 seconds** for the whole run. Detailed feedback and official descriptor links were rendered. This is a successful approximate-result workflow, not an exact 7.5 match or a scoring-accuracy benchmark.

[Public DOM receipt](evidence/closest-example-public.json) and [completed screenshot](evidence/closest-example-result.png) preserve the result. Raw per-candidate server history was not exported from this public run; the minimum-distance selection and retention of earlier candidates are covered by the controlled regression cases. No speed guarantee is inferred from this single run.

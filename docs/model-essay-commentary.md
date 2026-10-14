# Model essays: target writing and qualitative commentary

## Current behavior

A user selects a target band, position and ideas. Stepwise retrieves the official Task 2 descriptors near the target integer writing profile, then asks Gemini to write at that level. A second, single Gemini call comments on the actual essay across TR, CC, LR and GRA. It returns four actionable next steps and examples plus all 20 qualitative skill details. It does **not** assess scores or compare candidate bands.

The displayed overall number is **Target band**, copied unchanged from the user's input. There are no numeric criterion grades, actual-score claim, mean formula, target-match claim, post-generation assessment or calibration rewrites. This policy supersedes the previous closest-assessed-candidate design.

## Source and implementation

- `shared/assessment.py::generate_essay`: target guidance, one writer call, content/length validation, then commentary.
- `shared/model_commentary.py`: one four-criterion feedback schema; exact evidence IDs; server-attached official target descriptors and 20 detail citations. No score fields or grading calls.
- `services/api/main.py`: one request for the complete generation/commentary flow, including its NDJSON stream.
- `services/web/static/app.js`: preset Target band, qualitative tabs, advice/examples and text download.
- `services/web/static/progress.js`: two real processing steps, no candidate continuation requests.

Normal successful generation requires **two model calls**, rather than repeated candidates with four scoring calls each. Transport retries remain bounded. Invalid content/length may trigger one writer repair; invalid commentary references may trigger one feedback repair. These are format/content checks, not numerical scoring. Generated commentary uses the already retrieved source context, avoiding a second rubric retrieval.

Submitted-draft `Review my writing` is unchanged: all 119 Task 2 descriptor statements are checked, four criterion scores and their mean are calculated, and source-linked advice is returned.

## Verification

Regression tests reject unknown essay references, missing criteria/details, unavailable target sources and score fields in commentary. Generation tests make old scoring entry points fail if invoked. Frontend tests require one generation request and preserve the preset target without an assessment result. Live deployment evidence is recorded separately after release.

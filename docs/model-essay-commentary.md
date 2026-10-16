# Model essays: target writing and qualitative commentary

## Current behavior

A user selects a target band. Position and ideas are optional and blank by default. The original typed/pasted essay is sent as `source_essay`: blank position preserves its stance, and blank ideas reuse its relevant arguments/examples. An explicit new position takes precedence over the original stance; existing arguments are adapted when necessary. Stepwise retrieves the official Task 2 descriptors near the target integer writing profile, then asks Gemini to write at that level. A second, single Gemini call comments on the actual essay across TR, CC, LR and GRA. It returns four actionable next steps and examples plus all 20 qualitative skill details. It does **not** assess scores or compare candidate bands.

The displayed overall number is **Target band**, copied unchanged from the user's input. There are no numeric criterion grades, actual-score claim, mean formula, target-match claim, post-generation assessment or calibration rewrites. This policy supersedes the previous closest-assessed-candidate design.

## Source and implementation

- `shared/assessment.py::generate_essay`: target guidance, one writer call, content/length validation, then commentary.
- `shared/model_commentary.py`: one four-criterion feedback schema; exact evidence IDs; server-attached official target descriptors and 20 detail citations. Every criterion observation/refinement and each skill detail must reference an official statement from the same criterion and target boundaries. No score fields or grading calls.
- `services/api/main.py`: one request for the complete generation/commentary flow, including its NDJSON stream.
- `services/web/static/app.js`: preset Target band, qualitative tabs, advice/examples and text download.
- `services/web/static/progress.js`: two real processing steps, no candidate continuation requests.

Normal successful generation requires **two model calls**, rather than repeated candidates with four scoring calls each. Transport retries remain bounded. Invalid content/length may trigger one writer repair; invalid commentary references may trigger one feedback repair. These are format/content checks, not numerical scoring. Generated commentary uses the already retrieved source context, avoiding a second rubric retrieval.

Submitted-draft `Review my writing` is unchanged: all 119 Task 2 descriptor statements are checked, four criterion scores and their mean are calculated, and source-linked advice is returned.

## Verification

Regression tests reject unknown essay references, missing criteria/details, unavailable target sources and score fields in commentary. Generation tests make old scoring entry points fail if invoked. Frontend tests require one generation request and preserve the preset target without an assessment result. Live deployment evidence is recorded separately after release.

## Real public verification — 14 October 2026

The fixed public URL completed a target-7.5 request with **311 words** in **16 seconds** on the retained browser elapsed timer. The UI displayed **Target band 7.5**, two progress steps, four qualitative criterion tabs, individual next steps and before/after refinements. All four panels were inspected, with 5/5/6/4 expandable skill details. The target-guidance link was verified against the official Band Descriptors, page 7. There was no generated score average or numeric criterion grade. This is one observed run, not a latency guarantee or a new scoring benchmark.

- Application source: `ab9e1a085377986057136692b0847c43483ee166`
- Cloud Run: `stepwise-api-00049-weh`, 100% traffic
- Image: `sha256:37276c47aba73c8665ade5c268d74d87ffd006c0669c3df3a14d8b0d296f9b38`
- Vercel: `dpl_AUeE6rxuycePFGRghD18Fsc5LoMz`, READY, public alias attached
- Local regression checks: 137 Python tests and six JavaScript tests passed; frontend build passed.
- [Public DOM receipt](evidence/commentary-public.json) · [Result](evidence/commentary-result.png) · [Two-step loading](evidence/commentary-two-step-progress.png)

No new examiner-agreement study was run. Submitted-draft grading was preserved in code and its existing regression checks; this public run exercised generation/commentary.

## Optional goals and original-essay context

The two goal fields are blank on first load and remain blank after loading a sample draft. Both are labeled optional and have no HTML `required` attribute. `source_essay` carries the current typed/pasted draft to generation. Blank fields preserve the original stance and relevant arguments; an explicit new position takes priority. Ideas can be overridden independently. Missing both original content and a position returns an input error rather than inventing the learner’s stance. Short or whitespace-only optional fields are normalized appropriately.

The backend and frontend were released from `cfbedd1144018d1572aa6c5205145c1622685823` (Cloud Run `stepwise-api-00051-dox`, Vercel `dpl_2odAcynqxJe6HUVXKsFNr5Vficbh`). Regression coverage includes omitted/blank/short optional fields and all four combinations of stance/idea inheritance or overrides. **146 Python and six JavaScript tests passed.** The frontend build passed. Public verification receipts are stored in `docs/evidence/optional-goals-public.json`; the default optional form is shown in `docs/evidence/optional-goals-defaults.png`.

Two real public requests used the same authored road-priority source essay. With both goals blank, the 301-word result preserved road maintenance as the primary spending priority (23 s on the retained UI timer). Entering an explicit public-transit-priority position, with ideas still blank, produced a 282-word result that changed the main priority and reused the rural road/hospital/school examples appropriately (17 s). These are two observed functional checks, not a timing benchmark.


## Target-specific commentary (v6.4)

For a 6.5 writing goal, all four commentary panels receive the official **Band 6 and Band 7** rows. For integer goals they receive that integer row. Observations and skill explanations are anchored to the lower integer band; the upper boundary is available for concrete development advice. There is no invented official half-band row, and the generation profile is not treated as an awarded criterion score.

Each observation and suggested refinement selects an exact official paragraph statement ID; every one of the 20 skill explanations does likewise. The server rejects IDs from another criterion or outside the target boundaries and attaches the unchanged official statement, band and PDF source metadata. The existing UI shows the corresponding official rows.

The coaching prompt requires qualified, passage-specific observations and concrete revisions, rather than global praise or claims of effortless mastery. Conditional weaknesses in a descriptor must not be asserted as actual mistakes without essay evidence. Where the text is correct, an optional practice improvement is appropriate. The summary uses neutral server text, preventing an unsupported model-generated overall endorsement.

The normal flow remains one writer call plus one qualitative feedback call, with a bounded format/evidence repair. There is no post-generation numerical reassessment. Reference validation checks provenance and scope; semantic interpretation remains model-generated and is inspected in the live sample receipt.

### v6.4 release verification

Source `39b5a4a`, production Cloud Run revision `stepwise-api-00060-bil`. All 179 unit tests passed. A real target-6.5 public-sample request produced 319 words in 31.889 seconds using two first-attempt model calls. All four observation references and 20 skill references were validated against official Band 6 statements; refinement references were constrained to Bands 6–7. No numerical reassessment was performed.

The fixed public website also completed the preserved learner session at target 6.5 in 26 seconds (25,436 ms server elapsed), producing 289 words. All four visible criterion panels were inspected. Learner essay text and screenshots are excluded from the public evidence. See [provider receipt](evidence/target-commentary-provider.json), [release receipt](evidence/target-commentary-release.json), and [public readiness](evidence/target-commentary-public-ready.json). These are individual observed runs, not a latency guarantee.

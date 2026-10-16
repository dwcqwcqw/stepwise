# Official assessment knowledge

MS2 ingests **official assessment resources only**. The 8,049-record essay candidate collection is reserved for MS3 adaptation; its manifest is in `data/ms3/sources.lock.json` and is not read by the running pipeline.

| Source | What is indexed | Authority |
|---|---|---|
| [IELTS Writing Band Descriptors](https://ielts.org/cdn/ielts-guides/ielts-writing-band-descriptors.pdf) | All nine PDF pages; 80 criterion-band cells and 238 PDF-paragraph statements covering both tasks and bands 0–9; merged Band 0 rule; rating instructions and bold limiting features | Primary band scale, May 2023 |
| [IELTS Writing Key Assessment Criteria](https://ielts.org/cdn/ielts-guides/ielts-writing-key-assessment-criteria.pdf) | Task 2 definitions, shared response-format rules and all 20 detailed checks: TR 5, CC 5, LR 6, GRA 4 | Primary explanation of assessment criteria |

Downloads are checksum-verified against `data/sources.lock.json`. Raw PDFs and the complete extracted text remain in ignored runtime storage. Source URLs, pages, hashes, dates and stable chunk IDs accompany every vector.

## Coverage and boundaries

The full source library contains **359 chunks**: 238 paragraph statements, 80 parent band cells, 20 subcriteria, five criterion definitions, seven rating-rule chunks, nine full source pages. Page chunks preserve complete PDF coverage; criterion chunks provide precise retrieval. The same content may therefore be represented at both page and criterion level. PDF paragraph blocks define statement boundaries. Line wraps are joined, qualifications remain with their positive feature, and bold limiting spans are retained. A separate table extraction must exactly equal the concatenated paragraph text for every cell; centre-in-cell filtering prevents neighbouring-row glyphs from leaking into a chunk. Each statement has a stable ID, independent vector, parent-cell ID and physical PDF page. Overlap is zero.

Both tasks are indexed to preserve the complete requested PDF. **The application assesses Task 2 only.** Its scoring context retrieves the complete 0–9 band ladder for each of TR/CC/LR/GRA, all detailed definitions/checks and applicable rating rules, with a task filter that excludes Task 1. Mandatory coverage uses filtered Qdrant retrieval so semantic top-k cannot silently drop low bands or a criterion.

Target-band retrieval is used for generation and the retrieval demonstration. The assessor never receives the user's target band: its score must be based on the essay. The four criteria are assessed independently in parallel. Each call checks all ten official integer bands, every paragraph (TR 32; CC 33; LR 28; GRA 26) and each bold limiting condition. The server rejects missing/duplicate statements, cross-band IDs, unsupported skipped checks, invented essay excerpts, and scores inconsistent with the highest fully supported band or an applicable limiting condition. One repair is allowed per criterion. These judgments test compatibility with positive requirements and permitted weaknesses, rather than requiring the essay to exhibit weaknesses listed in a lower band.

Four criterion scores are whole numbers. Their exact arithmetic mean is preserved and displayed before conversion to a half-band Task 2 practice estimate using decimal half-up arithmetic: 6.25 → 6.5; 6.75 → 7.0. The UI shows the four inputs, sum/divisor, raw mean and rounded result for both draft and generated essay. No half-band descriptor rows or numerical paragraph sub-scores are invented. This is not a full Writing-section result combining Tasks 1 and 2.

The 20 qualitative detailed checks are **not** official individually scored bands. The model supplies a judgment and evidence for each; the server attaches the exact official wording and source link.

## Versions

Source snapshot: `f58ab6f2ce4fb7a9`. Paragraph chunk snapshot: `6f021ec96cdbaa7a`. The earlier `52814016b8103614` snapshot and 131-point evidence are historical, preceding paragraph matching. Index identity additionally hashes the actual ONNX embedding weights and dependency configuration. Repeated upserts use stable UUIDs and exact count checks. See generated `docs/evidence/index.json` for the verified runtime index.

MS3 will audit candidate essay reuse, label provenance, near duplicates, prompt families and prompt/essay alignment before fine-tuning. MS2 neither downloads that collection nor uses its essays, labels or generated advice for assessment.

## User-facing evidence

Current/next-band matches are shown first, each with the exact official statement, a qualitative judgment, an explanation, an original essay passage and the Band Descriptors PDF page link. All remaining band reviews are available in a separate expandable section. The generic Key Assessment Criteria checklist is supplementary. A model essay uses the same complete, target-blind assessment workflow after generation.

The [official scoring explanation](https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail) establishes equal criterion weights and averaging for each writing task. Its .25/.75 rounding description refers to the overall four-skill IELTS result; Stepwise explicitly labels its half-band conversion a Task 2 practice estimate, rather than claiming an independently reported official task result.

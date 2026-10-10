# Official assessment knowledge

MS2 ingests **official assessment resources only**. The 8,049-record essay candidate collection is reserved for MS3 adaptation; its manifest is in `data/ms3/sources.lock.json` and is not read by the running pipeline.

| Source | What is indexed | Authority |
|---|---|---|
| [IELTS Writing Band Descriptors](https://ielts.org/cdn/ielts-guides/ielts-writing-band-descriptors.pdf) | All nine PDF pages; 80 criterion-band cells covering both tasks and bands 0–9; merged Band 0 rule; rating instructions and bold limiting features | Primary band scale, May 2023 |
| [IELTS Writing Key Assessment Criteria](https://ielts.org/cdn/ielts-guides/ielts-writing-key-assessment-criteria.pdf) | Task 2 definitions, shared response-format rules and all 20 detailed checks: TR 5, CC 5, LR 6, GRA 4 | Primary explanation of assessment criteria |
| [British Council: Answer the Question](https://takeielts.britishcouncil.org/sites/default/files/writing_task_2_-_answer_the_questions.pdf) | Official question-analysis and relevance guidance, preserved by page | Supplementary teaching guidance, 2013; cannot override current band descriptors |

Downloads are checksum-verified against `data/sources.lock.json`. Raw PDFs and the complete extracted text remain in ignored runtime storage. Source URLs, pages, hashes, dates and stable chunk IDs accompany every vector.

## Coverage and boundaries

The full source library contains **131 chunks**: 80 band cells, 20 subcriteria, five criterion definitions, seven rating-rule chunks, nine full source pages and ten teaching-resource pages. Page chunks preserve complete PDF coverage; criterion chunks provide precise retrieval. The same content may therefore be represented at both page and criterion level. Chunk overlap within each table cell or detailed bullet is zero.

Both tasks are indexed to preserve the complete requested PDF. **The application assesses Task 2 only.** Its scoring context retrieves the complete 0–9 band ladder for each of TR/CC/LR/GRA, all detailed definitions/checks and applicable rating rules, with a task filter that excludes Task 1. Semantic retrieval adds up to two supplementary teaching pages. Mandatory coverage uses filtered Qdrant retrieval so semantic top-k cannot silently drop low bands or a criterion.

Target-band retrieval is used for generation and the retrieval demonstration. The assessor never receives the user's target band: its score must be based on the essay. Four criterion scores are whole numbers; the interface reports their mean rounded to the nearest half band as a Task 2 practice estimate. This is not a full Writing-section result combining Tasks 1 and 2.

The 20 qualitative detailed checks are **not** official individually scored bands. The model supplies a judgment and evidence for each; the server attaches the exact official wording and source link.

## Versions

Source snapshot: `3aea32a1828dd022`. Verified cloud chunk snapshot: `52814016b8103614`. Index identity additionally hashes the actual ONNX embedding weights and dependency configuration. Repeated upserts use stable UUIDs and exact count checks. See generated `docs/evidence/index.json` for the verified runtime index.

MS3 will audit candidate essay reuse, label provenance, near duplicates, prompt families and prompt/essay alignment before fine-tuning. MS2 neither downloads that collection nor uses its essays, labels or generated advice for assessment.

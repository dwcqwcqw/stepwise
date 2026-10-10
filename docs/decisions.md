# Engineering decisions

- **Full official knowledge coverage:** index the complete nine-page descriptor PDF, while task metadata keeps Task 1 out of Task 2 scoring. Preserve merged Band 0 rules and bold limiting features.
- **Fine-grained evidence:** index the official Key Assessment Criteria definitions and all 20 detailed checks. Supplement with British Council relevance guidance; current descriptors take precedence over older teaching materials.
- **Hybrid retrieval:** mandatory filtered retrieval provides complete band ladders, definitions and subcriteria; semantic search adds relevant teaching guidance. A tiny official corpus should not lose required rules to arbitrary top-k truncation.
- **Blind scoring:** the target band is used by generation, never by the assessor. A generated essay is scored in a fresh call that receives only the question, finished prose and independently retrieved standards.
- **No fabricated success:** return an error when the model cannot respond or evidence fails validation. Validate four criterion scores, all 20 checks, awarded/next-band citations, known source IDs and verbatim essay excerpts.
- **Candidate data belongs to MS3:** its pinned manifest is separate from MS2 ingestion. No candidate essays or scores influence the official assessment knowledge base.
- **Runtime authorization:** existing gcloud session, short-lived tokens in memory-backed storage, read-only API mount, no saved long-lived keys.
- **Container contracts:** five custom Python/uv containers and Qdrant. Frozen locks, source hashes, embedding fingerprint and stable upserts preserve reproducibility. Google model responses can vary even with a low temperature; receipts record model versions and usage.
- **Teacher references:** cheese-app-v0 informed separation of ingestion/chunking/indexing/application. babykev informed locked environments, contracts and documented experiments. The IELTS schema, retrieval and UI are specific to Stepwise.

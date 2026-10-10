# MS2 TF presentation · 15 minutes

Every member should understand the entire implementation. Use current evidence receipts to describe what was actually run; historical preview receipts are stored separately.

1. **Scope (1 min):** typed IELTS Academic Task 2 essays, four scores, specific revisions and tailored model essays.
2. **Architecture (2 min):** five Python/uv containers, Qdrant, FastAPI gateway, Vertex Gemini and validated output.
3. **Official knowledge (2 min):** three attributed sources; full nine-page band PDF, bands 0–9, all 20 detailed checks; 131 chunks. The 8,049 candidate essays are reserved for MS3 and not ingested.
4. **Retrieval (2 min):** mandatory complete Task 2 band ladders plus semantic teaching guidance; task filtering; half-band mapping; source/page/chunk lineage.
5. **Assessment (2 min):** target-blind scoring, exact quotations, source IDs, whole criterion bands, qualitative subcriteria and before/after revisions. Inspect actual model receipts if available.
6. **Application (3 min):** question/draft -> feedback -> target/position/ideas -> complete generated essay -> a separate blind assessment. A configured endpoint is not evidence of successful inference; disclose any unresolved project authorization.
7. **Reproducibility (2 min):** make run, source/model hashes, frozen locks, runtime authorization, logs and tests.
8. **MS3 (1 min):** reliable adaptation data, prompt-family leakage audit, open-model baseline/LoRA, scoring agreement and repeatability evaluation.

Q&A: why all bands are retrieved during scoring, why the assessor never sees target or generator notes, why a target is not a guaranteed result, how source/excerpt validation works, how model error differs from fallback templates, why the library includes Task 1 but the scorer excludes it, and what integration tests cannot establish about grading accuracy.

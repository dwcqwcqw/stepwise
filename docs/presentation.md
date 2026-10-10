# MS2 TF presentation · 15 minutes

Every member should explain every section; this is a shared-understanding guide.

1. **Scope (1 min):** typed IELTS argument essays, four criteria, target-band examples and MS2 boundary.
2. **Architecture (2 min):** README diagram, Compose stages, gateway/API/database flow.
3. **Data (2 min):** lock/checksums, official knowledge versus candidate essays, quality receipt and grouped splits.
4. **Chunks/vectors (2 min):** source table cell, metadata, 384-dimensional embedding and collection ID.
5. **Retrieval (2 min):** `make verify`; show 6.5 TR retrieving 6 and 7. Explain why similarity is not a band score.
6. **App (3 min):** sample draft, all criteria, goals and downloadable writing brief; show live/pending features.
7. **Reproducibility (2 min):** `make run`, locks, logs, screenshots, tests and persistent storage; navigate to files.
8. **Next milestone (1 min):** data approval, baseline/LoRA experiments, scoring/generation/evaluation.

Q&A: metadata filters, half-band mapping, idempotent upserts, source changes, prompt leakage, readiness versus health, private DB access and what trained scoring requires beyond retrieval.

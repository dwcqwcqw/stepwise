# Design decisions and reference projects

[Cheese App v0](https://github.com/dlops-io/cheese-app-v0) separates chunk/embedding/loading, FastAPI and a frontend; its reference uses Chroma, Vertex embeddings/Gemini, Next.js and mixed package tools. We retain inspectable pipeline stages with Stepwise-specific data and uniform uv projects.

[babykev](https://github.com/rahuldave/babykev) illustrates typed contracts, uv locks, Docker environments, smoke tests and documentation around Qwen2.5-0.5B/LoRA and a pointer head. Its current smoke uses untrained components. We adopt its engineering principles, not its predictions or task.

- **Qdrant:** explicit payload filtering, independent HTTP DB and persistent versioned collections; the RAG concepts transfer directly from the course example.
- **CPU BGE/FastEmbed:** reproducible vectorization without private API keys, a GPU or new service-account credentials.
- **Complete rubric cells:** preserve task/criterion/band relationships rather than split arbitrary windows.
- **Five small Python containers:** isolate PDF/parquet ingestion, lightweight chunking, ONNX indexing, API and web gateway. Every one has pyproject/uv locks.
- **Plain HTML/CSS/JS:** demonstrates four real interactions without a second package ecosystem; the typed API allows future frontend changes.
- **Honest model boundary:** retrieving rubric context is not essay scoring. Scores remain null, templates are labeled, and full generation is staged for MS3.

Next: compare general prompting, rubric RAG and open-weight LoRA adaptation after data approval/leakage checks. Evaluate held-out score MAE, within-0.5 agreement, variance and quote/citation validity separately from fluency. Add experiment tracking, scalable training/serving, CI/CD and monitored updates in later milestones.

# Executed MS2 evidence

Captured on 10 October 2026 from an actual Google Cloud Shell Linux/amd64 session. Verified implementation: `1810c5a031e54ed28cd42740062b340b585d1242`.

- `pipeline.log`: actual Compose logs, including the initial transient embedding download retry and subsequent successful runs.
- `containers.jsonl`, `docker-version.json`, `cloud-running*.jpg`: actual environment state; batch stages exit 0, API/web/Qdrant are healthy.
- `data_quality.json`, `chunking.json`, `index.json`: executed stage receipts and data/index identities.
- `sample_input.json` -> `feedback_output.json`: authored 273-word example and four criterion/context results.
- `retrieval_example.json`: real HTTP query -> target/criterion filters -> two official source chunks.
- `model_essay_request.json` -> `model_essay_output.json`: preserved user requirements and writing brief; model generation is explicitly pending.
- `verification.json`: eight live integration checks passed after `make run` and `make evidence`.
- `unit-tests.txt`: nine local contract/invariant tests passed.
- `app-*.jpg`: actual live UI screenshots. `*-detail.jpg` crop the visible application content for readable report figures; originals retain the full page.

The pipeline was rerun without changing its 24-point index. This is development evidence, not a scoring-accuracy or performance benchmark. Raw source essays, credentials and browser authentication state are excluded.

The cloud evidence archive was transferred without alteration; its SHA-256 was verified as `9cd672276744d20b84dd51809b3cc08a382a0b6d55d2e21604a8b235e0079489` before extraction. Screenshots and the local test receipt were added separately.

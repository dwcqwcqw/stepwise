# Run Stepwise in Google Cloud Shell

Prerequisites: Docker Engine + Compose v2 or newer, make, Python 3, gcloud signed into your authorized account, outbound HTTPS, and a Google Cloud project with billing and Vertex AI API already available. Host `uv` is needed only for `make test`.

```bash
git clone --branch milestone2 https://github.com/dwcqwcqw/stepwise.git
cd stepwise
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
export GEMINI_MODEL=gemini-3.8-flash
export STEPWISE_AUTH_DIR=/dev/shm/stepwise-auth
python3 scripts/cloud-auth.py > /tmp/stepwise-auth.log 2>&1 &
make run
```

The auth helper reads the existing gcloud session and refreshes a short-lived access token every 20 minutes in memory-backed `/dev/shm`. The directory is mode 0700, its token is 0600, and only the API container receives a read-only mount. Tokens are never printed, embedded in an image, added to Git or passed to the browser. Keep the helper alive while the demo runs. It does not create API keys or service-account keys. On hosts without `/dev/shm`, provide a private temporary directory through `STEPWISE_AUTH_DIR` and remove it after stopping the demo.

`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` and `GEMINI_MODEL` are ordinary configuration, not secrets. `GEMINI_MODEL` is configurable because availability differs between projects and model lifecycles. The evidence receipt records the model actually used; a configured model name alone does not prove successful inference.

Open http://localhost:8080, or Cloud Shell Web Preview on port 8080. API docs: http://localhost:8000/docs. The first run downloads three official PDFs and embedding weights. No essay training corpus is downloaded.

`make run` builds and starts the full container pipeline, then makes **real billable model calls** for draft feedback, essay generation, separate essay assessment and a distinct weak draft. It writes sample inputs/outputs and receipts to `runtime/artifacts`. It fails if Google authorization, the model, citations, excerpts or required criteria are unavailable; there is no template fallback.

- `make verify`: repeat the real integration checks (calls Google again).
- `make test`: local deterministic contract/evidence tests, no Google calls.
- `make evidence`: capture current logs and previously verified artifacts; does not repeat paid calls.
- `make logs`: show container logs.
- `make stop`: stop services while retaining data; stop the auth helper afterward.

## Troubleshooting

- HTTP 401: verify your signed-in gcloud session and restart the auth helper.
- HTTP 403 / `SERVICE_DISABLED`: inspect the selected project's Vertex API, billing and your permissions. Resolve access in the intended project; do not switch to another organization's project merely because it is listed.
- HTTP 404: check model availability and `GEMINI_MODEL` against Google's official model documentation.
- HTTP 429/5xx: bounded retries are built in; rerun once the project's quota/service recovers.
- Source hash drift: inspect the updated official source and audit it before changing the lock.
- Official PDF download blocked: some cloud regions receive HTTP 403 from the British Council website. Download the same public PDF from its official URL on an accessible connection, then copy it to `runtime/data/raw/bc-task2-answer-the-question.pdf` before restarting Compose. The ingestion container still verifies the exact SHA-256 in `data/sources.lock.json`; do not substitute another file or change the hash to suppress the error. The verified cloud run used this cache path for the supplementary British Council PDF.
- Evidence validation failure: the assessor selects short essay-span IDs; the server resolves exact original text and attaches verified official rubric records. One repair receives the prior answer and field-level errors. An exhausted repair remains a 503 with the draft preserved. Inspect `assessment_validation_retry` in API logs; these diagnostics contain validation paths/reasons, not learner passages. Run `make test` for the reference, Unicode, unknown-ID and repair regression checks.

Google Cloud Shell provides a temporary development VM and authenticated preview, not persistent production hosting. API/web ports bind to loopback, and Qdrant has no host-published port. Stepwise does not persist learner submissions; Google receives text to perform inference under the selected Cloud project.

## Verified project and artifact ownership

The live run used `stepwise-ac215-20261010` in Harvard’s `self-paid` folder with Vertex AI enabled. An authorized account must have access to the selected project; cloning code does not grant Google Cloud permissions.

If a previous Docker run created root-owned artifact files, restore ownership of only the generated artifact directory before verification: `sudo chown -R "$(id -u):$(id -g)" runtime/artifacts`. A fresh clone creates this directory as the invoking user.

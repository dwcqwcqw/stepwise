# Environment setup

## Local

Install Docker Desktop/Engine, Compose v2+, Python, Make and [uv](https://docs.astral.sh/uv/). Start the Docker daemon and check `docker version` and `docker compose version`. Clone `milestone2` and run `make run`. No secrets are required. Docker Desktop or a running Colima VM provides Linux containers on macOS; use WSL2 on Windows.

`make test` builds `services/api/.venv` from its lock and runs offline contracts/chunking tests. Real embeddings and vector DB checks run via `make verify` against the full container system.

## Google Cloud Shell

Cloud Shell's temporary Linux VM supports the CPU pipeline without creating a billable Compute Engine instance or choosing a billing project. Home storage persists within Cloud Shell limits; running sessions are temporary. This is a reproducible development demonstration, not a production deployment.

1. Activate Cloud Shell in the existing course Google Cloud session; authorize the existing login if prompted. The app itself uses no Google credentials.
2. Run:

```bash
git clone --branch milestone2 https://github.com/dwcqwcqw/stepwise.git
cd stepwise
make run
make evidence
```

3. Open Cloud Shell Web Preview on port **8080**, using its authenticated proxy. No public firewall change is needed.
4. Capture `docker compose ps -a` and the app for evidence. Download evidence if needed.
5. `make stop` ends the development containers while preserving the data cache.

Cloud Shell has session, disk and memory quotas. A longer session can use a Linux VM in an explicitly selected billing project with Docker/Compose and the same command. A paid VM is not needed for MS2.

## Failure recovery

- Checksum mismatch: inspect the source change before updating the lock or replacing the affected cached file.
- Failed stage: inspect `docker compose logs ingest chunk index`, resolve the error, rerun `make run`.
- Model unavailable: check outbound Hugging Face access; the shared model cache avoids repeat downloads.
- API unready: check `/ready` and DB/index logs. A healthy HTTP process alone does not prove indexing succeeded.
- Port conflict: change the host port mapping and set `STEPWISE_URL` for verification.
- Use `make stop` for routine cleanup; retain runtime data/DB directories.

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/verify.py
mkdir -p docs/evidence
docker compose logs --no-color > docs/evidence/pipeline.log
docker compose ps -a --format json > docs/evidence/containers.jsonl
docker version --format '{{json .}}' > docs/evidence/docker-version.json
cp runtime/artifacts/*.json docs/evidence/
echo "Evidence refreshed in docs/evidence. Inspect before committing; never copy raw essays or credentials."

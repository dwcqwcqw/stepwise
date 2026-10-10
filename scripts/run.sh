#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runtime/artifacts runtime/data runtime/model-cache runtime/qdrant
docker compose up --build -d
python3 scripts/verify.py
docker compose logs --no-color > runtime/artifacts/pipeline.log
docker compose ps -a --format json > runtime/artifacts/containers.jsonl
echo "Stepwise is ready: http://localhost:8080 | API: http://localhost:8000/docs"

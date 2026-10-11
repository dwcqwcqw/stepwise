#!/usr/bin/env bash
set -euo pipefail
mkdir -p .cloudrun-bundle/data/processed .cloudrun-bundle/model-cache
# Export only the frozen official rubric vectors, never learner essays or authorization.
docker compose exec -T api python - <<'PY' > .cloudrun-bundle/data/processed/points.json
import json
from shared.retrieval import database,active_index
rows=[];offset=None
while True:
    batch,offset=database().scroll(active_index()['collection'],limit=256,offset=offset,with_vectors=True)
    rows.extend(batch)
    if offset is None:break
assert len(rows)==active_index()['points']
print(json.dumps([{'id':str(p.id),'vector':p.vector,'payload':p.payload} for p in rows]))
PY
cp runtime/data/processed/index.manifest.json .cloudrun-bundle/data/processed/
cp -a runtime/model-cache/. .cloudrun-bundle/model-cache/
python3 - <<'PY'
import hashlib,json,pathlib
p=pathlib.Path('.cloudrun-bundle')
files={str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob('*')) if f.is_file() and f != p/'manifest.json'}
pathlib.Path('.cloudrun-bundle/manifest.json').write_text(json.dumps(files,indent=2)+'\n')
print('Official RAG bundle exported:',len(files),'files')
PY

"""Reparse the two pinned PDFs and reuse only byte-identical indexed chunks.

Run with the ingestion environment in a checkout containing the previous frozen
bundle. Unchanged text/IDs keep their existing embeddings and frozen model.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['DATA_DIR'] = str(ROOT/'runtime/data')
os.environ['ARTIFACTS_DIR'] = str(ROOT/'runtime/artifacts')
from services.ingest.main import main as ingest
from services.chunk.main import main as chunk
from shared.corpus import validate_points

bundle = ROOT/'.cloudrun-bundle'
processed = bundle/'data/processed'
old_index = json.loads((processed/'index.manifest.json').read_text())
old_points = {p['payload']['chunk_id']:p for p in json.loads((processed/'points.json').read_text())}
weights = sorted((bundle/'model-cache').rglob('*.onnx'))
assert weights and hashlib.sha256(weights[0].read_bytes()).hexdigest()==old_index['weights_sha256']
ingest()
chunk()
runtime = ROOT/'runtime/data/processed'
chunks = [json.loads(line) for line in (runtime/'chunks.jsonl').read_text().splitlines()]
points = []
for payload in chunks:
    previous = old_points[payload['chunk_id']]
    assert previous['payload']==payload, 'Changed chunk requires embedding again'
    assert len(previous['vector'])==old_index['dimension']==384
    points.append(previous)
validate_points(points)
chunk_manifest = json.loads((runtime/'chunks.manifest.json').read_text())
config = {key:old_index[key] for key in ['model','weights_sha256','fastembed','dimension','metric']}
config['chunk_snapshot'] = chunk_manifest['chunk_snapshot']
index_id = hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()[:16]
index = {**config,'index_id':index_id,'collection':f'stepwise_{index_id}',
         'points':len(points),'qdrant_client':old_index['qdrant_client']}
(processed/'points.json').write_text(json.dumps(points)+'\n')
(processed/'index.manifest.json').write_text(json.dumps(index,indent=2)+'\n')
files = {str(p.relative_to(bundle)):hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(bundle.rglob('*')) if p.is_file() and p!=bundle/'manifest.json'}
(bundle/'manifest.json').write_text(json.dumps(files,indent=2)+'\n')
receipt = {'status':'passed','index':index,'sources':sorted({p['payload']['source_id'] for p in points}),
           'verified_identical_embeddings_reused':len(points),'removed_points':len(old_points)-len(points),
           'descriptor_cells':sum(p['payload']['kind']=='band_descriptor' for p in points),
           'task2_statements':sum(p['payload']['kind']=='band_statement' and p['payload']['task']=='academic_task_2' for p in points)}
(ROOT/'runtime/artifacts/two-source-cleanup.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))

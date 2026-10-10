"""Embed a versioned chunk snapshot, idempotently upsert, verify and query."""
import importlib.metadata
import json
import uuid
from pathlib import Path
from qdrant_client import models
from shared.common import DATA, ARTIFACTS, digest, log, read_json, write_json
from shared.retrieval import MODEL, DIMENSION, database, embedder, retrieve

def main():
    chunks = [json.loads(x) for x in (DATA/'processed/chunks.jsonl').read_text().splitlines()]
    manifest = read_json(DATA/'processed/chunks.manifest.json')
    model = embedder()
    vectors = [v.tolist() for v in model.embed([c['text'] for c in chunks])]
    import os
    files = sorted(Path(os.getenv('MODEL_CACHE','/cache')).rglob('*.onnx'))
    if not files: raise ValueError('Missing ONNX model file; cannot record embedding fingerprint')
    weights_sha256 = digest(files[0].read_bytes())
    config = {'chunk_snapshot':manifest['chunk_snapshot'],'model':MODEL,'weights_sha256':weights_sha256,'fastembed':importlib.metadata.version('fastembed'),'dimension':DIMENSION,'metric':'cosine'}
    index_id = digest(json.dumps(config,sort_keys=True).encode())[:16]
    collection = f'stepwise_{index_id}'
    db = database()
    if not db.collection_exists(collection):
        db.create_collection(collection,vectors_config=models.VectorParams(size=DIMENSION,distance=models.Distance.COSINE))
    points = [models.PointStruct(id=str(uuid.UUID(c['chunk_id'][:32])),vector=v,payload=c) for c,v in zip(chunks,vectors,strict=True)]
    db.upsert(collection_name=collection,points=points,wait=True)
    count = db.count(collection_name=collection,exact=True).count
    if count != len(chunks): raise ValueError(f'Index count mismatch {count} != {len(chunks)}')
    result = {**config,'index_id':index_id,'collection':collection,'points':count,'qdrant_client':importlib.metadata.version('qdrant-client')}
    write_json(DATA/'processed/index.manifest.json',result)
    write_json(ARTIFACTS/'index.json',result)
    example = retrieve('How can I extend my main ideas and support my position with relevant examples?', 'TR', 6.5)
    if not example['matches']: raise ValueError('No context returned by retrieval smoke example')
    write_json(ARTIFACTS/'retrieval_example.json',example)
    log('index_complete',**result)
    log('retrieval_verified',query=example['query'],criterion='TR',target_band=6.5,returned=len(example['matches']),chunk_ids=[x['chunk_id'] for x in example['matches']])

if __name__ == '__main__': main()

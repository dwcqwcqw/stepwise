"""CPU ONNX embeddings and metadata-filtered Qdrant retrieval."""
import os
from functools import lru_cache
from fastembed import TextEmbedding
from qdrant_client import QdrantClient, models
from shared.common import DATA, CRITERIA, read_json

MODEL = "BAAI/bge-small-en-v1.5"
DIMENSION = 384

@lru_cache
def embedder():
    return TextEmbedding(model_name=MODEL, cache_dir=os.getenv('MODEL_CACHE','/cache'), threads=2)

@lru_cache
def database():
    return QdrantClient(url=os.getenv('QDRANT_URL','http://qdrant:6333'),timeout=60)

def active_index():
    return read_json(DATA/'processed/index.manifest.json')

def retrieve(query: str, criterion: str, target_band: float, top_k: int = 2) -> dict:
    if criterion not in CRITERIA: raise ValueError('Unknown criterion')
    # Official descriptors use integer bands. For 6.5, retrieve both 6 and 7.
    lower = int(target_band)
    upper = min(9, lower + (target_band > lower))
    index = active_index()
    vector = list(embedder().query_embed(query))[0].tolist()
    found = database().query_points(collection_name=index['collection'],query=vector,limit=top_k,query_filter=models.Filter(must=[models.FieldCondition(key='criterion',match=models.MatchValue(value=criterion)),models.FieldCondition(key='band',range=models.Range(gte=lower,lte=upper)),models.FieldCondition(key='task',match=models.MatchValue(value='academic_task_2'))])).points
    return {'query':query,'criterion':criterion,'target_band':target_band,'filters':{'task':'academic_task_2','criterion':criterion,'bands':list(range(lower,upper+1))},'index_id':index['index_id'],'embedding_model':MODEL,'collection':index['collection'],'matches':[{'similarity':p.score,**p.payload} for p in found]}

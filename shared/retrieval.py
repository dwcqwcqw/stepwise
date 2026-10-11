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
    # Production images ship a frozen model cache; do not make cold starts
    # depend on Hugging Face availability or metadata rate limits.
    return TextEmbedding(model_name=MODEL, cache_dir=os.getenv('MODEL_CACHE','/cache'), threads=2,
                         local_files_only=os.getenv('QDRANT_MODE') == 'bundled')

@lru_cache
def database():
    if os.getenv('QDRANT_MODE') == 'bundled':
        # Cloud Run replicas each load the same immutable official corpus.
        # The containerized MS2 pipeline continues to use the Qdrant server.
        index = active_index()
        points = read_json(DATA/'processed/points.json')
        if len(points) != index['points']: raise ValueError('Incomplete bundled index')
        db = QdrantClient(location=':memory:')
        db.create_collection(index['collection'], vectors_config=models.VectorParams(size=DIMENSION,distance=models.Distance.COSINE))
        db.upsert(index['collection'], points=[models.PointStruct(**p) for p in points], wait=True)
        return db
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
    found = database().query_points(collection_name=index['collection'],query=vector,limit=top_k,query_filter=models.Filter(must=[models.FieldCondition(key='kind',match=models.MatchValue(value='band_descriptor')),models.FieldCondition(key='criterion',match=models.MatchValue(value=criterion)),models.FieldCondition(key='band',range=models.Range(gte=lower,lte=upper)),models.FieldCondition(key='task',match=models.MatchValue(value='academic_task_2'))])).points
    return {'query':query,'criterion':criterion,'target_band':target_band,'filters':{'task':'academic_task_2','criterion':criterion,'bands':list(range(lower,upper+1))},'index_id':index['index_id'],'embedding_model':MODEL,'collection':index['collection'],'matches':[{'similarity':p.score,**p.payload} for p in found]}


def assessment_context(query: str) -> dict:
    """Retrieve each complete band ladder plus fine-grained official definitions.

    Scoring must not use the learner's requested score as a retrieval filter.
    The mandatory structured retrieval prevents semantic top-k from losing low bands.
    Supplemental guidance is retrieved semantically from the same vector database.
    """
    index=active_index();db=database()
    mandatory,offset=db.scroll(index['collection'],scroll_filter=models.Filter(must=[models.FieldCondition(key='task',match=models.MatchAny(any=['academic_task_2','shared'])),models.FieldCondition(key='kind',match=models.MatchAny(any=['band_descriptor','criterion_definition','subcriterion','rating_rule']))]),limit=256,with_vectors=False)
    if offset is not None: raise ValueError('Assessment context exceeds configured retrieval limit')
    chunks=[p.payload for p in mandatory]
    for code in CRITERIA:
        ladder=[x for x in chunks if x['kind']=='band_descriptor' and x['criterion']==code]
        if {x['band'] for x in ladder}!=set(range(10)): raise ValueError('Full Task 2 band ladder required')
        if any(not x.get('statements') for x in ladder):raise ValueError('Paragraph-level descriptor index required')
    vector=list(embedder().query_embed(query[:4000]))[0].tolist()
    ranked=db.query_points(collection_name=index['collection'],query=vector,limit=2,query_filter=models.Filter(must=[models.FieldCondition(key='task',match=models.MatchValue(value='academic_task_2')),models.FieldCondition(key='kind',match=models.MatchValue(value='teaching_guidance'))])).points
    chunks.extend({'similarity':p.score,**p.payload} for p in ranked)
    chunks=sorted({x['chunk_id']:x for x in chunks}.values(),key=lambda x:(x['criterion'],x['kind'],x.get('band') or 0,x['chunk_id']))
    return {'index_id':index['index_id'],'collection':index['collection'],'chunks':chunks,'retrieval_strategy':'complete_task2_ladders_and_subcriteria_plus_semantic_guidance','target_blind':True}

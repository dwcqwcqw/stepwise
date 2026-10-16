"""Exercise the two deployment boundaries that differ from Compose."""
import json
import pytest
import httpx
from shared import retrieval, gemini

def test_bundled_qdrant_preserves_vector_payload(tmp_path,monkeypatch):
    p=tmp_path/'processed';p.mkdir()
    (p/'index.manifest.json').write_text(json.dumps({'collection':'frozen','points':359}))
    payload={'chunk_id':'rubric-1','task':'academic_task_2','criterion':'TR','band':7,
             'source_id':'ielts-writing-band-descriptors-2023','kind':'band_descriptor'}
    points=[{'id':i+1,'vector':([1.0]+[0.0]*383 if i==0 else [0.0,1.0]+[0.0]*382),
             'payload':{**payload,'source_id':'ielts-writing-band-descriptors-2023' if i<333 else 'ielts-key-assessment-criteria'}}
            for i in range(359)]
    (p/'points.json').write_text(json.dumps(points))
    monkeypatch.setenv('QDRANT_MODE','bundled');monkeypatch.setattr(retrieval,'DATA',tmp_path)
    retrieval.database.cache_clear()
    try:
        db=retrieval.database()
        result=db.query_points('frozen',query=[1.0]+[0.0]*383,limit=1).points
        assert result[0].payload==payload
        assert db.count('frozen',exact=True).count==359
    finally:retrieval.database.cache_clear()

def test_bundled_qdrant_rejects_incomplete_snapshot(tmp_path,monkeypatch):
    p=tmp_path/'processed';p.mkdir()
    (p/'index.manifest.json').write_text(json.dumps({'collection':'frozen','points':131}))
    (p/'points.json').write_text('[]')
    monkeypatch.setenv('QDRANT_MODE','bundled');monkeypatch.setattr(retrieval,'DATA',tmp_path)
    retrieval.database.cache_clear()
    with pytest.raises(ValueError,match='Incomplete'):retrieval.database()

def test_cloud_metadata_failure_does_not_fall_back_to_user_token(monkeypatch):
    monkeypatch.setenv('VERTEX_AUTH_MODE','metadata')
    def fail(*args,**kwargs):raise httpx.ConnectError('unavailable')
    monkeypatch.setattr(gemini.httpx,'get',fail)
    with pytest.raises(gemini.ModelUnavailable,match='Cloud service authorization'):gemini.access_token()

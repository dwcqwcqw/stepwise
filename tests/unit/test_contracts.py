"""Guard against fake scores, unsafe input, source drift, and cross-band chunks."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import pytest
from pydantic import ValidationError
from services.api.main import EssayRequest, ModelEssayRequest, RetrievalRequest
from services.chunk.main import build_chunks
from shared.common import digest

@pytest.mark.parametrize('band',[-0.5,9.5,6.3])
def test_target_band_rejected(band):
    with pytest.raises(ValidationError): RetrievalRequest(query='Examples and argument development',criterion='TR',target_band=band)

def test_unknown_criterion_rejected():
    with pytest.raises(ValidationError): RetrievalRequest(query='Examples and argument development',criterion='TA',target_band=7)

def test_blank_essay_rejected():
    with pytest.raises(ValidationError): EssayRequest(prompt='A meaningful prompt here',essay=' '*100)

def test_generation_preserves_requirements():
    value=ModelEssayRequest(prompt='Should public transport receive more funding?',target_band=7,position='Prioritize affordable buses',ideas='Keep rural access; improve job access')
    assert value.model_dump()['ideas']=='Keep rural access; improve job access'

def test_chunks_keep_criterion_and_band_together():
    cells=[{'criterion':'TR','criterion_name':'Task Response','band':6,'text':'A complete source table cell.','source_sha256':'abc','page':8}]
    chunk=build_chunks(cells)[0]
    assert chunk['criterion']=='TR' and chunk['band']==6 and chunk['page']==8
    assert 'Band 6' in chunk['text'] and chunk['text'].endswith(cells[0]['text'])
    assert chunk['chunk_id']==build_chunks(cells)[0]['chunk_id']

def test_duplicate_chunks_fail():
    cell={'criterion':'TR','criterion_name':'Task Response','band':6,'text':'A complete cell.','source_sha256':'abc'}
    with pytest.raises(ValueError,match='Duplicate'): build_chunks([cell,cell])

def test_changed_source_changes_chunk_identity():
    cell={'criterion':'CC','criterion_name':'Coherence and Cohesion','band':7,'text':'An official cell.','source_sha256':'old'}
    assert build_chunks([cell])[0]['chunk_id'] != build_chunks([{**cell,'source_sha256':'new'}])[0]['chunk_id']

@pytest.mark.parametrize('extras',[{}, {'position':'  ', 'ideas':'\n'}, {'position':'No','ideas':'A'}])
def test_optional_goals_accept_blank_or_short_overrides_with_original_essay(extras):
    value=ModelEssayRequest(prompt='Should public transport receive more funding?',target_band=7.5,source_essay='I support road maintenance.',**extras)
    assert value.source_essay=='I support road maintenance.'
    if not extras.get('position','').strip(): assert value.position=='' and value.ideas==''

def test_blank_goals_need_original_content_instead_of_inventing_a_stance():
    with pytest.raises(ValidationError,match='original essay'):
        ModelEssayRequest(prompt='Should public transport receive more funding?',target_band=7.5,position=' ',ideas='More buses')

def test_explicit_new_position_can_generate_without_a_source_essay():
    value=ModelEssayRequest(prompt='Should public transport receive more funding?',target_band=7,position='Prioritize roads')
    assert value.ideas=='' and value.source_essay==''

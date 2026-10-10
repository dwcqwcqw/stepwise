"""Evidence checks that prevent fabricated excerpts, citations and missing standards."""
from copy import deepcopy
import pytest
from shared.assessment import validate_assessment
from services.api.main import EssayRequest

ESSAY='Public transport can connect residents to employers. Reliable buses reduce commuting costs.'
def fixture():
    chunks=[];cards=[]
    for code,count in [('TR',5),('CC',5),('LR',6),('GRA',4)]:
        for band in range(10):chunks.append(dict(chunk_id=f'{code}-band-{band}',criterion=code,band=band,kind='band_descriptor',task='academic_task_2'))
        for n in range(1,count+1):chunks.append(dict(chunk_id=f'{code}-detail-{n}',criterion=code,band=None,kind='subcriterion',subcriterion_id=f'{code}-{n}',text='Header\nOfficial check',task='academic_task_2'))
        cards.append(dict(criterion=code,score=6,rationale='The response shows some development but needs more detailed support.',higher_band_gap='More precise support would be needed to sustain the next band.',title='Develop your argument',essay_quote='Public transport can connect residents to employers.',next_step='Explain how the connection changes access to jobs.',example=dict(before='Reliable buses reduce commuting costs.',after='Reliable, affordable buses can reduce commuting costs for low-income workers.'),source_ids=[f'{code}-band-6',f'{code}-band-7',f'{code}-detail-1'],subcriteria=[dict(subcriterion_id=f'{code}-{n}',judgment='develop',explanation='This passage needs a more precise example.',essay_quote='Reliable buses reduce commuting costs.') for n in range(1,count+1)]))
    return {'summary':'A relevant response with opportunities to develop examples.','criteria':cards},{'chunks':chunks,'index_id':'test-index'}
def test_target_not_in_assessor_input_contract():
    req=EssayRequest(prompt='Should governments invest in public transport?',essay=ESSAY,target_band=9)
    assert 'target_band' not in req.model_dump()
def test_valid_checked_assessment():
    value,context=fixture();r=validate_assessment(value,ESSAY,context)
    assert r['overall_band']==6 and r['target_blind'] and sum(len(c['subcriteria']) for c in r['criteria'])==20
@pytest.mark.parametrize('mutation',['fake_quote','fake_before','fake_source','missing_band','missing_details','fake_detail_quote','duplicate_criterion'])
def test_invalid_evidence_rejected(mutation):
    value,context=fixture();c=value['criteria'][0]
    if mutation=='fake_quote':c['essay_quote']='An invented passage.'
    if mutation=='fake_before':c['example']['before']='An invented passage.'
    if mutation=='fake_source':c['source_ids'][0]='invented-chunk'
    if mutation=='missing_band':c['source_ids'][0]='TR-band-5'
    if mutation=='missing_details':c['subcriteria'].pop()
    if mutation=='fake_detail_quote':c['subcriteria'][0]['essay_quote']='An invented passage.'
    if mutation=='duplicate_criterion':value['criteria'][1]=deepcopy(c)
    with pytest.raises(ValueError):validate_assessment(value,ESSAY,context)

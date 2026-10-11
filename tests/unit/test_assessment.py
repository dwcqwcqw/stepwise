"""Evidence checks that prevent fabricated excerpts, citations and missing standards."""
from copy import deepcopy
import pytest
from shared.assessment import validate_assessment
from services.api.main import EssayRequest
from shared import assessment

ESSAY='Public transport can connect residents to employers. Reliable buses reduce commuting costs. This also helps residents reach more jobs without paying for a private car.'
def fixture():
    chunks=[];cards=[]
    for code,count in [('TR',5),('CC',5),('LR',6),('GRA',4)]:
        for band in range(10):chunks.append(dict(chunk_id=f'{code}-band-{band}',criterion=code,band=band,kind='band_descriptor',task='academic_task_2',statements=[dict(statement_id=f'{code}-B{band}-S1',chunk_id=f'{code}-statement-{band}',text=f'Official Band {band} requirement.',conditional=band<=1,limiting_features=[])]))
        for n in range(1,count+1):chunks.append(dict(chunk_id=f'{code}-detail-{n}',criterion=code,band=None,kind='subcriterion',subcriterion_id=f'{code}-{n}',text='Header\nOfficial check',task='academic_task_2'))
        cards.append(dict(criterion=code,score=6,rationale='The response shows some development but needs more detailed support.',higher_band_gap='More precise support would be needed to sustain the next band.',title='Develop your argument',essay_quote='Public transport can connect residents to employers.',next_step='Explain how the connection changes access to jobs.',example=dict(before='Reliable buses reduce commuting costs.',after='Reliable, affordable buses can reduce commuting costs for low-income workers.'),source_ids=[f'{code}-band-6',f'{code}-band-7',f'{code}-detail-1'],subcriteria=[dict(subcriterion_id=f'{code}-{n}',judgment='develop',explanation='This passage needs a more precise example.',essay_quote='Reliable buses reduce commuting costs.') for n in range(1,count+1)]))
    for card in cards:
        card['band_reviews']=[dict(band=b,checks=[dict(statement_id=f"{card['criterion']}-B{b}-S1",match='meets' if 1<=b<=6 else 'not_met',explanation='The essay demonstrates this level of development.',essay_quote='Reliable buses reduce commuting costs.')],limiters=[]) for b in range(10)]
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

def referenced_fixture(essay=ESSAY):
    value,context=fixture();evidence=assessment.essay_evidence(essay)
    for c in value['criteria']:
        c.pop('source_ids');c.pop('essay_quote');c['essay_evidence_id']=evidence[0]['evidence_id']
        c['example'].pop('before');c['example']['before_evidence_id']=evidence[-1]['evidence_id']
        for band in c['band_reviews']:
            for d in band['checks']+band['limiters']:
                d.pop('essay_quote');d['essay_evidence_id']=evidence[0]['evidence_id']
        for d in c['subcriteria']:
            d.pop('essay_quote');d['essay_evidence_id']=evidence[0]['evidence_id']
    return value,context,evidence

def test_reference_contract_preserves_unicode_and_original_mistakes():
    essay='I don’t agree—buses is useful.\n\nThis matters because affordable services enable workers to reach more employers and spend less of their income on commuting.\n\nThey  helps “low-income” workers!'
    value,context,evidence=referenced_fixture(essay)
    resolved=assessment.resolve_references(value,evidence,context)
    result=validate_assessment(resolved,essay,context)
    assert result['criteria'][0]['essay_quote']=='I don’t agree—buses is useful.'
    assert result['criteria'][0]['example']['before']=='They  helps “low-income” workers!'
    assert all(essay[e['start']:e['end']]==e['text'] for e in evidence)
    # Previously a model's autocorrection caused this exact-text failure.
    resolved['criteria'][0]['essay_quote']='I don’t agree—buses are useful.'
    with pytest.raises(ValueError,match='verbatim'):validate_assessment(resolved,essay,context)

def test_long_evidence_is_bounded_and_verbatim():
    essay=('word ' * 300)+'end.'
    evidence=assessment.essay_evidence(essay)
    assert len(evidence)>1
    assert all(0<len(e['text'])<=600 and essay[e['start']:e['end']]==e['text'] for e in evidence)

@pytest.mark.parametrize('mutation',['unknown_ref','cross_detail','bad_score','missing_ladder'])
def test_reference_resolution_still_rejects_invalid_evidence(mutation):
    value,context,evidence=referenced_fixture()
    if mutation=='unknown_ref':value['criteria'][0]['essay_evidence_id']='E999'
    if mutation=='cross_detail':value['criteria'][0]['subcriteria'][0]['subcriterion_id']='CC-1'
    if mutation=='bad_score':value['criteria'][0]['score']=6.5
    if mutation=='missing_ladder':context['chunks']=[c for c in context['chunks'] if c['chunk_id']!='TR-band-6']
    with pytest.raises((ValueError,KeyError)):
        validate_assessment(assessment.resolve_references(value,evidence,context),ESSAY,context)

def test_repair_receives_prior_answer_and_field_reason(monkeypatch,caplog):
    value,context,evidence=referenced_fixture();requests=[]
    def generate(system,payload,schema,temperature):
        requests.append(deepcopy(payload));code=payload['requested_criterion']
        card=deepcopy(next(c for c in value['criteria'] if c['criterion']==code))
        if code=='TR' and 'validation_repair' not in payload:card['essay_evidence_id']='E999'
        return {'summary':value['summary'],'criteria':[card]},{'response_id':str(len(requests))}
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    monkeypatch.setattr(assessment,'generate',generate)
    result=assessment.assess('Should governments fund buses?',ESSAY)
    assert len(result['model_calls'])==5
    tr=[r for r in requests if r['requested_criterion']=='TR']
    assert tr[1]['previous_assessment']['criteria'][0]['essay_evidence_id']=='E999'
    assert tr[1]['validation_repair']=='Unknown essay evidence ID'
    assert ESSAY not in caplog.text

def test_failed_reference_repair_remains_closed(monkeypatch):
    value,context,evidence=referenced_fixture()
    def generate(system,payload,*a,**k):
        card=deepcopy(next(c for c in value['criteria'] if c['criterion']==payload['requested_criterion']))
        card['essay_evidence_id']='E999'
        return {'summary':value['summary'],'criteria':[card]},{}
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    monkeypatch.setattr(assessment,'generate',generate)
    with pytest.raises(assessment.ModelUnavailable):assessment.assess('Should governments fund buses?',ESSAY)

@pytest.mark.parametrize('mutation',['missing_band_review','missing_statement','duplicate_statement','skip_requirement','unsupported_score','missing_next_gap','fake_band_quote','cross_band_statement'])
def test_complete_band_matching_is_required(mutation):
    value,context=fixture();card=value['criteria'][0]
    if mutation=='missing_band_review':card['band_reviews'].pop()
    if mutation=='missing_statement':card['band_reviews'][6]['checks']=[]
    if mutation=='duplicate_statement':card['band_reviews'][6]['checks']*=2
    if mutation=='skip_requirement':card['band_reviews'][6]['checks'][0]['match']='not_applicable'
    if mutation=='unsupported_score':card['score']=8
    if mutation=='missing_next_gap':card['band_reviews'][7]['checks'][0]['match']='meets'
    if mutation=='fake_band_quote':card['band_reviews'][6]['checks'][0]['essay_quote']='Invented words.'
    if mutation=='cross_band_statement':card['band_reviews'][6]['checks'][0]['statement_id']='TR-B7-S1'
    with pytest.raises(ValueError):validate_assessment(value,ESSAY,context)

def test_bold_limit_caps_score_even_if_higher_features_met():
    value,context=fixture();card=value['criteria'][0]
    context['chunks'][5]['statements'][0]['limiting_features']=[{'limiter_id':'TR-B5-S1-L1','text':'Incompletely addressed.'}]
    card['band_reviews'][5]['limiters']=[dict(limiter_id='TR-B5-S1-L1',present=True,explanation='One required part of the question is missing.',essay_quote='Reliable buses reduce commuting costs.')]
    with pytest.raises(ValueError,match='expected 5'):validate_assessment(value,ESSAY,context)
    card['score']=5;card['source_ids']=['TR-band-5','TR-band-6','TR-detail-1']
    assert validate_assessment(value,ESSAY,context)['criteria'][0]['score_decision']['limiting_band_cap']==5

def test_twenty_word_rule_is_applied_without_invented_penalty():
    value,context=fixture()
    with pytest.raises(ValueError,match='expected 1'):validate_assessment(value,'Public transport can connect residents to employers. Reliable buses reduce commuting costs.',context)

@pytest.mark.parametrize('scores,mean,band',[([6,6,6,6],6,6),([6,6,6,7],6.25,6.5),([6,6,7,7],6.5,6.5),([6,7,7,7],6.75,7),([7,8,8,8],7.75,8),([9,9,9,9],9,9),([0,0,0,1],.25,.5)])
def test_exact_equal_weight_mean_and_half_up_rounding(scores,mean,band):
    from shared.band_matching import score_summary
    result=score_summary(scores)
    assert result['criterion_mean']==mean and result['overall_band']==band
    assert result['score_calculation']['raw_mean']==f'{mean:.2f}'

def test_skipped_requirement_repair_identifies_exact_statement():
    value,context=fixture()
    value['criteria'][0]['band_reviews'][6]['checks'][0]['match']='not_applicable'
    with pytest.raises(ValueError,match='TR-B6-S1 at Band 6.*conditional=false.*meets or not_met'):
        validate_assessment(value,ESSAY,context)

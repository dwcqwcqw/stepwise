"""Decision-first scoring keeps complete coverage while deferring feedback."""
from copy import deepcopy
from collections import Counter
import pytest
from shared import model_assessment as fast
from shared.assessment import validate_assessment
from test_assessment import fixture, ESSAY


def fixtures():
    original,context=fixture();evidence=fast.essay_evidence(ESSAY)
    ref=next(x['evidence_id'] for x in evidence if x['text']=='Reliable buses reduce commuting costs.')
    decisions={};feedback={}
    for card in original['criteria']:
        code=card['criterion']
        decisions[code]={'checks':[{'match':{'meets':'M','not_met':'N','not_applicable':'A'}[s['match']], 'evidence_id':ref} for b in card['band_reviews'] for s in b['checks']],
            'limiters':[],'rationale':card['rationale'],'higher_band_gap':card['higher_band_gap']}
        feedback[code]={k:card[k] for k in ['rationale','higher_band_gap','title','next_step']}
        feedback[code].update(essay_evidence_id=ref,example={'before_evidence_id':ref,'after':card['example']['after']},
            subcriteria={d['subcriterion_id']:{'judgment':d['judgment'],'explanation':d['explanation'],'essay_evidence_id':ref} for d in card['subcriteria']},
            statement_explanations={s['statement_id']:s['explanation'] for b in card['band_reviews'] if b['band'] in [6,7] for s in b['checks']})
    return decisions,feedback,context,evidence


def install(monkeypatch,alter=None):
    decisions,feedback,context,evidence=fixtures();calls=[]
    monkeypatch.setattr(fast,'assessment_context',lambda _:context)
    def model(system,payload,schema,temperature):
        calls.append(deepcopy(payload));code=payload['requested_criterion']
        stage='feedback' if 'derived_score' in payload else 'decisions'
        value=deepcopy((feedback if stage=='feedback' else decisions)[code])
        if alter:alter(value,payload,stage)
        return value,{'stage':stage}
    monkeypatch.setattr(fast,'generate',model)
    return calls,context,evidence


def test_screen_has_no_numeric_model_scores_or_expensive_feedback(monkeypatch):
    calls,_,_=install(monkeypatch)
    result=fast.screen_model_essay('Should we fund buses?',ESSAY)
    assert len(calls)==4 and result['overall_band']==6
    assert result['descriptor_statements_checked']==40 and result['target_blind']
    assert all('target_band' not in p and 'derived_score' not in p and 'previous_assessment' not in p for p in calls)
    assert all('subcriteria' not in c for c in result['criteria'])
    assert 'score' not in fast.decision_schema(fast.essay_evidence(ESSAY))['properties']
    assert all(s['essay_quote'] in ESSAY for c in result['criteria'] for b in c['band_reviews'] for s in b['checks'])


def test_final_feedback_preserves_all_decisions_and_twenty_details(monkeypatch):
    calls,_,_=install(monkeypatch);updates=[]
    result=fast.assess_model_essay('Should we fund buses?',ESSAY,lambda **e:updates.append(e))
    assert len(calls)==8 and result['overall_band']==6
    assert result['assessment_mode']=='decision_first_with_final_feedback'
    assert sum(len(c['subcriteria']) for c in result['criteria'])==20
    assert result['score_calculation']['raw_mean']=='6.00'
    assert all('target_band' not in p for p in calls)
    assert {e['criterion'] for e in updates if 'criterion' in e}==set(fast.CRITERIA)
    assert all(c['score_decision']['highest_supported_band']==c['score'] for c in result['criteria'])


@pytest.mark.parametrize('mutation',['missing','unknown_evidence','ordinary_skip','bad_limiter','numeric_score'])
def test_invalid_decisions_rejected_without_unchecked_scores(mutation):
    decisions,_,context,evidence=fixtures();value=decisions['TR']
    if mutation=='missing':value['checks'].pop()
    if mutation=='unknown_evidence':value['checks'][6]['evidence_id']='E999'
    if mutation=='ordinary_skip':value['checks'][6]['match']='A'
    if mutation=='bad_limiter':value['limiters']=[{'present':'true','evidence_id':'E001'}]
    if mutation=='numeric_score':value['score']=9
    with pytest.raises((ValueError,KeyError)):
        fast.unpack_decisions(value,context,'TR',evidence,ESSAY)


def test_bold_caps_and_quarter_to_half_arithmetic_preserved():
    decisions,_,context,evidence=fixtures()
    row=next(c for c in context['chunks'] if c['chunk_id']=='TR-band-5')
    row['statements'][0]['limiting_features']=[{'limiter_id':'TR-B5-S1-L1','text':'A required question part is not addressed.'}]
    decisions['TR']['limiters']=[{'present':True,'evidence_id':'E001'}]
    card=fast.unpack_decisions(decisions['TR'],context,'TR',evidence,ESSAY)
    assert card['score']==5 and card['score_decision']['limiting_band_cap']==5
    result=fast.score_summary([6,5,5,5])
    assert result['criterion_mean']==5.25 and result['overall_band']==5.5


def test_retry_only_failed_criterion(monkeypatch):
    def alter(value,payload,stage):
        if stage=='decisions' and payload['requested_criterion']=='LR' and 'validation_repair' not in payload:
            value['checks'][6]['evidence_id']='E999'
    calls,_,_=install(monkeypatch,alter)
    assert fast.screen_model_essay('Should we fund buses?',ESSAY)['overall_band']==6
    assert Counter(p['requested_criterion'] for p in calls)=={'TR':1,'CC':1,'LR':2,'GRA':1}
    assert 'LR:' in next(p['validation_repair'] for p in calls if 'validation_repair' in p)


def test_empty_eligible_set_reports_criterion_and_fails_closed(monkeypatch):
    def alter(value,payload,stage):
        if payload['requested_criterion']=='LR':
            for s in value['checks']:s['match']='N'
    calls,_,_=install(monkeypatch,alter)
    with pytest.raises(fast.ModelUnavailable,match='Lexical Resource'):
        fast.screen_model_essay('Should we fund buses?',ESSAY)
    assert Counter(p['requested_criterion'] for p in calls)['LR']==2


@pytest.mark.parametrize('mutation',['missing_focus','missing_detail','fake_quote','tamper_score','short_explanation'])
def test_feedback_cannot_modify_scores_or_fabricate_evidence(mutation):
    decisions,feedback,context,evidence=fixtures()
    card=fast.unpack_decisions(decisions['TR'],context,'TR',evidence,ESSAY);value=feedback['TR']
    if mutation=='missing_focus':value['statement_explanations'].pop('TR-B6-S1')
    if mutation=='missing_detail':value['subcriteria'].pop('TR-1')
    if mutation=='fake_quote':value['essay_evidence_id']='E999'
    if mutation=='tamper_score':value['score']=9
    if mutation=='short_explanation':value['statement_explanations']['TR-B6-S1']='ok'
    with pytest.raises((ValueError,KeyError)):
        fast.materialize_feedback(value,card,context,evidence,ESSAY)


def test_feedback_schema_uses_server_selected_slots_and_no_score():
    decisions,_,context,evidence=fixtures();card=fast.unpack_decisions(decisions['TR'],context,'TR',evidence,ESSAY)
    fields=fast.feedback_schema(card,context,evidence)['properties']
    assert 'score' not in fields and 'matches' not in fields
    assert set(fields['statement_explanations']['properties'])=={'TR-B6-S1','TR-B7-S1'}
    assert len(fields['subcriteria']['properties'])==5
    assert 'limiter_explanations' not in fields


def test_same_essay_and_index_required_for_feedback(monkeypatch):
    install(monkeypatch);screen=fast.screen_model_essay('Should we fund buses?',ESSAY)
    with pytest.raises(ValueError,match='essay changed'):
        fast.complete_model_feedback('Should we fund buses?',ESSAY+' changed',screen)
    screen['index_id']='different'
    with pytest.raises(ValueError,match='index changed'):
        fast.complete_model_feedback('Should we fund buses?',ESSAY,screen)

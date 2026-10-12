"""One-call generation grading preserves all official match/evidence gates."""
from copy import deepcopy
import pytest
from shared import model_assessment as fast
from shared.compact import rename
from shared.assessment import resolve_references,validate_assessment
from test_assessment import referenced_fixture,ESSAY


def compact_fixture():
    value,context,evidence=referenced_fixture();cards={}
    for original in value['criteria']:
        c=deepcopy(original);code=c.pop('criterion');bands=c.pop('band_reviews')
        checks=[s for b in bands for s in b['checks']];limiters=[l for b in bands for l in b['limiters']]
        c['matches']=[{'meets':'M','not_met':'N','not_applicable':'A'}[s['match']] for s in checks]
        c['evidence_ids']=[s['essay_evidence_id'] for s in checks]
        c['limiter_flags']=[l['present'] for l in limiters];c['limiter_evidence_ids']=[l['essay_evidence_id'] for l in limiters]
        c['focus_explanations']=[{k:s[k] for k in ('statement_id','explanation')} for b in bands if b['band'] in {c['score'],c['score']+1} for s in b['checks']]
        c['limiter_explanations']=[];cards[code]=c
    return {'summary':value['summary'],'criteria':cards},context,evidence


def test_one_target_blind_call_validates_every_statement_and_all_details(monkeypatch):
    value,context,evidence=compact_fixture();calls=[];updates=[]
    monkeypatch.setattr(fast,'assessment_context',lambda _:context)
    def model(system,payload,schema,temperature):
        calls.append(deepcopy(payload))
        assert set(payload)=={'question','essay','essay_evidence','word_count','official_assessment_context','decision_order'}
        for code in ['TR','CC','LR','GRA']:
            assert len(payload['decision_order'][code]['statement_ids'])==10
            assert schema['properties']['criteria']['properties'][code]['properties']['matches']['minItems']==10
        return rename(value),{'response_id':'combined'}
    monkeypatch.setattr(fast,'generate',model)
    result=fast.assess_model_essay('Should governments fund buses?',ESSAY,progress=lambda **e:updates.append(e))
    assert len(calls)==1 and result['overall_band']==6 and result['target_blind']
    assert result['descriptor_statements_checked']==40  # full compact unit fixture
    assert sum(len(c['subcriteria']) for c in result['criteria'])==20
    assert result['assessment_mode']=='compact_four_criteria'
    assert {e['criterion'] for e in updates if e.get('criterion')}=={'TR','CC','LR','GRA'}
    assert all(s['essay_quote'] in ESSAY for c in result['criteria'] for b in c['band_reviews'] for s in b['checks'])
    assert result['criteria'][0]['band_reviews'][5]['checks'][0]['explanation']=='Assessment decision: threshold met.'
    assert result['criteria'][0]['band_reviews'][6]['checks'][0]['explanation']==value['criteria']['TR']['focus_explanations'][0]['explanation']


@pytest.mark.parametrize('mutation',['short_matches','missing_evidence','fake_evidence','skip_requirement','unsupported_score','duplicate_focus','missing_focus','extra_criterion','missing_detail'])
def test_compact_format_cannot_skip_or_fabricate_evidence(mutation):
    value,context,evidence=compact_fixture();c=value['criteria']['TR']
    if mutation=='short_matches':c['matches'].pop()
    if mutation=='missing_evidence':c['evidence_ids'].pop()
    if mutation=='fake_evidence':c['evidence_ids'][6]='E999'
    if mutation=='skip_requirement':c['matches'][6]='A'
    if mutation=='unsupported_score':c['score']=7;c['focus_explanations']=[{'statement_id':f'TR-B{b}-S1','explanation':'This threshold is supported by the writing.'} for b in [7,8]]
    if mutation=='duplicate_focus':c['focus_explanations'][1]=deepcopy(c['focus_explanations'][0])
    if mutation=='missing_focus':c['focus_explanations'].pop()
    if mutation=='extra_criterion':value['criteria']['FAKE']=deepcopy(c)
    if mutation=='missing_detail':c['subcriteria'].pop()
    with pytest.raises((ValueError,KeyError)):
        canonical=fast.unpack_matches(value,context)
        validate_assessment(resolve_references(canonical,evidence,context),ESSAY,context)


def test_present_bold_limiter_still_caps_an_otherwise_supported_higher_band():
    value,context,evidence=compact_fixture();c=value['criteria']['TR']
    row=next(x for x in context['chunks'] if x['chunk_id']=='TR-band-5')
    row['statements'][0]['limiting_features']=[{'limiter_id':'TR-B5-S1-L1','text':'A required question part is not addressed.'}]
    c['limiter_flags']=[True];c['limiter_evidence_ids']=['E001']
    c['limiter_explanations']=[{'limiter_id':'TR-B5-S1-L1','explanation':'One required part of the question is absent.'}]
    with pytest.raises(ValueError,match='expected 5'):
        canonical=fast.unpack_matches(value,context)
        validate_assessment(resolve_references(canonical,evidence,context),ESSAY,context)


def test_combined_repair_receives_exact_failure_and_previous_answer(monkeypatch):
    value,context,_=compact_fixture();requests=[]
    monkeypatch.setattr(fast,'assessment_context',lambda _:context)
    def model(system,payload,schema,temperature):
        requests.append(deepcopy(payload));v=deepcopy(value)
        if len(requests)==1:v['criteria']['LR']['evidence_ids'][6]='E999'
        return rename(v),{}
    monkeypatch.setattr(fast,'generate',model)
    result=fast.assess_model_essay('Should governments fund buses?',ESSAY)
    assert len(requests)==2 and requests[1]['validation_repair']=='Unknown essay evidence ID'
    assert 'previous_assessment' in requests[1] and result['target_blind']


def test_repeated_combined_failure_returns_no_score(monkeypatch):
    value,context,_=compact_fixture();value['criteria']['LR']['evidence_ids'][6]='E999'
    monkeypatch.setattr(fast,'assessment_context',lambda _:context)
    monkeypatch.setattr(fast,'generate',lambda *a,**kw:(rename(value),{}))
    with pytest.raises(fast.ModelUnavailable):fast.assess_model_essay('Should governments fund buses?',ESSAY)

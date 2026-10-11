"""Regression: a generated 9 is not a successful request for a 5/6/7."""
from copy import deepcopy
import pytest
from shared import assessment
from shared.targeting import target_profile, adjust_writer_profile, nearest_score_profile, MAX_TARGET_ATTEMPTS
from shared.band_matching import score_summary
from shared.gemini import ModelUnavailable
from shared.progress import events
from test_assessment import referenced_fixture
import json

@pytest.mark.parametrize('target',[4,4.5,5,5.5,6,6.5,7,7.5,8,8.5,9])
def test_half_band_profile_has_exact_mean_and_published_integer_rows(target):
    profile=target_profile(target)
    assert all(type(v) is int for v in profile.values())
    assert sum(profile.values())/4==target
    assert score_summary(list(profile.values()))['overall_band']==target

@pytest.mark.parametrize('target',[True,3.5,9.5,6.25,float('nan'),float('inf'),'7'])
def test_invalid_generation_profile_rejected(target):
    with pytest.raises(ValueError):target_profile(target)

def setup_generation(monkeypatch, bands, target=7):
    _,context,_=referenced_fixture()
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    payloads=[];assessed=[]
    requirements={'prompt':'Should public transport receive more funding?', 'target_band':target,
                  'position':'Prioritize public transport.', 'ideas':'Improve job access; maintain rural roads.'}
    def model(system,payload,schema,temperature):
        payloads.append(deepcopy(payload))
        return {'title':'Transport priorities','essay':('A learner sentence. '*100)+str(len(payloads)),
                'requirement_notes':['Preserves job access and rural roads.']}, {'response_id':str(len(payloads))}
    def independent(prompt,essay,progress):
        # Signature accepts no target/profile/plan/prior score.
        assert prompt==requirements['prompt'];assessed.append(essay)
        band=bands[len(assessed)-1]
        return {'overall_band':band,'essay_sha256':str(len(assessed)), 'target_blind':True,
                'model_calls':[{'response_id':'assessment-'+str(len(assessed))}],
                'criteria':[{'criterion':c,'score':v,'rationale':'Observed writing performance.',
                             'higher_band_gap':'Observed gap from the next descriptor.','band_reviews':[]}
                            for c,v in target_profile(band).items()]}
    monkeypatch.setattr(assessment,'generate',model)
    monkeypatch.setattr(assessment,'assess',independent)
    return requirements,payloads,assessed

@pytest.mark.parametrize('target,observed',[(5,[9,6,5]),(6.5,[9,6.5]),(7,[6,7]),(9,[9])])
def test_rewrite_until_independent_score_matches_exact_target(monkeypatch,target,observed):
    requirements,payloads,assessed=setup_generation(monkeypatch,observed,target)
    updates=[]
    result=assessment.generate_essay(requirements,progress=lambda **e:updates.append(e))
    assert result['assessment']['overall_band']==target and result['target_met']
    assert len(payloads)==len(observed)==len(result['target_match']['attempts'])
    assert result['essay']==assessed[-1] and result['assessment']['target_blind']
    assert payloads[0]['criterion_target_profile']==target_profile(target)
    if len(observed)>1:
        assert payloads[1]['previous_essay']==assessed[0]
        assert payloads[1]['revision_feedback']['observed_band']==observed[0]
        assert any(e['phase']=='generation' and e['status']=='repair' and e['attempt']==2 for e in updates)
    assert updates[-1]['phase']=='calibration' and updates[-1]['status']=='done'

def test_generation_retrieves_adjacent_official_boundaries(monkeypatch):
    requirements,payloads,_=setup_generation(monkeypatch,[6.5],6.5)
    assessment.generate_essay(requirements)
    for code,expected in target_profile(6.5).items():
        rows=[r for r in payloads[0]['official_rubric_context'] if r['kind']=='band_descriptor' and r['criterion']==code]
        assert {r['band'] for r in rows}=={expected-1,expected,expected+1}

def test_persistent_overshoot_never_returns_wrong_band_as_success(monkeypatch):
    requirements,payloads,_=setup_generation(monkeypatch,[9]*MAX_TARGET_ATTEMPTS,5)
    output=[json.loads(line) for line in events(lambda emit:assessment.generate_essay(requirements,emit))]
    assert len(payloads)==MAX_TARGET_ATTEMPTS
    assert not any(e['type']=='result' for e in output)
    assert output[-1]['type']=='error' and 'Band 5.0' in output[-1]['detail']

@pytest.mark.parametrize('current,observed,desired,expected',[
    (7,9,7,5),(5,6,7,6),(4,6,4,2),(2,9,4,2),(9,5,9,9)])
def test_writer_control_corrects_observed_error_without_changing_scores(current,observed,desired,expected):
    original={'criteria':[{'criterion':c,'score':observed} for c in ['TR','CC','LR','GRA']]}
    saved=deepcopy(original)
    result=adjust_writer_profile(dict.fromkeys(['TR','CC','LR','GRA'],current),original,
                                 dict.fromkeys(['TR','CC','LR','GRA'],desired))
    assert set(result.values())=={expected} and original==saved

@pytest.mark.parametrize('scores,target',[( [7,6,6,6],7),([5,5,4,4],5),([8,7,7,7],7),([9,9,9,9],8.5),([0,0,0,0],4)])
def test_nearest_profile_changes_only_the_required_score_sum(scores,target):
    a={'criteria':[{'criterion':c,'score':v} for c,v in zip(['TR','CC','LR','GRA'],scores)]}
    p=nearest_score_profile(a,target)
    assert score_summary(list(p.values()))['overall_band']==target
    assert all(type(v) is int and 0<=v<=9 for v in p.values())

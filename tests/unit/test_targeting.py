"""Regression: a generated 9 is not a successful request for a 5/6/7."""
from copy import deepcopy
import pytest
from shared import assessment
from shared.targeting import target_profile, adjust_writer_profile, nearest_score_profile, MAX_TARGET_ATTEMPTS, apply_focus_edits
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
        if schema is assessment.PATCH_SCHEMA:
            ending=payload['previous_essay'].rsplit(' ',2)[-2:]
            return {'edits':[{'before':' '.join(ending),'after':'sentence. '+str(len(payloads))}]},{'response_id':str(len(payloads))}
        return {'title':'Transport priorities','position_sentence':'A learner sentence.','essay':('A learner sentence. '*100)+str(len(payloads)),
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
    monkeypatch.setattr(assessment,'assess_model_essay',independent)
    monkeypatch.setattr(assessment,'complete_model_feedback',lambda prompt,essay,evaluation,progress:evaluation)
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
        assert payloads[1]['protected_position_sentence']=='A learner sentence.'
        assert any(e['phase']=='generation' and e['status']=='repair' and e['attempt']==2 for e in updates)
    assert updates[-1]['phase']=='calibration' and updates[-1]['status']=='done'

def test_generation_retrieves_adjacent_official_boundaries(monkeypatch):
    requirements,payloads,_=setup_generation(monkeypatch,[6.5],6.5)
    assessment.generate_essay(requirements)
    for code,expected in target_profile(6.5).items():
        rows=[r for r in payloads[0]['official_rubric_context'] if r['kind']=='band_descriptor' and r['criterion']==code]
        assert {r['band'] for r in rows}=={expected-1,expected,expected+1}

def test_persistent_overshoot_returns_actual_score_without_claiming_target_match(monkeypatch):
    requirements,payloads,_=setup_generation(monkeypatch,[9]*MAX_TARGET_ATTEMPTS,5)
    output=[json.loads(line) for line in events(lambda emit:assessment.generate_essay(requirements,emit))]
    assert len(payloads)==MAX_TARGET_ATTEMPTS, apply_focus_edits
    result=next(e['result'] for e in output if e['type']=='result')
    assert not any(e['type']=='error' for e in output)
    assert result['assessment']['overall_band']==9 and result['requirements']['target_band']==5
    assert result['target_met'] is False and result['target_match']['exact_match'] is False
    assert result['target_match']['selection']=='closest_assessed_candidate'
    assert 'Band 5.0' in result['notice'] and 'Band 9.0' in result['notice']

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

def test_rewrite_cannot_drop_the_protected_position(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[6.5,5],5)
    original=assessment.generate
    def writer(*args,**kwargs):
        value,receipt=original(*args,**kwargs)
        if len(payloads)==2:value['position_sentence']='A completely changed position.'
        return value,receipt
    monkeypatch.setattr(assessment,'generate',writer)
    result=assessment.generate_essay(requirements)
    assert len(payloads)==3 and len(assessed)==2
    assert payloads[-1]['protected_position_sentence'] in result['essay']

def test_single_candidate_continuation_preserves_attempt_history_and_target_blind_scoring(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[9,7],7)
    pending=assessment.generate_essay(requirements,pause_after_candidate=True)
    assert pending['status']=='continuation_required'
    assert len(assessed)==1 and pending['checkpoint']['next_attempt']==2
    result=assessment.generate_essay(requirements,checkpoint=pending['checkpoint'],pause_after_candidate=True)
    assert result['target_met'] and result['assessment']['overall_band']==7
    assert [x['assessed_band'] for x in result['target_match']['attempts']]==[9,7]
    assert payloads[1]['protected_position_sentence']=='A learner sentence.'

def test_focused_revision_keeps_calibrated_control_levels_for_unchanged_skills(monkeypatch):
    requirements,payloads,_=setup_generation(monkeypatch,[9,6.5,7],7)
    result=assessment.generate_essay(requirements)
    assert result['target_met']
    second=payloads[1]['criterion_target_profile']
    third=payloads[2]['criterion_target_profile']
    assert second=={'TR':5,'CC':5,'LR':5,'GRA':5}
    assert payloads[2]['revision_mode']=='rewrite'
    assert payloads[2]['focus_criteria']==['LR']
    assert third=={'TR':5,'CC':5,'LR':6,'GRA':5}
    # Do not reset TR/CC/GRA to the observed scores (7/6/6), which rewrites
    # already calibrated skills and causes oscillation back to higher bands.


def test_local_edits_preserve_every_unmodified_word_and_the_position():
    essay='My position is clear. '+('ordinary words ' * 100)+'A specific observation matters.'
    result=apply_focus_edits(essay,[{'before':'specific observation','after':'precise example'}],'My position is clear.',['LR'])
    assert result==essay.replace('specific observation','precise example')

@pytest.mark.parametrize('edits',[
    [{'before':'invented passage','after':'new'}],
    [{'before':'ordinary words','after':'new'}],
    [{'before':'My position is clear.','after':'I am undecided.'}],
    [{'before':'A specific observation matters.','after':' '.join(['long']*36)}],
    [{'before':'A specific observation','after':'different'},{'before':'specific observation matters.','after':'overlap'}],
])
def test_invalid_focused_edits_are_rejected(edits):
    essay='My position is clear. '+('ordinary words ' * 100)+'A specific observation matters.'
    with pytest.raises(ValueError):apply_focus_edits(essay,edits,'My position is clear.',['LR'])


def test_calibration_outputs_complete_essay_without_brittle_patch_protocol(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[6.5,7],7)
    original=assessment.generate
    def writer(system,payload,schema,temperature):
        assert schema is not assessment.PATCH_SCHEMA
        return original(system,payload,schema,temperature)
    monkeypatch.setattr(assessment,'generate',writer)
    result=assessment.generate_essay(requirements)
    assert result['target_met'] and len(assessed)==2
    assert payloads[1]['revision_mode']=='rewrite'
    assert payloads[1]['protected_position_sentence'] in result['essay']


def test_length_repair_receives_failed_candidate_and_measured_count(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[7],7)
    original=assessment.generate
    def writer(*args,**kwargs):
        value,receipt=original(*args,**kwargs)
        if len(payloads)==1:value['essay']='A learner sentence. '*70
        return value,receipt
    monkeypatch.setattr(assessment,'generate',writer)
    result=assessment.generate_essay(requirements)
    repair=payloads[1]['validation_repair']
    assert repair['actual_word_count']==210
    assert repair['previous_invalid_candidate']['essay']=='A learner sentence. '*70
    assert 'SAME requested proficiency' in repair['instruction']
    assert payloads[1]['criterion_target_profile']==payloads[0]['criterion_target_profile']
    assert len(assessed)==1 and result['target_met']


def test_revised_essay_length_repair_keeps_target_profile_and_protected_stance(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[6.5,7],7)
    original=assessment.generate
    def writer(*args,**kwargs):
        value,receipt=original(*args,**kwargs)
        if len(payloads)==2:value['essay']='A learner sentence. '*70
        return value,receipt
    monkeypatch.setattr(assessment,'generate',writer)
    result=assessment.generate_essay(requirements)
    assert len(payloads)==3 and len(assessed)==2 and result['target_met']
    assert payloads[2]['validation_repair']['actual_word_count']==210
    assert payloads[2]['criterion_target_profile']==payloads[1]['criterion_target_profile']
    assert payloads[2]['protected_position_sentence'] in result['essay']


def test_detailed_feedback_only_for_target_matching_final_candidate(monkeypatch):
    requirements,_,assessed=setup_generation(monkeypatch,[9,7],7)
    completed=[]
    def finish(prompt,essay,evaluation,progress):
        completed.append((essay,evaluation['overall_band']))
        return evaluation
    monkeypatch.setattr(assessment,'complete_model_feedback',finish)
    result=assessment.generate_essay(requirements)
    assert len(assessed)==2 and completed==[(result['essay'],7)]


def test_closest_candidate_is_preserved_even_when_last_draft_regresses(monkeypatch):
    requirements,payloads,assessed=setup_generation(monkeypatch,[7,6.5,8.5],7.5)
    finished=[]
    def finish(prompt,essay,evaluation,progress):
        finished.append(essay);return evaluation
    monkeypatch.setattr(assessment,'complete_model_feedback',finish)
    result=assessment.generate_essay(requirements)
    assert len(payloads)==3 and result['essay']==assessed[0] and finished==[assessed[0]]
    assert result['assessment']['overall_band']==7 and not result['target_met']
    assert result['target_match']['selected_attempt']==1
    assert result['target_match']['band_distance']==.5
    assert len(result['target_match']['attempts'])==3


def test_best_candidate_stays_private_across_continuations_and_finishes_after_two_adjustments(monkeypatch):
    requirements,_,assessed=setup_generation(monkeypatch,[6.5,7,8.5],7.5)
    a=assessment.generate_essay(requirements,pause_after_candidate=True)
    b=assessment.generate_essay(requirements,checkpoint=a['checkpoint'],pause_after_candidate=True)
    assert a['status']==b['status']=='continuation_required'
    assert b['checkpoint']['best']['attempt']==2 and 'essay' not in b
    result=assessment.generate_essay(requirements,checkpoint=b['checkpoint'],pause_after_candidate=True)
    assert result['status']=='generated_and_assessed' and result['essay']==assessed[1]
    assert result['assessment']['overall_band']==7 and result['target_met'] is False


def test_final_feedback_failure_never_returns_an_unchecked_closest_candidate(monkeypatch):
    requirements,_,_=setup_generation(monkeypatch,[7,7,7],7.5)
    def finish(*args):raise ModelUnavailable('Feedback evidence failed')
    monkeypatch.setattr(assessment,'complete_model_feedback',finish)
    output=[json.loads(line) for line in events(lambda emit:assessment.generate_essay(requirements,emit))]
    assert not any(e['type']=='result' for e in output)
    assert output[-1]['type']=='error' and output[-1]['detail']=='Feedback evidence failed'


def test_invalid_later_draft_does_not_discard_an_assessed_candidate(monkeypatch):
    requirements,_,assessed=setup_generation(monkeypatch,[7],7.5)
    writer=assessment.generate
    count=0
    def short_revision(*args,**kwargs):
        nonlocal count
        count+=1
        value,receipt=writer(*args,**kwargs)
        if count>1:value['essay']='A learner sentence. '*70
        return value,receipt
    monkeypatch.setattr(assessment,'generate',short_revision)
    result=assessment.generate_essay(requirements)
    assert count==3 and len(assessed)==1
    assert result['essay']==assessed[0] and result['assessment']['overall_band']==7
    assert result['target_met'] is False and len(result['target_match']['attempts'])==1

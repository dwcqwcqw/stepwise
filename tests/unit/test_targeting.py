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

















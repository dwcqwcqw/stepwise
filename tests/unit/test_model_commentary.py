from copy import deepcopy
import pytest
from shared import assessment, model_commentary as commentary
from shared.targeting import target_profile
from shared.gemini import ModelUnavailable
from test_assessment import fixture, ESSAY


def sample():
    _,context=fixture();evidence=assessment.essay_evidence(ESSAY)
    value={'summary':'The essay presents a clear argument with opportunities for more precise support.','criteria':{}}
    for code in assessment.CRITERIA:
        value['criteria'][code]={'title':'Develop precise support','rationale':'The passage explains an important benefit but can add a more specific example.',
            'essay_evidence_id':'E001','next_step':'Add a specific commuter example to make this benefit concrete.',
            'example':{'before_evidence_id':'E002','after':'Reliable buses reduce commuting costs for workers travelling from outer suburbs.'},
            'subcriteria':{c['subcriterion_id']:{'judgment':'develop','explanation':'Make the benefit concrete with an example.','essay_evidence_id':'E001'} for c in context['chunks'] if c['kind']=='subcriterion' and c['criterion']==code}}
    return value,context,evidence


def test_qualitative_feedback_keeps_exact_quotes_and_official_target_rows():
    value,context,evidence=sample();r=commentary.materialize(value,context,evidence,target_profile(7.5))
    assert len(r['criteria'])==4 and sum(len(c['subcriteria']) for c in r['criteria'])==20
    for c in r['criteria']:
        assert c['essay_quote'] in ESSAY and c['example']['before'] in ESSAY
        assert c['rubric'][0]['band']==target_profile(7.5)[c['criterion']]
        assert not {'score','band_reviews','score_decision'}.intersection(c)
    assert not {'overall_band','score_calculation'}.intersection(r)

@pytest.mark.parametrize('mutation',['fake_quote','score','missing_criterion','wrong_skill','missing_rubric'])
def test_commentary_rejects_invalid_evidence_or_score_fields(mutation):
    value,context,evidence=sample()
    if mutation=='fake_quote':value['criteria']['TR']['essay_evidence_id']='E999'
    if mutation=='score':value['criteria']['TR']['score']=9
    if mutation=='missing_criterion':value['criteria'].pop('CC')
    if mutation=='wrong_skill':value['criteria']['TR']['subcriteria']['CC-1']=value['criteria']['TR']['subcriteria'].pop('TR-1')
    if mutation=='missing_rubric':context['chunks']=[c for c in context['chunks'] if c['chunk_id']!='TR-band-8']
    with pytest.raises((ValueError,KeyError)):commentary.materialize(value,context,evidence,target_profile(7.5))


def setup_writer(monkeypatch,target=7.5):
    _,context,_=sample();requests=[]
    requirements={'prompt':'Should public transport receive more funding?','target_band':target,'position':'Prioritize public transport.','ideas':'Improve job access and maintain rural roads.'}
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    def writer(system,payload,schema,temperature):
        requests.append(deepcopy(payload))
        return {'title':'Transport priorities','position_sentence':'A learner sentence.','essay':'A learner sentence. '*100,'requirement_notes':['Includes public transport and rural roads.']},{'response_id':'writer'}
    monkeypatch.setattr(assessment,'generate',writer)
    def forbidden(*a,**kw):raise AssertionError('Post-generation grading must not run')
    monkeypatch.setattr(assessment,'assess_model_essay',forbidden)
    monkeypatch.setattr(assessment,'complete_model_feedback',forbidden)
    return requirements,requests,writer

@pytest.mark.parametrize('target',[5,6.5,7.5,9])
def test_generated_essay_uses_target_guidance_then_commentary_without_scoring(monkeypatch,target):
    requirements,requests,_=setup_writer(monkeypatch,target);seen=[]
    def comment(req,essay,context,profile,progress):
        seen.append((req,essay,profile));return {'mode':'qualitative_commentary','criteria':[]}
    monkeypatch.setattr(commentary,'comment_on_essay',comment)
    r=assessment.generate_essay(requirements)
    assert len(requests)==len(seen)==1 and requests[0]['criterion_target_profile']==target_profile(target)
    assert r['requirements']['target_band']==target and r['status']=='generated_with_commentary'
    assert not {'assessment','target_match','target_met','overall_band','score_calculation'}.intersection(r)
    assert seen[0][1]==r['essay']


def test_content_repair_is_bounded_and_not_score_calibration(monkeypatch):
    requirements,requests,writer=setup_writer(monkeypatch)
    def broken(*a,**kw):
        v,r=writer(*a,**kw);v['essay']='Too short.';return v,r
    monkeypatch.setattr(assessment,'generate',broken)
    with pytest.raises(ModelUnavailable,match='content and length'):assessment.generate_essay(requirements)
    assert len(requests)==2 and requests[1]['validation_repair']['actual_word_count']==2


def test_commentary_repairs_only_feedback_without_rewriting_essay(monkeypatch):
    value,context,_=sample();calls=[]
    def model(system,payload,schema,temperature):
        calls.append(deepcopy(payload));v=deepcopy(value)
        if len(calls)==1:v['criteria']['TR']['essay_evidence_id']='E999'
        return v,{'response_id':str(len(calls))}
    monkeypatch.setattr(commentary,'generate',model)
    result=commentary.comment_on_essay({'prompt':'Transport question?','target_band':7.5},ESSAY,context,target_profile(7.5))
    assert len(calls)==2 and all(p['essay']==ESSAY for p in calls)
    assert 'validation_repair' in calls[1] and result['essay_sha256']

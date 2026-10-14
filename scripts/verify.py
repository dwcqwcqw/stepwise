"""Live gateway -> Qdrant -> Gemini assessment -> generation -> qualitative commentary."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE=os.getenv('STEPWISE_URL','http://localhost:8080');ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'runtime/artifacts';OUT.mkdir(parents=True,exist_ok=True)
def call(path,body=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode() if body is not None else None,headers={'content-type':'application/json'})
    with urllib.request.urlopen(req,timeout=600) as response:return json.load(response)
def save(name,value):
    p=OUT/(name+'.tmp');p.write_text(json.dumps(value,indent=2)+'\n');p.replace(OUT/name)
def check_assessment(result,essay):
    assert result['target_blind'] is True
    assert {c['criterion'] for c in result['criteria']}=={'TR','CC','LR','GRA'}
    assert len(result['model_calls'])>=1 and result['model_calls'][0]['usage']['totalTokenCount']>0
    assert result['criterion_mean']==sum(c['score'] for c in result['criteria'])/4
    assert sum(len(c['subcriteria']) for c in result['criteria'])==20
    assert result['descriptor_statements_checked']==119
    assert sum(len(r['checks']) for c in result['criteria'] for r in c['band_reviews'])==119
    assert result['score_calculation']['raw_mean']==f"{result['criterion_mean']:.2f}"
    for c in result['criteria']:
        assert type(c['score']) is int and 0<=c['score']<=9
        assert c['essay_quote'] in essay and c['example']['before'] in essay
        assert all(d['essay_quote'] in essay for d in c['subcriteria'])
        assert all(r['task'] in {'academic_task_2','shared'} for r in c['rubric'])
        assert c['score'] in {r['band'] for r in c['rubric'] if r['kind']=='band_descriptor'}
        assert all(d['source']['source_id']=='ielts-key-assessment-criteria' for d in c['subcriteria'])
        assert len(c['band_reviews'])==10 and {r['band'] for r in c['band_reviews']}==set(range(10))
        assert c['score_decision']['highest_supported_band']==c['score']
        for band in c['band_reviews']:
            for d in band['checks']:
                assert d['essay_quote'] in essay
                assert d['source']['source_id']=='ielts-writing-band-descriptors-2023'
                assert d['source']['band']==band['band'] and d['source']['criterion']==c['criterion']
                assert d['source']['page'] in {7,8,9}
            assert all(d['essay_quote'] in essay for d in band['limiters'])
for attempt in range(90):
    try:status=call('/api/ready');break
    except (urllib.error.URLError,TimeoutError,ConnectionError):
        if attempt==89:raise
        time.sleep(2)
assert status['status']=='ready' and status['points']>=110,status
save('ready.json',status)
sample=json.loads((ROOT/'data/sample_essay.json').read_text());sample.pop('target_band',None)
feedback=call('/api/feedback',sample);check_assessment(feedback,sample['essay']);assert feedback['mode']=='live_model_assessment'
save('sample_input.json',sample);save('feedback_output.json',feedback)
retrieval=call('/api/retrieve',{'query':'How can I develop and support my position with specific examples?','criterion':'TR','target_band':6.5,'top_k':2})
assert {x['band'] for x in retrieval['matches']}=={6,7};save('retrieval_example.json',retrieval)
req={'prompt':sample['prompt'],'source_essay':sample['essay'],'target_band':7,'position':'Prioritize public transport while maintaining essential roads.','ideas':'Affordability for commuters; access to jobs; lower congestion; protect rural connections.'}
generated=call('/api/model-essay',req);assert generated['status']=='generated_with_commentary' and generated['requirements']==req
assert 250<=generated['word_count']<=450
commentary=generated['commentary']
assert 'assessment' not in generated and 'overall_band' not in commentary
assert commentary['mode']=='qualitative_commentary' and len(commentary['criteria'])==4
assert sum(len(c['subcriteria']) for c in commentary['criteria'])==20
for c in commentary['criteria']:
    assert 'score' not in c and c['essay_quote'] in generated['essay'] and c['example']['before'] in generated['essay']
    assert c['rubric'][0]['source_id']=='ielts-writing-band-descriptors-2023'
    assert all(d['essay_quote'] in generated['essay'] for d in c['subcriteria'])
assert generated['generation_calls'][0]['usage']['totalTokenCount']>0
save('model_essay_request.json',req);save('model_essay_output.json',generated)
# A distinct weak answer demonstrates content-dependent live scoring.
weak={'prompt':sample['prompt'],'essay':'I think bus is good. People goes work and bus help them. Roads is also need because car use road. Government should do both. I agree transport is good because it good for people. This is my opinion.'}
weak_result=call('/api/feedback',weak);check_assessment(weak_result,weak['essay'])
assert weak_result['overall_band']<feedback['overall_band'];save('weak_essay_input.json',weak);save('weak_essay_output.json',weak_result)
for path,invalid in [('/api/feedback',dict(sample,essay='')),('/api/model-essay',dict(req,target_band=10)),('/api/model-essay',dict(req,target_band=6.3))]:
    try:call(path,invalid)
    except urllib.error.HTTPError as error:assert error.code==422
    else:raise AssertionError('Invalid input accepted')
summary={'status':'passed','checks':['entire official band PDF indexed','Task 2 score excludes Task 1','real Google model scoring and feedback','20 official subcriteria checked','verbatim essay excerpts','validated source IDs and awarded bands','target-blind assessment','half-band descriptor retrieval','complete model essay generated','model essay qualitative commentary without scoring','different weak essay scores lower','invalid input rejected'],'index_id':status['index_id'],'vectors':status['points'],'sample_band':feedback['overall_band'],'weak_band':weak_result['overall_band'],'target_band':req['target_band'],'model':feedback['model_calls'][0]['model_version'],'model_calls':sum(len(x['model_calls']) for x in [feedback,weak_result,generated['commentary']])+len(generated['generation_calls']),'feedback_latency_ms':feedback['latency_ms']}
save('verification.json',summary);print(json.dumps(summary,indent=2))

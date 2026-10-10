"""Verify the real public gateway -> API -> embedding -> vector DB flow."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.getenv('STEPWISE_URL','http://localhost:8080')
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'runtime/artifacts'
OUT.mkdir(parents=True,exist_ok=True)

def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE+path,data=data,headers={'content-type':'application/json'})
    with urllib.request.urlopen(request,timeout=120) as response: return json.load(response)

def save(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+'\n')

for attempt in range(90):
    try:
        status=call('/api/ready')
        break
    except (urllib.error.URLError,TimeoutError,ConnectionError):
        if attempt == 89: raise
        time.sleep(2)
assert status['status']=='ready' and status['points']==24,status
save('ready.json',status)
sample=json.loads((ROOT/'data/sample_essay.json').read_text())
feedback=call('/api/feedback',sample)
assert {x['criterion'] for x in feedback['criteria']} == {'TR','CC','LR','GRA'}
for card in feedback['criteria']:
    assert card['essay_quote'] in sample['essay']
    assert card['score'] is None
    assert card['rubric']
    assert all(x['criterion']==card['criterion'] and x['band']==sample['target_band'] for x in card['rubric'])
save('sample_input.json',sample)
save('feedback_output.json',feedback)
retrieval=call('/api/retrieve',{'query':'How can I develop and support my position with specific examples?','criterion':'TR','target_band':6.5,'top_k':2})
assert {x['band'] for x in retrieval['matches']} == {6,7}
assert all(x['criterion']=='TR' and x['task']=='academic_task_2' for x in retrieval['matches'])
save('retrieval_example.json',retrieval)
req={'prompt':sample['prompt'],'target_band':7,'position':'Prioritize public transport while maintaining essential roads.','ideas':'Affordability for commuters; access to jobs; lower congestion; protect rural connections.'}
outline=call('/api/model-essay',req)
assert outline['status']=='generation_pending_ms3' and outline['requirements']==req
save('model_essay_request.json',req)
save('model_essay_output.json',outline)
# Test validation through the real HTTP boundary, not only Pydantic construction.
for invalid in [dict(sample,essay=''),dict(sample,target_band=10),dict(sample,target_band=6.3)]:
    try: call('/api/feedback',invalid)
    except urllib.error.HTTPError as error: assert error.code == 422
    else: raise AssertionError('Invalid input accepted')
summary={'status':'passed','checks':['24 official rubric vectors','gateway to API','four criterion retrievals','essay quotes valid','target-band filters','half-band neighboring descriptors','model-essay requirements preserved','invalid input rejected'],'index_id':status['index_id'],'feedback_latency_ms':feedback['latency_ms'],'generation_status':outline['status'],'scoring_status':'pending MS3; no invented band scores'}
save('verification.json',summary)
print(json.dumps(summary,indent=2))

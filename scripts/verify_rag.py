"""Verify full official-rubric coverage and retrieval without calling Gemini."""
import json
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def call(path,body=None):
    r=urllib.request.Request('http://localhost:8080'+path,data=json.dumps(body).encode() if body else None,headers={'content-type':'application/json'})
    with urllib.request.urlopen(r,timeout=90) as response:return json.load(response)
quality=json.loads((ROOT/'runtime/artifacts/data_quality.json').read_text())
assert quality['descriptor_cells']==80 and quality['task2_descriptor_cells']==40 and quality['subcriteria']==20
assert quality['training_candidates_loaded']==0
status=call('/api/ready');assert status['points']==131
traces=[]
for code in ['TR','CC','LR','GRA']:
    for band in range(10):
        response=call('/api/retrieve',dict(query='Relevant position and argument development, language and organization',criterion=code,target_band=band,top_k=1))
        assert len(response['matches'])==1
        match=response['matches'][0]
        assert match['task']=='academic_task_2' and match['criterion']==code and match['band']==band
        traces.append(dict(criterion=code,band=band,chunk_id=match['chunk_id'],source_url=match['source_url'],page=match['page']))
half=call('/api/retrieve',dict(query='How can I support my ideas with relevant examples?',criterion='TR',target_band=6.5,top_k=2))
assert {x['band'] for x in half['matches']}=={6,7}
summary={'status':'passed','implementation_commit':'ef95c63e569df28d4aaa231ccf546fb68de8619d','checks':['all 80 cells from complete official band PDF','all 20 official detailed checks','131 indexed official-source chunks','40 live criterion-band queries cover Task 2 bands 0–9','no Task 1 returned','half-band 6.5 returns 6 and 7','zero MS3 training candidate records loaded'],'index_id':status['index_id'],'vectors':status['points'],'traces':traces,'generation_status':'not verified: authorized Google Cloud project required'}
p=ROOT/'runtime/artifacts/rag_verification.json';temporary=p.with_suffix('.tmp');temporary.write_text(json.dumps(summary,indent=2)+'\n');temporary.replace(p)
print(json.dumps({k:v for k,v in summary.items() if k!='traces'},indent=2))

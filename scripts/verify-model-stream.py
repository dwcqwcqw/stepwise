"""Real provider check using the repository's public sample essay, never a fixture."""
import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--public',action='store_true')
parser.add_argument('--case',choices=['feedback','model','both'],default='both')
parser.add_argument('--output',default='runtime/artifacts/streamed-model-verification.json')
args=parser.parse_args()
sample=json.loads((ROOT/'docs/evidence/sample_input.json').read_text())
headers={'Content-Type':'application/json'}
if not args.public:
    token=subprocess.check_output(['gcloud','auth','print-identity-token'],text=True).strip()
    headers['Authorization']='Bearer '+token

def run(path,body):
    started=time.monotonic();events=[];result=None
    request=urllib.request.Request(args.url+path,data=json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(request,timeout=280) as response:
        assert 'application/x-ndjson' in response.headers['Content-Type']
        for line in response:
            event=json.loads(line)
            if event['type']=='error':raise RuntimeError(event['detail'])
            if event['type']=='result':result=event['result']
            else:
                events.append(event)
                if event['type']=='progress':print(json.dumps(event),flush=True)
    assert result is not None
    return result,{'wall_seconds':round(time.monotonic()-started,3),'events':events}

receipt={'url':args.url,'sample_source':'docs/evidence/sample_input.json','cases':{}}
if args.case in {'feedback','both'}:
    result,trace=run('/api/feedback/stream',sample)
    assert result['descriptor_statements_checked']==119 and len(result['criteria'])==4
    assert result['index_id']=='34ed51cdcb06ed7c'
    assert all(c['transport']=='vertex_sse' for c in result['model_calls'])
    receipt['cases']['feedback']={**trace,'overall_band':result['overall_band'],
        'descriptor_statements_checked':result['descriptor_statements_checked'],
        'index_id':result['index_id'],'model_calls':result['model_calls']}
if args.case in {'model','both'}:
    result,trace=run('/api/model-essay/stream',{'prompt':sample['prompt'],'source_essay':sample['essay'],
                    'target_band':6.5,'position':'','ideas':''})
    assert result['status']=='generated_with_commentary' and result['requirements']['target_band']==6.5
    assert 250<=result['word_count']<=450 and len(result['commentary']['criteria'])==4
    assert all('score' not in c for c in result['commentary']['criteria'])
    calls=result['generation_calls']+result['commentary']['model_calls']
    assert all(c['transport']=='vertex_sse' for c in calls)
    receipt['cases']['model']={**trace,'target_band':6.5,'word_count':result['word_count'],
        'mode':result['commentary']['mode'],'model_calls':calls}
receipt['status']='passed'
output=ROOT/args.output;output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':'passed','cases':{k:{x:v[x] for x in v if x!='events'} for k,v in receipt['cases'].items()}},indent=2))

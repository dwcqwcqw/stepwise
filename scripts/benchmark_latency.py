"""Real Cloud Run before/after receipts; tokens stay in memory and are never printed."""
import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True,help='Authorized private Cloud Run URL')
    parser.add_argument('--output',default='runtime/artifacts/speed-after.json')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sample=json.loads((root/'data/sample_essay.json').read_text())
    sample.pop('target_band',None)
    requirements={'prompt':sample['prompt'],'target_band':7,'position':'Prioritize public transport while maintaining essential roads.','ideas':'Affordability for commuters; access to jobs; lower congestion; protect rural connections.'}
    token=subprocess.check_output(['gcloud','auth','print-identity-token'],text=True).strip()
    results=[]
    for route,data in [('feedback',sample),('model-essay',requirements)]:
        started=time.monotonic();updates=[];value=None
        request=urllib.request.Request(args.url.rstrip('/')+'/api/'+route+'/stream',data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=280) as response:
            for line in response:
                event=json.loads(line);at=round(time.monotonic()-started,3)
                if event['type']=='error':raise RuntimeError(event['detail'])
                if event['type']=='result':value=event['result']
                else:updates.append({**event,'received_seconds':at})
        assert value is not None
        elapsed=round(time.monotonic()-started,3)
        a=value.get('assessment',value);essay=value.get('essay',sample['essay'])
        checks=[s for c in a['criteria'] for b in c['band_reviews'] for s in b['checks']]
        assert len(checks)==119 and len({s['statement_id'] for s in checks})==119
        assert all(s['essay_quote'] in essay for s in checks)
        assert all(s['source']['source_id']=='ielts-writing-band-descriptors-2023' and s['source']['page'] in {7,8,9} for s in checks)
        assert {e['criterion'] for e in updates if e.get('criterion') and e.get('status')=='done'}=={'TR','CC','LR','GRA'}
        assert a['descriptor_statements_checked']==119 and a['target_blind']
        assert a['criterion_mean']==sum(c['score'] for c in a['criteria'])/4
        assert updates[0]['phase']=='accepted' and updates[0]['received_seconds']<elapsed
        calls=a['model_calls']+value.get('generation_calls',[])
        row={'route':route,'wall_seconds':elapsed,'first_event_seconds':updates[0]['received_seconds'],'statements':len(checks),'scores':[c['score'] for c in a['criteria']],'score_calculation':a['score_calculation'],'events':updates,'calls':[{k:c.get(k) for k in ['criterion','latency_ms','usage','response_id','prompt_version']} for c in calls]}
        results.append(row)
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(results,indent=2)+'\n')
        print(json.dumps({k:row[k] for k in ['route','wall_seconds','first_event_seconds','statements','scores']}),flush=True)
if __name__=='__main__':main()

"""Real private Cloud Run generation checks; runtime authorization is never saved."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import re
from pathlib import Path
import subprocess
import time
import urllib.request

def streamed_generation(url,requirements,token,updates,started):
    request=urllib.request.Request(url.rstrip('/')+'/api/model-essay/stream',data=json.dumps(requirements).encode(),
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    value=None
    with urllib.request.urlopen(request,timeout=290) as response:
        for line in response:
            event=json.loads(line)
            if event['type']=='error':raise RuntimeError(event['detail'])
            if event['type']=='result':value=event['result']
            else:updates.append({**event,'received_seconds':round(time.monotonic()-started,3)})
    if value is None:raise RuntimeError('Stream ended before its result')
    return value

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--bands',type=float,nargs='+',default=[4,5,6.5,7,8.5,9])
    parser.add_argument('--workers',type=int,choices=[1,2],default=1)
    parser.add_argument('--output',default='runtime/artifacts/target-band-verification.json')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sample=json.loads((root/'data/sample_essay.json').read_text())
    token=subprocess.check_output(['gcloud','auth','print-identity-token'],text=True).strip()
    def check(band):
        requirements={'prompt':sample['prompt'],'source_essay':sample['essay'],'target_band':band,
                      'position':'Prioritize public transport while maintaining essential roads.',
                      'ideas':'Affordability for commuters; access to jobs; lower congestion; protect rural connections.'}
        started=time.monotonic();updates=[];value=None
        try:
            value=streamed_generation(args.url,requirements,token,updates,started)
            a=value['commentary'];essay=value['essay']
            assert value['status']=='generated_with_commentary' and value['requirements']['target_band']==band
            assert 'assessment' not in value and 'overall_band' not in a
            assert len(a['criteria'])==4 and sum(len(c['subcriteria']) for c in a['criteria'])==20
            assert all('score' not in c and c['essay_quote'] in essay and c['example']['before'] in essay for c in a['criteria'])
            assert all(c['rubric'][0]['source_id']=='ielts-writing-band-descriptors-2023' for c in a['criteria'])
            result={'requested_band':band,'mode':a['mode'],
                    'wall_seconds':round(time.monotonic()-started,3),'result':value,'events':updates,'passed':True}
        except Exception as error:
            result={'requested_band':band,'passed':False,'error':str(error),'events':updates,'wall_seconds':round(time.monotonic()-started,3)}
        print(json.dumps({k:v for k,v in result.items() if k not in {'events','result'}}),flush=True)
        return result
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(check,args.bands):
            rows.append(row);output.write_text(json.dumps(rows,indent=2)+'\n')
    if not all(r['passed'] for r in rows):raise SystemExit(1)

if __name__=='__main__':main()

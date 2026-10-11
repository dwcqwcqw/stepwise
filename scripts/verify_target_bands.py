"""Real private Cloud Run generation checks; runtime authorization is never saved."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time
import urllib.request

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',required=True)
    parser.add_argument('--bands',type=float,nargs='+',default=[4,5,6.5,7,8.5,9])
    parser.add_argument('--output',default='runtime/artifacts/target-band-verification.json')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    sample=json.loads((root/'data/sample_essay.json').read_text())
    token=subprocess.check_output(['gcloud','auth','print-identity-token'],text=True).strip()
    def check(band):
        requirements={'prompt':sample['prompt'],'target_band':band,
                      'position':'Prioritize public transport while maintaining essential roads.',
                      'ideas':'Affordability for commuters; access to jobs; lower congestion; protect rural connections.'}
        started=time.monotonic();updates=[];value=None
        request=urllib.request.Request(args.url.rstrip('/')+'/api/model-essay/stream',data=json.dumps(requirements).encode(),
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=290) as response:
                for line in response:
                    event=json.loads(line)
                    if event['type']=='error':raise RuntimeError(event['detail'])
                    if event['type']=='result':value=event['result']
                    else:updates.append({**event,'received_seconds':round(time.monotonic()-started,3)})
            assert value is not None
            a=value['assessment'];essay=value['essay']
            assert a['overall_band']==band and value['target_met'] and value['target_match']['exact_match']
            assert a['target_blind'] and a['descriptor_statements_checked']==119
            checks=[s for c in a['criteria'] for b in c['band_reviews'] for s in b['checks']]
            assert len(checks)==119 and len({s['statement_id'] for s in checks})==119
            assert all(s['essay_quote'] in essay for s in checks)
            assert all(s['source']['source_id']=='ielts-writing-band-descriptors-2023' and s['source']['page'] in {7,8,9} for s in checks)
            assert a['criterion_mean']==sum(c['score'] for c in a['criteria'])/4
            result={'requested_band':band,'assessed_band':a['overall_band'],'scores':[c['score'] for c in a['criteria']],
                    'wall_seconds':round(time.monotonic()-started,3),'result':value,'events':updates,'passed':True}
        except Exception as error:
            result={'requested_band':band,'passed':False,'error':str(error),'events':updates,'wall_seconds':round(time.monotonic()-started,3)}
        print(json.dumps({k:v for k,v in result.items() if k not in {'events','result'}}),flush=True)
        return result
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(check,args.bands):
            rows.append(row);output.write_text(json.dumps(rows,indent=2)+'\n')
    if not all(r['passed'] for r in rows):raise SystemExit(1)

if __name__=='__main__':main()

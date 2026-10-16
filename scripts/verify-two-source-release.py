"""Verify the private Cloud Run release with the existing signed-in identity."""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--output',default='runtime/artifacts/two-source-http.json')
args=parser.parse_args()
token=subprocess.check_output(['gcloud','auth','print-identity-token'],text=True).strip()
def call(path,body=None):
    request=urllib.request.Request(args.url+path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=120) as response:return json.load(response)

ready=call('/ready')
assert ready['status']=='ready' and ready['points']==359
traces=[]
for code in ['TR','CC','LR','GRA']:
    for band in range(10):
        result=call('/api/retrieve',{'query':'Relevant ideas, clear organization and accurate language',
            'criterion':code,'target_band':band,'top_k':1})
        match,=result['matches']
        assert (match['task'],match['criterion'],match['band'])==('academic_task_2',code,band)
        assert match['source_id']=='ielts-writing-band-descriptors-2023'
        traces.append({key:match[key] for key in ['criterion','band','source_id','page','chunk_id']})
half=call('/api/retrieve',{'query':'Develop relevant arguments with specific examples',
                         'criterion':'TR','target_band':6.5,'top_k':2})
assert {match['band'] for match in half['matches']}=={6,7}
receipt={'status':'passed','url':args.url,'ready':ready,'criterion_band_cases':len(traces),
         'half_band_6_5_returns':[6,7],'traces':traces}
output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({key:value for key,value in receipt.items() if key!='traces'},indent=2))

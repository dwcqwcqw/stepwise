"""Vertex REST client; access tokens are read at call time and never logged."""
import json
import os
import re
import time
import threading
from pathlib import Path
import httpx

MODEL=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
PROMPT_VERSION='official-rubric-v4.2-compact-stream'
CLIENT=httpx.Client(timeout=240,limits=httpx.Limits(max_connections=12,max_keepalive_connections=8))
_metadata_token=None
_token_lock=threading.Lock()

class ModelUnavailable(RuntimeError): pass

def access_token():
    global _metadata_token
    if os.getenv('VERTEX_AUTH_MODE') == 'metadata':
        with _token_lock:
            if _metadata_token and _metadata_token[1]>time.monotonic():return _metadata_token[0]
            try:
                response=httpx.get('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'},timeout=10)
                response.raise_for_status()
                value=response.json()
                _metadata_token=(value['access_token'],time.monotonic()+max(0,value.get('expires_in',300)-60))
                return _metadata_token[0]
            except (httpx.HTTPError,KeyError,ValueError) as error:
                raise ModelUnavailable('Cloud service authorization is temporarily unavailable.') from error
    try: token=Path(os.getenv('VERTEX_TOKEN_FILE','/run/stepwise-auth/token')).read_text().strip()
    except OSError as error: raise ModelUnavailable('Google authorization unavailable. Start scripts/cloud-auth.py in your signed-in Cloud Shell.') from error
    if not token: raise ModelUnavailable('Google authorization is empty; refresh Cloud Shell authorization.')
    return token

def configuration():
    return {'provider':'Google Vertex AI','model':MODEL,'prompt_version':PROMPT_VERSION,'project_configured':bool(os.getenv('GOOGLE_CLOUD_PROJECT'))}

def generate(system, payload, schema, temperature=0.1):
    project=os.getenv('GOOGLE_CLOUD_PROJECT','')
    location=os.getenv('GOOGLE_CLOUD_LOCATION','global')
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',project): raise ModelUnavailable('Set GOOGLE_CLOUD_PROJECT to your authorized Google Cloud project.')
    token=access_token()
    host='aiplatform.googleapis.com' if location=='global' else f'{location}-aiplatform.googleapis.com'
    url=f'https://{host}/v1/projects/{project}/locations/{location}/publishers/google/models/{MODEL}:generateContent'
    body={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':[{'text':json.dumps(payload,ensure_ascii=False,separators=(',',':'))}]}],'generationConfig':{'temperature':temperature,'maxOutputTokens':16384,'responseMimeType':'application/json','responseSchema':schema}}
    if 'gemini-3' in MODEL: body['generationConfig']['thinkingConfig']={'thinkingLevel':'LOW'}
    else: body['generationConfig']['thinkingConfig']={'thinkingBudget':1024}
    started=time.monotonic()
    for attempt in range(3):
        try:
            response=CLIENT.post(url,json=body,headers={'Authorization':f'Bearer {token}'})
        except (httpx.ConnectError,httpx.RemoteProtocolError) as error:
            if attempt<2:time.sleep(2**attempt);continue
            raise ModelUnavailable('Google model request could not complete; please retry.') from error
        except httpx.HTTPError as error:raise ModelUnavailable('Google model request could not complete; please retry.') from error
        if response.status_code in {429,500,502,503} and attempt<2:
            time.sleep(2**attempt);continue
        if response.status_code>=400:
            try: message=response.json().get('error',{}).get('message','')[:700]
            except ValueError: message=''
            # Google error messages may contain project/model names, never the bearer token.
            raise ModelUnavailable(f'Google model returned HTTP {response.status_code}: {message}')
        result=response.json(); candidates=result.get('candidates',[])
        if not candidates or candidates[0].get('finishReason')!='STOP': raise ModelUnavailable('Google did not return a complete assessment; please retry.')
        text=''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
        try: value=json.loads(text)
        except ValueError as error: raise ModelUnavailable('Google returned invalid structured output; please retry.') from error
        return value,{'provider':'Google Vertex AI','model':MODEL,'model_version':result.get('modelVersion',MODEL),'response_id':result.get('responseId'),'usage':result.get('usageMetadata',{}),'latency_ms':round((time.monotonic()-started)*1000),'prompt_version':PROMPT_VERSION,'temperature':temperature}
    raise ModelUnavailable('Google model temporarily unavailable.')

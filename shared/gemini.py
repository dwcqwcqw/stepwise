"""Vertex REST client; access tokens are read at call time and never logged."""
import json
import os
import re
import time
import threading
import logging
import random
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
import httpx

MODEL=os.getenv('GEMINI_MODEL','gemini-3.5-flash')
PROMPT_VERSION='official-rubric-v4.9-compact-model-assessment'
CLIENT=httpx.Client(timeout=httpx.Timeout(75,connect=10,pool=5,write=15),limits=httpx.Limits(max_connections=12,max_keepalive_connections=8))
_metadata_token=None
_token_lock=threading.Lock()
logger=logging.getLogger(__name__)
_request_deadline=ContextVar('vertex_request_deadline',default=None)
_request_progress=ContextVar('vertex_request_progress',default=None)

@contextmanager
def request_budget(progress=None,seconds=235):
    """Leave time for a checked error before the 270-second gateway limit."""
    deadline=_request_deadline.get()
    token=_request_deadline.set(min(deadline,time.monotonic()+seconds) if deadline else time.monotonic()+seconds)
    callback=_request_progress.set(progress)
    try:yield
    finally:
        _request_progress.reset(callback);_request_deadline.reset(token)

def request_remaining(call_deadline):
    deadline=_request_deadline.get()
    return min(call_deadline,deadline if deadline is not None else call_deadline)-time.monotonic()

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
    if 'gemini-3' in MODEL:
        level=os.getenv('GEMINI_THINKING_LEVEL','LOW').upper()
        if level not in {'MINIMAL','LOW','MEDIUM','HIGH'}:raise ModelUnavailable('Invalid Gemini thinking configuration.')
        body['generationConfig']['thinkingConfig']={'thinkingLevel':level}
    else: body['generationConfig']['thinkingConfig']={'thinkingBudget':1024}
    started=time.monotonic()
    call_deadline=started+180
    for attempt in range(3):
        remaining=request_remaining(call_deadline)
        if remaining<=1:
            raise ModelUnavailable('Google model response timed out. Please try again; your writing is unchanged.')
        # Bound each attempt so a read timeout leaves room for a real retry.
        attempt_timeout=httpx.Timeout(min(75,remaining),connect=min(10,remaining),pool=min(5,remaining),write=min(15,remaining))
        retry_reason=None
        try:
            response=CLIENT.post(url,json=body,headers={'Authorization':f'Bearer {token}'},timeout=attempt_timeout)
        except (httpx.TimeoutException,httpx.NetworkError,httpx.RemoteProtocolError) as error:
            retry_reason=type(error).__name__
            logger.warning('vertex_transport_failure model=%s attempt=%s kind=%s elapsed_ms=%s',MODEL,attempt+1,retry_reason,round((time.monotonic()-started)*1000))
            if attempt==2 or request_remaining(call_deadline)<=2:
                message='Google model response timed out' if isinstance(error,httpx.TimeoutException) else 'The connection to Google was interrupted'
                raise ModelUnavailable(message+'. Please try again; your writing is unchanged.') from error
        except httpx.HTTPError as error:
            logger.warning('vertex_transport_failure model=%s kind=%s',MODEL,type(error).__name__)
            raise ModelUnavailable('The connection to Google could not complete. Please try again; your writing is unchanged.') from error
        if retry_reason is None and response.status_code in {408,429,500,502,503,504} and attempt<2:
            retry_reason='HTTP_'+str(response.status_code)
        if retry_reason:
            delay=min(2**attempt+random.uniform(0,.5),max(0,request_remaining(call_deadline)-1))
            logger.warning('vertex_request_retry model=%s attempt=%s reason=%s',MODEL,attempt+1,retry_reason)
            emit=_request_progress.get()
            if emit:emit(phase='model_retry',status='repair',message=f'Google request delayed; retrying automatically ({attempt+2} of 3)')
            time.sleep(delay);continue
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
        return value,{'provider':'Google Vertex AI','model':MODEL,'model_version':result.get('modelVersion',MODEL),'response_id':result.get('responseId'),'usage':result.get('usageMetadata',{}),'latency_ms':round((time.monotonic()-started)*1000),'prompt_version':PROMPT_VERSION,'temperature':temperature,'transport_attempts':attempt+1}
    raise ModelUnavailable('Google model temporarily unavailable.')

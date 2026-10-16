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
PROMPT_VERSION='official-rubric-v6.4-target-grounded-commentary'
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
    return {'provider':'Google Vertex AI','model':MODEL,'fallback_model':os.getenv('GEMINI_FALLBACK_MODEL') or None,'prompt_version':PROMPT_VERSION,'transport':'vertex_sse','project_configured':bool(os.getenv('GOOGLE_CLOUD_PROJECT'))}

def request_model(attempt):
    fallback=os.getenv('GEMINI_FALLBACK_MODEL','').strip()
    return fallback if fallback and attempt%2 else MODEL

def thinking_config(model):
    if 'gemini-3' not in model:return {'thinkingBudget':1024}
    level=os.getenv('GEMINI_THINKING_LEVEL','LOW').upper()
    if level not in {'MINIMAL','LOW','MEDIUM','HIGH'}:raise ModelUnavailable('Invalid Gemini thinking configuration.')
    # Gemini 3.8 rejects MINIMAL; LOW is its supported low-latency setting.
    if model.startswith('gemini-3.8') and level=='MINIMAL':level='LOW'
    return {'thinkingLevel':level}

def stream_response(url,body,token,timeout,call_deadline):
    """Consume Vertex SSE incrementally; never expose unvalidated model text.

    The read timeout measures silence between chunks, rather than waiting for
    the entire large structured rubric response. Each retry starts a new buffer.
    """
    started=time.monotonic();first_response_ms=None;last_progress=None
    parts=[];metadata={};finish=None;events=0;data=[]
    def consume(lines):
        nonlocal first_response_ms,last_progress,finish,events
        raw='\n'.join(lines)
        if not raw or raw.strip()=='[DONE]':return
        try: item=json.loads(raw)
        except ValueError as error:raise httpx.RemoteProtocolError('Invalid Google stream frame') from error
        if 'error' in item:raise httpx.RemoteProtocolError('Google stream returned an error')
        events+=1
        if first_response_ms is None:first_response_ms=round((time.monotonic()-started)*1000)
        for key in ('modelVersion','responseId','usageMetadata'):
            if key in item:metadata[key]=item[key]
        candidates=item.get('candidates',[])
        if not candidates:return
        candidate=candidates[0]
        if candidate.get('finishReason'):finish=candidate['finishReason']
        text=''.join(p.get('text','') for p in candidate.get('content',{}).get('parts',[]) if not p.get('thought'))
        if text:
            parts.append(text)
            now=time.monotonic();emit=_request_progress.get()
            if emit and (last_progress is None or now-last_progress>=8):
                emit(phase='model_response',status='running',message='Receiving the response from Google')
                last_progress=now
    with CLIENT.stream('POST',url,json=body,headers={'Authorization':f'Bearer {token}','Accept':'text/event-stream'},timeout=timeout) as response:
        if response.status_code>=400:
            response.read();return response
        for line in response.iter_lines():
            if request_remaining(call_deadline)<=0:raise httpx.ReadTimeout('Google stream deadline exceeded')
            if line.startswith('data:'):data.append(line[5:].lstrip())
            elif not line and data:consume(data);data=[]
        if data:consume(data)
        if not events or finish is None:
            raise httpx.RemoteProtocolError('Google stream ended before completion')
        result={**metadata,'candidates':[{'finishReason':finish,'content':{'parts':[{'text':''.join(parts)}]}}],
                '_stream_receipt':{'stream_events':events,'first_response_ms':first_response_ms}}
        return httpx.Response(200,request=response.request,json=result)

def generate(system, payload, schema, temperature=0.1):
    project=os.getenv('GOOGLE_CLOUD_PROJECT','')
    location=os.getenv('GOOGLE_CLOUD_LOCATION','global')
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',project): raise ModelUnavailable('Set GOOGLE_CLOUD_PROJECT to your authorized Google Cloud project.')
    token=access_token()
    host='aiplatform.googleapis.com' if location=='global' else f'{location}-aiplatform.googleapis.com'
    body={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':[{'text':json.dumps(payload,ensure_ascii=False,separators=(',',':'))}]}],'generationConfig':{'temperature':temperature,'maxOutputTokens':16384,'responseMimeType':'application/json','responseSchema':schema}}
    started=time.monotonic()
    call_deadline=started+180
    attempted_models=[]
    for attempt in range(3):
        remaining=request_remaining(call_deadline)
        if remaining<=1:
            raise ModelUnavailable('Google model response timed out. Please try again; your writing is unchanged.')
        # Bound each attempt so a read timeout leaves room for a real retry.
        attempt_timeout=httpx.Timeout(min(75,remaining),connect=min(10,remaining),pool=min(5,remaining),write=min(15,remaining))
        model=request_model(attempt)
        if not re.fullmatch(r'gemini-[a-z0-9.-]+',model):raise ModelUnavailable('Invalid Gemini model configuration.')
        url=f'https://{host}/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:streamGenerateContent?alt=sse'
        body['generationConfig']['thinkingConfig']=thinking_config(model)
        attempted_models.append(model)
        retry_reason=None
        try:
            response=stream_response(url,body,token,attempt_timeout,call_deadline)
        except (httpx.TimeoutException,httpx.NetworkError,httpx.RemoteProtocolError) as error:
            retry_reason=type(error).__name__
            logger.warning('vertex_transport_failure model=%s attempt=%s kind=%s elapsed_ms=%s',model,attempt+1,retry_reason,round((time.monotonic()-started)*1000))
            if attempt==2 or request_remaining(call_deadline)<=2:
                message='Google model response timed out' if isinstance(error,httpx.TimeoutException) else 'The connection to Google was interrupted'
                raise ModelUnavailable(message+'. Please try again; your writing is unchanged.') from error
        except httpx.HTTPError as error:
            logger.warning('vertex_transport_failure model=%s kind=%s',model,type(error).__name__)
            raise ModelUnavailable('The connection to Google could not complete. Please try again; your writing is unchanged.') from error
        if retry_reason is None and response.status_code in {408,429,500,502,503,504} and attempt<2:
            retry_reason='HTTP_'+str(response.status_code)
        if retry_reason:
            delay=min(2**attempt+random.uniform(0,.5),max(0,request_remaining(call_deadline)-1))
            logger.warning('vertex_request_retry model=%s next_model=%s attempt=%s reason=%s',model,request_model(attempt+1),attempt+1,retry_reason)
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
        return value,{'provider':'Google Vertex AI','model':model,'configured_model':MODEL,'attempted_models':attempted_models,'model_version':result.get('modelVersion',model),'response_id':result.get('responseId'),'usage':result.get('usageMetadata',{}),'latency_ms':round((time.monotonic()-started)*1000),'prompt_version':PROMPT_VERSION,'temperature':temperature,'thinking_config':thinking_config(model),'transport_attempts':attempt+1,'transport':'vertex_sse',**result.get('_stream_receipt',{})}
    raise ModelUnavailable('Google model temporarily unavailable.')

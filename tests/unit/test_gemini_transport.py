"""Actual HTTP client boundary: transient failures retry without leaking payloads."""
import json
import logging
from contextlib import contextmanager
from copy import deepcopy
import httpx
import pytest
from shared import gemini


def prepare(monkeypatch,outcomes):
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','stepwise-test-123')
    monkeypatch.setattr(gemini,'access_token',lambda:'runtime-only-secret')
    monkeypatch.setattr(gemini.time,'sleep',lambda _:None)
    calls=[]
    @contextmanager
    def stream(method,url,**kwargs):
        calls.append({'url':url,**kwargs,'json':deepcopy(kwargs['json'])})
        item=outcomes[len(calls)-1]
        if isinstance(item,Exception):raise item
        result={
            'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"ok":true}'}]}}],
            'responseId':'real-boundary-fixture'}
        yield httpx.Response(item,request=httpx.Request('POST',url),
            content=('data: '+json.dumps(result)+'\n\n').encode() if item==200 else json.dumps(result).encode(),
            headers={'content-type':'text/event-stream' if item==200 else 'application/json'})
    monkeypatch.setattr(gemini.CLIENT,'stream',stream)
    return calls


@pytest.mark.parametrize('failure',[httpx.ReadTimeout('private essay'),httpx.WriteTimeout('private essay'),httpx.ConnectError('private essay'),httpx.RemoteProtocolError('private essay')])
def test_transport_failure_retries_and_keeps_private_data_out_of_logs(monkeypatch,caplog,failure):
    calls=prepare(monkeypatch,[failure,200]);updates=[]
    with caplog.at_level(logging.WARNING),gemini.request_budget(lambda **e:updates.append(e)):
        value,receipt=gemini.generate('private essay',{'essay':'private essay'},{'type':'OBJECT'})
    assert value=={'ok':True} and receipt['transport_attempts']==2
    assert len(calls)==2 and calls[0]['timeout'].read<=75
    assert updates[0]['phase']=='model_retry'
    assert 'private essay' not in caplog.text and 'runtime-only-secret' not in caplog.text
    assert type(failure).__name__ in caplog.text


@pytest.mark.parametrize('status',[408,429,500,502,503,504])
def test_transient_http_status_retries(monkeypatch,status):
    calls=prepare(monkeypatch,[status,200])
    _,receipt=gemini.generate('role',{}, {'type':'OBJECT'})
    assert len(calls)==2 and receipt['transport_attempts']==2


def test_authentication_failure_is_not_retried(monkeypatch):
    calls=prepare(monkeypatch,[403])
    with pytest.raises(gemini.ModelUnavailable,match='HTTP 403'):gemini.generate('role',{}, {'type':'OBJECT'})
    assert len(calls)==1


def test_repeated_read_timeouts_stop_after_three_attempts(monkeypatch):
    calls=prepare(monkeypatch,[httpx.ReadTimeout('private')]*3)
    with pytest.raises(gemini.ModelUnavailable,match='response timed out'):
        gemini.generate('role',{}, {'type':'OBJECT'})
    assert len(calls)==3


def test_request_budget_prevents_starting_a_new_model_call(monkeypatch):
    calls=prepare(monkeypatch,[200])
    with gemini.request_budget(seconds=0):
        with pytest.raises(gemini.ModelUnavailable,match='timed out'):
            gemini.generate('role',{}, {'type':'OBJECT'})
    assert not calls and gemini._request_deadline.get() is None


def test_elapsed_time_caps_retry_timeout_within_shared_request_budget(monkeypatch):
    prepare(monkeypatch,[200]);now=[0.0];timeouts=[]
    monkeypatch.setattr(gemini.time,'monotonic',lambda:now[0])
    monkeypatch.setattr(gemini.time,'sleep',lambda delay:now.__setitem__(0,now[0]+delay))
    monkeypatch.setattr(gemini.random,'uniform',lambda *_:0)
    @contextmanager
    def slow(method,url,**kwargs):
        timeouts.append(kwargs['timeout'].read);now[0]+=kwargs['timeout'].read
        raise httpx.ReadTimeout('private')
        yield  # make the failure happen when the stream context is entered
    monkeypatch.setattr(gemini.CLIENT,'stream',slow)
    with gemini.request_budget(seconds=100):
        with pytest.raises(gemini.ModelUnavailable,match='timed out'):
            gemini.generate('role',{}, {'type':'OBJECT'})
    assert timeouts==[75,24] and now[0]==100


def test_parallel_criterion_calls_share_deadline_and_retry_progress(monkeypatch):
    from copy import deepcopy
    from shared import assessment
    from shared.compact import rename
    from test_assessment import referenced_fixture,ESSAY
    value,context,_=referenced_fixture();updates=[];deadlines=[]
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    def model(system,payload,schema,temperature):
        deadlines.append(gemini._request_deadline.get())
        gemini._request_progress.get()(phase='model_retry',status='repair',message='Retry fixture')
        card=deepcopy(next(c for c in value['criteria'] if c['criterion']==payload['requested_criterion']))
        return rename({'summary':value['summary'],'criteria':[card]}),{}
    monkeypatch.setattr(assessment,'generate',model)
    with gemini.request_budget(lambda **e:updates.append(e)):
        deadline=gemini._request_deadline.get()
        result=assessment.assess('Should governments fund buses?',ESSAY)
    assert deadlines==[deadline]*4 and len(updates)==4
    assert result['target_blind'] and result['descriptor_statements_checked']==40  # complete compact unit fixture

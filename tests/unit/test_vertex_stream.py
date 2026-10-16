"""Stream parsing preserves structured JSON, deadline checks and atomic retries."""
import json
from contextlib import contextmanager
import httpx
import pytest
from shared import gemini

def frame(text=None,finish=None,**metadata):
    candidate={'content':{'parts':[{'text':text}] if text is not None else []}}
    if finish:candidate['finishReason']=finish
    return {'candidates':[candidate],**metadata}

def install(monkeypatch,attempts):
    monkeypatch.setenv('GOOGLE_CLOUD_PROJECT','stepwise-test-123')
    monkeypatch.setattr(gemini,'access_token',lambda:'private-token')
    monkeypatch.setattr(gemini.time,'sleep',lambda _:None)
    calls=[]
    @contextmanager
    def stream(method,url,**kwargs):
        calls.append((url,kwargs))
        events=attempts[len(calls)-1]
        body=''.join('data: '+json.dumps(event)+'\n\n' for event in events)
        yield httpx.Response(200,request=httpx.Request(method,url),content=body.encode(),
                             headers={'content-type':'text/event-stream'})
    monkeypatch.setattr(gemini.CLIENT,'stream',stream)
    return calls

def test_fragments_and_final_usage_are_assembled_without_thought_text(monkeypatch):
    thought={'candidates':[{'content':{'parts':[{'text':'private thought','thought':True}]}}]}
    events=[thought,frame('{"ok":'),frame('true}',finish='STOP'),
            {'usageMetadata':{'totalTokenCount':42},'responseId':'stream-id','modelVersion':'model-version'}]
    calls=install(monkeypatch,[events]);updates=[]
    with gemini.request_budget(lambda **e:updates.append(e)):
        value,receipt=gemini.generate('role',{}, {'type':'OBJECT'})
    assert value=={'ok':True} and receipt['usage']=={'totalTokenCount':42}
    assert receipt['stream_events']==4 and receipt['transport_attempts']==1
    assert receipt['response_id']=='stream-id' and receipt['transport']=='vertex_sse'
    assert calls[0][0].endswith(':streamGenerateContent?alt=sse')
    assert calls[0][1]['headers']['Accept']=='text/event-stream'
    assert any(update['phase']=='model_response' for update in updates)
    assert all('private thought' not in str(update) for update in updates)

def test_truncated_attempt_is_discarded_before_retry(monkeypatch):
    calls=install(monkeypatch,[[frame('{"wrong":')],[frame('{"ok":true}',finish='STOP')]])
    value,receipt=gemini.generate('role',{}, {'type':'OBJECT'})
    assert value=={'ok':True} and receipt['transport_attempts']==2 and len(calls)==2

def test_complete_json_without_stop_is_not_accepted(monkeypatch):
    install(monkeypatch,[[frame('{"ok":true}')]]*3)
    with pytest.raises(gemini.ModelUnavailable,match='connection to Google was interrupted'):
        gemini.generate('role',{}, {'type':'OBJECT'})

def test_token_truncation_is_not_accepted_as_valid_output(monkeypatch):
    calls=install(monkeypatch,[[frame('{"ok":true}',finish='MAX_TOKENS')]])
    with pytest.raises(gemini.ModelUnavailable,match='complete assessment'):
        gemini.generate('role',{}, {'type':'OBJECT'})
    assert len(calls)==1

def test_active_stream_still_obeys_shared_deadline(monkeypatch):
    install(monkeypatch,[[frame('{"ok":true}',finish='STOP')]])
    remaining=iter([100,0])
    monkeypatch.setattr(gemini,'request_remaining',lambda _:next(remaining,0))
    with pytest.raises(gemini.ModelUnavailable,match='timed out'):
        gemini.generate('role',{}, {'type':'OBJECT'})

def test_transient_failure_switches_model_and_receipt_names_actual_provider(monkeypatch):
    from test_gemini_transport import prepare
    monkeypatch.setattr(gemini,'MODEL','gemini-3.8-flash')
    monkeypatch.setenv('GEMINI_FALLBACK_MODEL','gemini-3.5-flash')
    monkeypatch.setenv('GEMINI_THINKING_LEVEL','MINIMAL')
    calls=prepare(monkeypatch,[429,200])
    value,receipt=gemini.generate('role',{}, {'type':'OBJECT'})
    assert value=={'ok':True} and receipt['model']=='gemini-3.5-flash'
    assert receipt['attempted_models']==['gemini-3.8-flash','gemini-3.5-flash']
    assert receipt['thinking_config']=={'thinkingLevel':'MINIMAL'}
    assert '/gemini-3.8-flash:' in calls[0]['url']
    assert '/gemini-3.5-flash:' in calls[1]['url']
    assert calls[0]['json']['generationConfig']['thinkingConfig']=={'thinkingLevel':'LOW'}
    assert calls[1]['json']['generationConfig']['thinkingConfig']=={'thinkingLevel':'MINIMAL'}
    assert len(calls)==2

def test_supported_thinking_setting_is_chosen_for_each_model(monkeypatch):
    monkeypatch.setenv('GEMINI_THINKING_LEVEL','MINIMAL')
    assert gemini.thinking_config('gemini-3.8-flash')=={'thinkingLevel':'LOW'}
    assert gemini.thinking_config('gemini-3.5-flash')=={'thinkingLevel':'MINIMAL'}

def test_no_fallback_preserves_operator_chosen_model(monkeypatch):
    monkeypatch.delenv('GEMINI_FALLBACK_MODEL',raising=False)
    assert gemini.request_model(0)==gemini.request_model(1)==gemini.request_model(2)==gemini.MODEL

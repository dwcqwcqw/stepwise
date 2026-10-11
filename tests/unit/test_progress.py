import json
import threading
from copy import deepcopy
from fastapi.testclient import TestClient
from shared.compact import rename,expand,compact_schema,rubric_payload
from shared.progress import events
from shared.gemini import ModelUnavailable
from services.api import main
from test_assessment import referenced_fixture,ESSAY
from shared import assessment

def test_compact_model_output_still_passes_full_evidence_validation(monkeypatch):
    value,context,evidence=referenced_fixture()
    def model(system,payload,schema,temperature):
        code=payload['requested_criterion']
        card=deepcopy(next(c for c in value['criteria'] if c['criterion']==code))
        assert 'bands' in schema['properties']['criteria']['items']['properties']
        assert all('source_sha256' not in c for c in payload['official_assessment_context'])
        return rename({'summary':value['summary'],'criteria':[card]}),{'criterion':code}
    monkeypatch.setattr(assessment,'assessment_context',lambda _:context)
    monkeypatch.setattr(assessment,'generate',model)
    updates=[];result=assessment.assess('Should governments fund buses?',ESSAY,progress=lambda **e:updates.append(e))
    assert result['overall_band']==6
    assert {e['criterion'] for e in updates if e['phase']=='assessment' and e['status']=='done'}=={'TR','CC','LR','GRA'}
    assert updates[-1]['phase']=='validation' and updates[-1]['status']=='done'

def test_compact_transport_keeps_all_standards_and_bold_conditions():
    _,context,_=referenced_fixture()
    context['chunks'][6]['statements'][0]['limiting_features']=[{'limiter_id':'L1','text':'Bold cap.'}]
    payload=rubric_payload(context['chunks'])
    for original,compact in zip(context['chunks'],payload):
        assert compact['criterion']==original['criterion'] and compact['band']==original['band']
        if original['kind']=='band_descriptor':
            for s,c in zip(original['statements'],compact['statements']):
                assert all(s[k]==c[k] for k in ('statement_id','text','conditional','limiting_features'))
        else:assert compact['text']==original['text']
    assert len(json.dumps(payload))<len(json.dumps(context['chunks']))

def test_compact_schema_does_not_change_enum_values():
    schema={'type':'OBJECT','properties':{'statement_id':{'type':'STRING','enum':['e','TR-B7-S1']},'essay_evidence_id':{'type':'STRING'}},'required':['statement_id','essay_evidence_id']}
    packed=compact_schema(schema)
    assert packed['required']==['s','e'] and packed['properties']['s']['enum']==['e','TR-B7-S1']
    value={'essay_evidence_id':'E001','example':{'before_evidence_id':'E002'},'band_reviews':[{'checks':[{'statement_id':'TR-B7-S1','explanation':'A specific explanation.'}]}]}
    assert expand(rename(value))==value

def test_progress_is_available_before_work_finishes():
    release=threading.Event()
    def operation(emit):
        emit(phase='assessment',status='running',criterion='CC',message='Checking coherence')
        release.wait(timeout=2)
        return {'checked':True}
    stream=events(operation,heartbeat_seconds=.01)
    assert json.loads(next(stream))['phase']=='accepted'
    assert json.loads(next(stream))['criterion']=='CC'
    assert json.loads(next(stream))['type']=='heartbeat'
    release.set()
    assert json.loads(next(stream))['type']=='result'

def test_progress_failure_returns_no_unchecked_result():
    def fail(emit):raise ModelUnavailable('Evidence check failed')
    output=[json.loads(line) for line in events(fail)]
    assert [e['type'] for e in output]==['progress','error']
    assert output[-1]['detail']=='Evidence check failed'

def test_unexpected_failure_does_not_expose_private_exception():
    def fail(emit):raise ValueError('private learner text')
    output=''.join(events(fail))
    assert 'private learner text' not in output and '"type":"error"' in output

def test_stream_endpoint_validates_input_before_starting():
    client=TestClient(main.app)
    response=client.post('/api/feedback/stream',json={'prompt':'Question long enough','essay':' '})
    assert response.status_code==422

def test_stream_endpoint_preserves_final_contract(monkeypatch):
    def fake(prompt,essay,progress):
        progress(phase='validation',status='done',message='Evidence checked')
        return {'summary':'Verified feedback','overall_band':6.5,'descriptor_statements_checked':119}
    monkeypatch.setattr(main,'assess',fake)
    response=TestClient(main.app).post('/api/feedback/stream',json={'prompt':'Should governments fund public transport?','essay':ESSAY})
    output=[json.loads(line) for line in response.text.splitlines()]
    assert response.headers['content-type'].startswith('application/x-ndjson')
    assert output[1]['phase']=='validation' and output[-1]['type']=='result'
    assert output[-1]['result']['descriptor_statements_checked']==119
    assert response.headers['cache-control']=='no-store, no-transform'

import importlib.util
import io
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('verify_target_bands',Path(__file__).parents[2]/'scripts/verify_target_bands.py')
script=importlib.util.module_from_spec(spec);spec.loader.exec_module(script)

def test_real_verifier_resumes_a_new_request_with_original_target(monkeypatch):
    requests=[];token='a'*64
    def open_request(request,timeout):
        requests.append(json.loads(request.data))
        value={'status':'continuation_required','continuation_id':token} if len(requests)==1 else {'status':'generated_and_assessed','target_met':True}
        return io.BytesIO((json.dumps({'type':'result','result':value})+'\n').encode())
    monkeypatch.setattr(script.urllib.request,'urlopen',open_request)
    requirements={'target_band':7,'ideas':'bus access'}
    result=script.streamed_generation('https://example.run.app',requirements,'runtime-only',[],0)
    assert result['target_met'] and len(requests)==2
    assert requests[1]=={**requirements,'continuation_id':token}
    assert requirements=={'target_band':7,'ideas':'bus access'}

def test_real_verifier_rejects_an_incomplete_stream(monkeypatch):
    monkeypatch.setattr(script.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(b'{"type":"heartbeat"}\n'))
    with pytest.raises(RuntimeError,match='before its result'):
        script.streamed_generation('https://example.run.app',{},'runtime-only',[],0)

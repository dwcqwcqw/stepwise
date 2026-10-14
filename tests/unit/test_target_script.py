import importlib.util
import io
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('verify_target_bands',Path(__file__).parents[2]/'scripts/verify_target_bands.py')
script=importlib.util.module_from_spec(spec);spec.loader.exec_module(script)

def test_real_verifier_uses_one_request_and_preserves_preset_target(monkeypatch):
    requests=[];token='a'*64
    def open_request(request,timeout):
        requests.append(json.loads(request.data))
        value={'status':'generated_with_commentary','requirements':{'target_band':7}}
        return io.BytesIO((json.dumps({'type':'result','result':value})+'\n').encode())
    monkeypatch.setattr(script.urllib.request,'urlopen',open_request)
    requirements={'target_band':7,'ideas':'bus access'}
    result=script.streamed_generation('https://example.run.app',requirements,'runtime-only',[],0)
    assert result['requirements']['target_band']==7 and len(requests)==1
    assert requests[0]==requirements
    assert requirements=={'target_band':7,'ideas':'bus access'}

def test_real_verifier_rejects_an_incomplete_stream(monkeypatch):
    monkeypatch.setattr(script.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(b'{"type":"heartbeat"}\n'))
    with pytest.raises(RuntimeError,match='before its result'):
        script.streamed_generation('https://example.run.app',{},'runtime-only',[],0)

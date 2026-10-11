import pytest
from shared.continuation import Continuations
from shared.gemini import ModelUnavailable

def test_checkpoint_is_private_single_use_and_bound_to_original_requirements():
    sessions=Continuations();requirements={'target_band':7,'ideas':'Bus access'}
    calls=[]
    def operation(req,*,checkpoint,**kw):
        calls.append(checkpoint)
        return {'status':'continuation_required','checkpoint':{'private_essay':'unmatched'}} if checkpoint is None else {'status':'generated_and_assessed','target_met':True}
    pending=sessions.run(requirements,None,operation,None)
    assert 'checkpoint' not in pending and 'essay' not in pending
    token=pending['continuation_id']
    with pytest.raises(ModelUnavailable):sessions.run({'target_band':9},token,operation,None)
    assert sessions.run(requirements,token,operation,None)['target_met']
    assert calls==[None,{'private_essay':'unmatched'}]
    with pytest.raises(ModelUnavailable):sessions.run(requirements,token,operation,None)
    assert not sessions.entries

def test_expired_session_is_not_resumed():
    now=[0];sessions=Continuations(clock=lambda:now[0],ttl=1)
    operation=lambda *a,**kw:{'status':'continuation_required','checkpoint':{'private':'state'}}
    token=sessions.run({},None,operation,None)['continuation_id'];now[0]=2
    with pytest.raises(ModelUnavailable):sessions.run({},token,operation,None)
    assert not sessions.entries

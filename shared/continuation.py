"""One independently assessed candidate per request; opaque, temporary continuation.

Single Cloud Run instance/worker. State expires after 15 minutes, is bounded,
never logged, never persisted, and is discarded when consumed or completed.
An instance restart produces a clear retry error instead of losing validation.
"""
import secrets
import threading
import time
from shared.gemini import ModelUnavailable

class Continuations:
    def __init__(self,ttl=900,capacity=8,clock=time.monotonic):
        self.ttl=ttl;self.capacity=capacity;self.clock=clock
        self.entries={};self.lock=threading.Lock()

    def run(self,requirements,token,operation,progress):
        checkpoint=None
        with self.lock:
            now=self.clock()
            self.entries={k:v for k,v in self.entries.items() if v[0]>now}
            if token:
                item=self.entries.get(token)
                if item is None or item[1]!=requirements:
                    raise ModelUnavailable('Your writing session expired or changed. Please generate again; your requirements are unchanged.')
                checkpoint=self.entries.pop(token)[2]
        result=operation(requirements,progress=progress,checkpoint=checkpoint,pause_after_candidate=True)
        if result.get('status')!='continuation_required':return result
        token=secrets.token_hex(32)
        with self.lock:
            if len(self.entries)>=self.capacity:
                raise ModelUnavailable('The writing service is busy. Please retry; your requirements are unchanged.')
            self.entries[token]=(self.clock()+self.ttl,dict(requirements),result['checkpoint'])
        return {'status':'continuation_required','continuation_id':token}

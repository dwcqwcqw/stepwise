"""Request-scoped progress stream; no task database or saved learner text."""
import json
import logging
import queue
import threading
import time
from shared.gemini import ModelUnavailable

logger=logging.getLogger(__name__)

def events(operation, heartbeat_seconds=10):
    updates=queue.Queue()
    disconnected=threading.Event()
    started=time.monotonic()
    def emit(**event):
        if not disconnected.is_set():updates.put({'type':'progress',**event,'elapsed_ms':round((time.monotonic()-started)*1000)})
    def work():
        try:
            result=operation(emit)
            if not disconnected.is_set():updates.put({'type':'result','result':result,'elapsed_ms':round((time.monotonic()-started)*1000)})
        except ModelUnavailable as error:
            if not disconnected.is_set():updates.put({'type':'error','detail':str(error)})
        except Exception:
            # Exception values can include learner text; keep them out of logs/events.
            logger.error('stream_operation_failed')
            if not disconnected.is_set():updates.put({'type':'error','detail':'Assessment evidence could not be validated. Please retry; your text is unchanged.'})
    yield json.dumps({'type':'progress','phase':'accepted','status':'done','message':'Request received; preparing your writing','elapsed_ms':0})+'\n'
    threading.Thread(target=work,daemon=True).start()
    try:
        while True:
            try:event=updates.get(timeout=heartbeat_seconds)
            except queue.Empty:event={'type':'heartbeat','elapsed_ms':round((time.monotonic()-started)*1000)}
            yield json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'
            if event['type'] in {'result','error'}:break
    finally:disconnected.set()

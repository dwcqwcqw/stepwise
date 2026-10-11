import test from 'node:test';
import assert from 'node:assert/strict';
import {readEvents,streamedRequest} from '../services/web/static/progress.js';

function stream(parts){return new ReadableStream({start(controller){for(const p of parts)controller.enqueue(p);controller.close();}});}
test('fragmented UTF-8 events preserve order and the final result',async()=>{
  const text='{"type":"progress","message":"Checking – evidence","phase":"assessment"}\n{"type":"heartbeat"}\n{"type":"result","result":{"score":6.5}}\n';
  const bytes=new TextEncoder().encode(text),seen=[];
  const result=await readEvents(stream([...bytes].map(b=>new Uint8Array([b]))),e=>seen.push(e));
  assert.equal(seen[0].message,'Checking – evidence');assert.equal(seen[1].type,'heartbeat');assert.equal(result.score,6.5);
});
test('a disconnected stream never looks like success',async()=>{
  await assert.rejects(readEvents(stream([new TextEncoder().encode('{"type":"progress"}\n')]),()=>{}),/ended before/);
});
test('server validation errors reach the user without an unchecked score',async()=>{
  await assert.rejects(readEvents(stream([new TextEncoder().encode('{"type":"error","detail":"Evidence failed"}\n')]),()=>{}),/Evidence failed/);
});
test('only identical verified feedback is reused; changed inputs and generation run again',async()=>{
  const original=globalThis.fetch;let calls=0;
  globalThis.fetch=async()=>{calls++;return new Response('{"type":"result","result":{"score":6.5}}\n',{headers:{'Content-Type':'application/x-ndjson'}});};
  try{
    await streamedRequest('/api/feedback/stream',{essay:'one'},()=>{});
    const reused=await streamedRequest('/api/feedback/stream',{essay:'one'},()=>{});
    assert.equal(calls,1);assert.equal(reused.session_reused,true);
    await streamedRequest('/api/feedback/stream',{essay:'two'},()=>{});
    await streamedRequest('/api/model-essay/stream',{ideas:'one'},()=>{});
    await streamedRequest('/api/model-essay/stream',{ideas:'one'},()=>{});
    assert.equal(calls,4);
  }finally{globalThis.fetch=original;}
});

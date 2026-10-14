import test from 'node:test';
import assert from 'node:assert/strict';
import {readEvents,streamedRequest,generatedRequest} from '../services/web/static/progress.js';

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

test('generation uses one request and returns the preset target with qualitative commentary',async()=>{
  const original=globalThis.fetch,requests=[];
  globalThis.fetch=async(path,options)=>{
    requests.push({path,value:JSON.parse(options.body)});
    const result={status:'generated_with_commentary',requirements:{target_band:7.5},essay:'Model essay',commentary:{mode:'qualitative_commentary'}};
    return new Response(JSON.stringify({type:'result',result})+'\n',{headers:{'Content-Type':'application/x-ndjson'}});
  };
  try{
    const result=await generatedRequest({target_band:7.5,ideas:'Bus access'},()=>{});
    assert.equal(requests.length,1);assert.equal(requests[0].path,'/api/model-essay/stream');
    assert.equal(result.requirements.target_band,7.5);assert.equal(result.assessment,undefined);
    assert.equal(result.commentary.mode,'qualitative_commentary');
  }finally{globalThis.fetch=original;}
});

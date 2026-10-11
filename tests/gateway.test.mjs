import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import handler from '../api/gateway.mjs';

test('gateway forwards progress before completion and reuses unexpired identity',{timeout:5000},async()=>{
  const savedFetch=globalThis.fetch,savedEnv={...process.env};
  Object.assign(process.env,{VERCEL_OIDC_TOKEN:'unit-test-only',VERCEL_ENV:'production',STEPWISE_API_URL:'https://unit-test.run.app',GCP_WIF_AUDIENCE:'unit-test-audience',GCP_INVOKER_EMAIL:'unit-test@example.com'});
  let exchanges=0,identities=0,controller,resolveWritten;
  const firstWritten=new Promise(resolve=>resolveWritten=resolve);
  const token='header.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600})).toString('base64url')+'.signature';
  process.env.VERCEL_OIDC_TOKEN=token;
  delete process.env.VERCEL_OIDC_TOKEN_FILE;
  globalThis.fetch=async(url)=>{
    if(url.includes('sts.googleapis.com')){exchanges++;return Response.json({access_token:'unit-test-only'});}
    if(url.includes('iamcredentials.googleapis.com')){identities++;return Response.json({token});}
    return new Response(new ReadableStream({start(c){controller=c;c.enqueue(new TextEncoder().encode('{"type":"progress","phase":"retrieval"}\n'));}}),{headers:{'Content-Type':'application/x-ndjson'}});
  };
  class Result extends EventEmitter {
    constructor(){super();this.headers={};this.chunks=[];this.destroyed=false;}
    setHeader(k,v){this.headers[k]=v;}
    flushHeaders(){this.headersSent=true;}
    write(c){this.chunks.push(Buffer.from(c));resolveWritten();return true;}
    end(c){if(c)this.chunks.push(Buffer.from(c));this.ended=true;}
    status(n){this.statusCode=n;return this;}
    json(v){this.end(JSON.stringify(v));}
  }
  try {
    const res=new Result(),pending=handler({query:{path:'feedback/stream'},method:'POST',body:{essay:'sample'}},res);
    await firstWritten;
    assert.equal(res.ended,undefined);assert.equal(res.headers['Content-Type'],'application/x-ndjson; charset=utf-8');
    controller.enqueue(new TextEncoder().encode('{"type":"result","result":{"checked":119}}\n'));controller.close();await pending;
    assert.equal(JSON.parse(Buffer.concat(res.chunks).toString().trim().split('\n')[1]).result.checked,119);
    const again=new Result(),next=handler({query:{path:'model-essay/stream'},method:'POST',body:{}},again);
    // Observe the second request's first forwarded chunk before releasing its stream.
    await new Promise(resolve=>{resolveWritten=resolve;});
    controller.close();await next;
    assert.equal(exchanges,1);assert.equal(identities,1);
  }finally{globalThis.fetch=savedFetch;for(const key of Object.keys(process.env))if(!(key in savedEnv))delete process.env[key];Object.assign(process.env,savedEnv);}
});

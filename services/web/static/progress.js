/** Parse request-scoped server events, including fragmented UTF-8 and JSON lines. */
export async function readEvents(body, onEvent) {
  if (!body) throw new Error('Your browser could not open the progress connection. Please retry.');
  const reader=body.getReader(),decoder=new TextDecoder();let pending='',result,finished=false;
  function accept(line){
    if(!line.trim())return;
    const event=JSON.parse(line);
    if(event.type==='error')throw new Error(event.detail||'Please retry; your text is unchanged.');
    if(event.type==='result'){if(finished)throw new Error('Duplicate assessment result.');result=event.result;finished=true;}
    else onEvent(event);
  }
  try {
    while(true){const {value,done}=await reader.read();pending+=decoder.decode(value,{stream:!done});let newline;
      while((newline=pending.indexOf('\n'))>=0){accept(pending.slice(0,newline));pending=pending.slice(newline+1);}
      if(done)break;
    }
    if(pending.trim())accept(pending);
    if(!finished)throw new Error('The connection ended before the assessment was ready. Please retry; your text is unchanged.');
    return result;
  } finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
}

// Only verified feedback is reused within this tab; nothing enters persistent storage.
const feedbackCache=new Map();
export async function streamedRequest(path,value,onEvent){
  const key=path+'\n'+JSON.stringify(value),cached=path.includes('/feedback/')&&feedbackCache.get(key);
  if(cached){onEvent({type:'progress',phase:'cached',status:'done',message:'Reusing your verified review from this tab'});return {...cached,session_reused:true};}
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
  if(!response.ok){let body;try{body=await response.json();}catch{}throw new Error(typeof body?.detail==='string'?body.detail:'Please check your inputs and retry.');}
  if(!response.headers.get('content-type')?.includes('application/x-ndjson'))throw new Error('The progress connection is unavailable. Please refresh and retry.');
  const result=await readEvents(response.body,onEvent);
  if(path.includes('/feedback/')){feedbackCache.set(key,result);if(feedbackCache.size>3)feedbackCache.delete(feedbackCache.keys().next().value);}
  return result;
}

export function startProgress(kind){
  const panel=document.getElementById('processing'),isModel=kind==='model';
  const rows=isModel?[['generation','Write your essay'],['assessment','Check your band'],['validation','Prepare your feedback']]:[['assessment','Review your writing'],['validation','Prepare your feedback']];
  const criteria=new Map(),started=performance.now();
  const controls=[...document.querySelectorAll('button, textarea, select')].filter(e=>!e.disabled);
  controls.forEach(e=>e.disabled=true);document.body.classList.add('processing');
  panel.innerHTML=`<div class="processing-heading"><div class="ai-orbit" aria-hidden="true">✦</div><div><p class="eyebrow">Stepwise is working</p><h2>${isModel?'An essay shaped around your ideas.':'A closer look at your writing.'}</h2><p class="processing-caption">${isModel?'Writing, checking and preparing your feedback.':'Checking your writing against official IELTS standards.'}</p></div><span class="processing-elapsed">0s elapsed</span></div><ol class="processing-steps">${rows.map(([key,label],i)=>`<li data-phase="${key}" data-state="waiting"><span class="step-indicator">${i+1}</span><div><strong>${label}</strong><small>Waiting</small></div><span class="step-state">Waiting</span></li>`).join('')}</ol><p class="processing-message" role="status" aria-live="polite">Connecting to your writing review…</p><p class="processing-footnote">You can keep this tab open. Your writing stays here if a connection fails.</p>`;
  panel.classList.remove('hidden');panel.setAttribute('aria-busy','true');
  panel.scrollIntoView({behavior:'smooth',block:'start'});
  const clock=setInterval(()=>{panel.querySelector('.processing-elapsed').textContent=`${Math.floor((performance.now()-started)/1000)}s elapsed`;},1000);
  function update(event){
    if(event.type==='heartbeat')return;
    panel.dataset.currentPhase=event.phase;panel.dataset.serverElapsed=event.elapsed_ms??'';
    panel.querySelector('.processing-message').textContent=event.message;
    if(isModel&&event.phase==='generation'&&event.status==='repair'&&event.attempt>1){
      criteria.clear();
      for(const key of ['assessment','validation']){
        const pendingRow=panel.querySelector(`[data-phase="${key}"]`);pendingRow.dataset.state='waiting';
        pendingRow.querySelector('.step-state').textContent='Waiting';pendingRow.querySelector('small').textContent='Waiting';
        pendingRow.querySelector('.step-indicator').textContent=rows.findIndex(([phase])=>phase===key)+1;
      }
    }
    const phase=event.phase==='generation_retrieval'?'generation':(['retrieval','calibration'].includes(event.phase)?'assessment':event.phase);
    const row=panel.querySelector(`[data-phase="${phase}"]`);
    if(event.criterion){
      criteria.set(event.criterion,event.status);
    }
    if(row){
      const done=phase==='assessment'?[...criteria.values()].filter(v=>v==='done').length:0;
      const complete=phase==='assessment'?(event.phase==='assessment'&&done===4)||(event.phase==='calibration'&&event.status==='done'):event.status==='done'&&event.phase!=='generation_retrieval';
      if(!complete)row.querySelector('.step-indicator').textContent=rows.findIndex(([key])=>key===phase)+1;
      row.dataset.state=complete?'done':'running';row.querySelector('.step-state').textContent=complete?'Done':'In progress';
      row.querySelector('small').textContent=phase==='assessment'?`${done} of 4 criteria checked`:event.status==='done'?'Complete':event.message;
      if(complete)row.querySelector('.step-indicator').textContent='✓';
    }
  }
  function stop(){clearInterval(clock);controls.forEach(e=>e.disabled=false);document.body.classList.remove('processing');panel.classList.add('hidden');panel.setAttribute('aria-busy','false');}
  return {update,stop};
}

// Each candidate gets its own bounded gateway request. Progress remains visible
// across candidates; an opaque server token resumes the same validated session.
export async function generatedRequest(value,onEvent){
  let continuation;
  for(let attempt=0;attempt<3;attempt++){
    const result=await streamedRequest('/api/model-essay/stream',
      continuation?{...value,continuation_id:continuation}:value,onEvent);
    if(result.status!=='continuation_required')return result;
    if(!/^[a-f0-9]{64}$/.test(result.continuation_id||''))throw new Error('The writing session could not continue. Please generate again.');
    continuation=result.continuation_id;
  }
  throw new Error('The writing session did not complete. Please retry; your requirements are unchanged.');
}

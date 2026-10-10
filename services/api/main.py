"""Typed essay endpoints backed by real rubric retrieval; model interfaces staged for MS3."""
import re
import time
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator
from shared.common import DATA, CRITERIA
from shared.retrieval import active_index, database, retrieve

app = FastAPI(title='Stepwise',version='0.2.0',description='MS2: real retrieval, typed essay input, and a working UI. Model-based scoring and essay generation follow in MS3.')
Criterion = Literal['TR','CC','LR','GRA']

class RetrievalRequest(BaseModel):
    query: str = Field(min_length=5,max_length=4000)
    criterion: Criterion
    target_band: float = Field(ge=4,le=9,multiple_of=0.5)
    top_k: int = Field(default=2,ge=1,le=4)

class EssayRequest(BaseModel):
    prompt: str = Field(min_length=10,max_length=2000)
    essay: str = Field(min_length=80,max_length=15000)
    target_band: float = Field(default=7,ge=4,le=9,multiple_of=0.5)
    @field_validator('prompt','essay')
    @classmethod
    def content_required(cls,value):
        if len(value.strip()) < 10: raise ValueError('Please enter meaningful text')
        return value.strip()

class ModelEssayRequest(BaseModel):
    prompt: str = Field(min_length=10,max_length=2000)
    target_band: float = Field(ge=4,le=9,multiple_of=0.5)
    position: str = Field(min_length=5,max_length=1500)
    ideas: str = Field(min_length=10,max_length=4000)

SUGGESTIONS = {
 'TR': ('Make each main idea do more work.','State a claim, explain why it follows, and add one relevant example.','Public transport is useful.','Affordable buses can widen access to jobs because workers can reach employers beyond walking distance; for example, a low-cost commuter pass can connect outer suburbs to the city.'),
 'CC': ('Give each paragraph one clear purpose.','Use a topic sentence, develop that point, and make the connection to the next paragraph explicit.','It is cheap. Pollution is a problem.','Alongside lower travel costs, reliable public transport can reduce pollution by replacing some journeys made in private cars.'),
 'LR': ('Choose precise words for your meaning.','Replace broad words with accurate topic vocabulary and check the surrounding word combination.','There are many good things.','Two potential benefits are lower commuting costs and wider access to employment.'),
 'GRA': ('Use sentence variety with control.','Combine two related ideas with a clear subordinate clause, then check agreement and punctuation.','Buses are cheap. People can use them.','Because buses are affordable, more residents can use them for daily travel.'),
}

@app.get('/health')
def health(): return {'status':'ok','milestone':'MS2','input_mode':'typed_or_pasted_text'}

@app.get('/ready')
def ready():
    try:
        index = active_index()
        count = database().count(index['collection'],exact=True).count
        if count != index['points']: raise ValueError('Index incomplete')
        return {'status':'ready',**index}
    except Exception as error:
        raise HTTPException(503,'Rubric index unavailable; run make run and inspect pipeline logs.') from error

@app.post('/api/retrieve')
def retrieve_context(request: RetrievalRequest):
    try: return retrieve(**request.model_dump())
    except Exception as error: raise HTTPException(503,'Retrieval unavailable; inspect index service logs.') from error

@app.post('/api/feedback')
def feedback(request: EssayRequest):
    started = time.monotonic()
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+',request.essay) if s.strip()]
    cards = []
    try:
        for n,(code,name) in enumerate(CRITERIA.items()):
            title,step,before,after = SUGGESTIONS[code]
            quote = sentences[min(n,len(sentences)-1)]
            context = retrieve(f'{name}. {request.prompt} {quote}',code,request.target_band)
            if not context['matches']: raise ValueError('No rubric matches')
            cards.append({'criterion':code,'name':name,'score':None,'score_status':'Awaiting calibrated model in MS3','essay_quote':quote,'title':title,'next_step':step,'example':{'before':before,'after':after,'type':'illustrative example, not an automatic correction of your text'},'rubric':context['matches']})
        return {'mode':'rubric_retrieval_preview','notice':'MS2 preview: rubric retrieval is live. Suggestions are curated practice templates; band scoring and individualized model feedback will be added in MS3.','word_count':len(request.essay.split()),'target_band':request.target_band,'criteria':cards,'latency_ms':round((time.monotonic()-started)*1000),'index_id':active_index()['index_id']}
    except Exception as error: raise HTTPException(503,'Rubric context unavailable; please check /ready.') from error

@app.post('/api/model-essay')
def model_essay(request: ModelEssayRequest):
    try: context=retrieve(f'{request.prompt} {request.position} {request.ideas}','TR',request.target_band)
    except Exception as error: raise HTTPException(503,'Rubric retrieval unavailable') from error
    return {'status':'generation_pending_ms3','notice':'Your requirements and rubric context are ready. Model essay generation and its separate four-criterion scoring pass will be connected in MS3.','requirements':request.model_dump(),'outline':[{'section':'Introduction','purpose':f'Introduce the question and state your position: {request.position}'},{'section':'Body paragraphs','purpose':f'Develop your requested ideas with reasons and examples: {request.ideas}'},{'section':'Conclusion','purpose':'Summarize the argument and return to the question.'}],'rubric':context['matches']}

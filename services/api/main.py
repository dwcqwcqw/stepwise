"""Live Gemini scoring, actionable revisions, targeted generation and qualitative commentary."""
import time
from typing import Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from fastapi.responses import StreamingResponse
from shared.progress import events
from shared.retrieval import active_index, database, retrieve
from shared.assessment import assess, generate_essay
from shared.gemini import ModelUnavailable, configuration

app=FastAPI(title='Stepwise',version='0.3.0',description='Live rubric-grounded IELTS essay feedback and targeted model essays with qualitative commentary.')
Criterion=Literal['TR','CC','LR','GRA']
class RetrievalRequest(BaseModel):
    query: str=Field(min_length=5,max_length=4000)
    criterion: Criterion
    target_band: float=Field(ge=0,le=9,multiple_of=0.5)
    top_k: int=Field(default=2,ge=1,le=4)
class EssayRequest(BaseModel):
    prompt: str=Field(min_length=10,max_length=2000)
    essay: str=Field(min_length=1,max_length=15000)
    @field_validator('prompt','essay')
    @classmethod
    def content_required(cls,value):
        if not value.strip(): raise ValueError('Please enter meaningful text')
        return value.strip()
class ModelEssayRequest(BaseModel):
    prompt: str=Field(min_length=10,max_length=2000)
    target_band: float=Field(ge=4,le=9,multiple_of=0.5)
    source_essay: str=Field(default='',max_length=15000)
    position: str=Field(default='',max_length=1500)
    ideas: str=Field(default='',max_length=4000)
    @field_validator('prompt')
    @classmethod
    def nonblank_prompt(cls,value):
        if not value.strip(): raise ValueError('Please enter a meaningful question')
        return value.strip()
    @field_validator('source_essay','position','ideas')
    @classmethod
    def trim_optional(cls,value):
        return value.strip()
    @model_validator(mode='after')
    def source_or_position(self):
        if not self.source_essay and not self.position:
            raise ValueError('Add your original essay in step 1 or enter a position.')
        return self

@app.get('/health')
def health(): return {'status':'ok','milestone':'MS2','input_mode':'typed_or_pasted_text'}
@app.get('/ready')
def ready():
    try:
        index=active_index();count=database().count(index['collection'],exact=True).count
        if count!=index['points']: raise ValueError('Index incomplete')
        return {'status':'ready',**index,'generation':configuration()}
    except Exception as error: raise HTTPException(503,'Official rubric index unavailable; inspect pipeline logs.') from error
@app.post('/api/retrieve')
def retrieve_context(request:RetrievalRequest):
    try:return retrieve(**request.model_dump())
    except Exception as error:raise HTTPException(503,'Official rubric retrieval unavailable.') from error
@app.post('/api/feedback')
def feedback(request:EssayRequest):
    started=time.monotonic()
    try:
        result=assess(request.prompt,request.essay)
        return {'mode':'live_model_assessment',**result,'notice':result['summary'],'latency_ms':round((time.monotonic()-started)*1000)}
    except ModelUnavailable as error:raise HTTPException(503,str(error)) from error
    except Exception as error:raise HTTPException(503,'Assessment evidence could not be validated; inspect the official rubric pipeline.') from error
@app.post('/api/model-essay')
def model_essay(request:ModelEssayRequest):
    try:return generate_essay(request.model_dump())
    except ModelUnavailable as error:raise HTTPException(503,str(error)) from error
    except Exception as error:raise HTTPException(503,'Model essay feedback evidence could not be validated; please retry.') from error

STREAM_HEADERS={'Cache-Control':'no-store, no-transform','X-Accel-Buffering':'no'}

@app.post('/api/feedback/stream')
def feedback_stream(request:EssayRequest):
    def operation(progress):
        started=time.monotonic()
        result=assess(request.prompt,request.essay,progress=progress)
        return {'mode':'live_model_assessment',**result,'notice':result['summary'],'latency_ms':round((time.monotonic()-started)*1000)}
    return StreamingResponse(events(operation),media_type='application/x-ndjson',headers=STREAM_HEADERS)

@app.post('/api/model-essay/stream')
def model_essay_stream(request:ModelEssayRequest):
    requirements=request.model_dump()
    return StreamingResponse(events(lambda progress:generate_essay(requirements,progress)),media_type='application/x-ndjson',headers=STREAM_HEADERS)

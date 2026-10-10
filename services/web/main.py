"""Same-origin frontend gateway; the browser never connects directly to the vector DB."""
import os
from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title='Stepwise Web')
STATIC = Path(__file__).parent/'static'
app.mount('/static',StaticFiles(directory=STATIC),name='static')

@app.get('/')
def home(): return FileResponse(STATIC/'index.html')

@app.get('/health')
def health(): return {'status':'ok'}

@app.api_route('/api/{path:path}',methods=['GET','POST'])
async def proxy(path: str,request: Request):
    async with httpx.AsyncClient(timeout=600) as client:
        target = '/ready' if path == 'ready' else f'/api/{path}'
        try:
            result=await client.request(request.method,os.getenv('API_URL','http://api:8000')+target,content=await request.body(),headers={'content-type':'application/json'})
            return Response(result.content,status_code=result.status_code,media_type='application/json')
        except httpx.HTTPError:
            return Response('{"detail":"The API is unavailable. Please check the running containers."}',status_code=503,media_type='application/json')

import asyncio
import logging
import os
import time
import uuid
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import ValidationError
from .llm import Ollama
from .models import AnalyzeRequest, AnalyzeResponse
from .service import analyze_extraction

MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2')
URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434')
TIMEOUT = float(os.getenv('OLLAMA_TIMEOUT', '120'))
MAX_INPUT = int(os.getenv('MAX_INPUT_LENGTH', '2000'))
MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', '1'))
if TIMEOUT <= 0 or MAX_INPUT < 1 or MAX_CONCURRENCY < 1:
    raise ValueError('Configuration limits must be positive')
app = FastAPI(title='Patient Pharmacy Assistance', version='0.1.0')
log = logging.getLogger('pharmacy_service')
capacity = asyncio.Queue(maxsize=MAX_CONCURRENCY)
for _ in range(MAX_CONCURRENCY):
    capacity.put_nowait(object())

def get_llm():
    return Ollama(URL, MODEL, TIMEOUT)

@app.get('/health')
async def health():
    return {'status': 'ok'}

@app.post('/api/analyze', response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, llm=Depends(get_llm)):
    if len(request.text) > MAX_INPUT:
        raise HTTPException(422, 'text exceeds configured maximum')
    try:
        token = capacity.get_nowait()
    except asyncio.QueueEmpty:
        raise HTTPException(503, 'processing capacity saturated', headers={'Retry-After': '1'})
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    category = 'ok'
    try:
        context = request.context.model_dump(exclude_none=True) if request.context else None
        text = ' '.join(request.text.split())
        extraction = await asyncio.wait_for(llm.extract(text, context), timeout=TIMEOUT)
        return analyze_extraction(request_id, request, extraction)
    except (asyncio.TimeoutError, httpx.TimeoutException):
        category = 'timeout'
        raise HTTPException(504, 'model timeout')
    except httpx.HTTPError:
        category = 'ollama_unavailable'
        raise HTTPException(503, 'Ollama unavailable')
    except (ValidationError, ValueError, KeyError, TypeError):
        category = 'invalid_model_output'
        raise HTTPException(502, 'invalid model output')
    finally:
        capacity.put_nowait(token)
        log.info('request_id=%s duration_ms=%.1f model=%s category=%s', request_id, (time.monotonic()-started)*1000, MODEL, category)

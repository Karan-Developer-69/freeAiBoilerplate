import os
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ollama import AsyncClient

app = FastAPI()

# --- SECURITY SETUP ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Ye key Hugging Face Secrets se aayegi
MASTER_KEY = 'lysis69'

async def verify_api_key(api_key: str = Security(api_key_header)):
    # 1. Agar Server par Key set nahi hai, toh error do (Security First)
    if not MASTER_KEY:
        raise HTTPException(status_code=500, detail="Server Error: API_KEY not set in Secrets")
        
    # 2. Agar Key match nahi karti
    if api_key != MASTER_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid Master Key")
    
    return True

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-pro-preview"
    temperature: float = 0.7
    max_tokens: int = 4096

# --- HOME ROUTE ---
@app.get("/")
def home():
    return {"status": "Online", "message": "Secure AI API is Running. Auth Required."}

# --- GENERATION ROUTE ---
@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_text(request: QueryRequest):
    async def stream_generator():
        try:
            client = AsyncClient()
            messages = [
                {'role': 'system', 'content': 'You are a helpful coding assistant.'},
                {'role': 'user', 'content': request.prompt}
            ]
            async for part in await client.chat(
                model=request.model,
                messages=messages,
                stream=True,
                options={'temperature': request.temperature, 'num_predict': request.max_tokens}
            ):
                content = part['message']['content']
                if content: yield content
        except Exception as e:
            yield f"[Error: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")
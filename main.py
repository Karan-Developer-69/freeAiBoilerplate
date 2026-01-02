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
SERVER_API_KEY = os.environ.get("API_KEY") # HF Secret se lega

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not SERVER_API_KEY:
        return True # Agar key set nahi hai to allow karo (Dev mode)
    if api_key_header == SERVER_API_KEY:
        return True
    raise HTTPException(status_code=403, detail="Invalid API Key")

# --- REQUEST MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    # Default model updated to Gemini 3 Pro
    model: str = "gemini-3-pro-preview"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(4096, description="Max response length")

@app.get("/")
def home():
    return {"message": "Gemini 3 Pro API is Live on Hugging Face!"}

@app.post("/generate", dependencies=[Depends(get_api_key)])
async def generate_text(request: QueryRequest):
    async def stream_generator():
        try:
            client = AsyncClient()
            
            # System prompt add kiya hai for better coding
            messages = [
                {'role': 'system', 'content': 'You are an expert Coding Assistant. Write efficient, modern code.'},
                {'role': 'user', 'content': request.prompt}
            ]

            async for part in await client.chat(
                model=request.model,
                messages=messages,
                stream=True,
                options={
                    'temperature': request.temperature,
                    'num_predict': request.max_tokens,
                }
            ):
                content = part['message']['content']
                if content:
                    yield content

        except Exception as e:
            yield f"\n[Error: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")
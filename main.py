from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx # Hum direct HTTP request karenge, ollama library slow ho sakti hai
import json

app = FastAPI()

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "deepseek-coder-v2"
    temperature: float = 0.6
    max_tokens: int = 4096

@app.get("/")
def home():
    return {"status": "Online", "mode": "Turbo Proxy Mode"}

@app.post("/generate")
async def generate_text(request: QueryRequest):
    # Ollama ka local URL (HF spaces me usually yahi hota hai)
    OLLAMA_API_URL = "http://localhost:11434/api/chat"
    
    # Payload tayar karo jo seedha Ollama ko jayega
    payload = {
        "model": request.model,
        "messages": [{'role': 'user', 'content': request.prompt}],
        "stream": True, # Hamesha stream true rakhenge internal processing ke liye
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
            # Hack: Context window chota rakhne se speed badhti hai
            "num_ctx": 2048 
        }
    }

    async def proxy_generator():
        timeout = httpx.Timeout(120.0, connect=60.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                # Seedha Ollama ke API ko hit karte hain
                async with client.stream("POST", OLLAMA_API_URL, json=payload) as response:
                    async for chunk in response.aiter_lines():
                        if chunk:
                            # Ollama RAW JSON bhejta hai. 
                            # Hum usse parse karke sirf text nikal kar bhejenge taaki payload chota ho.
                            try:
                                data = json.loads(chunk)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except:
                                pass
            except Exception as e:
                yield f"[Error: {str(e)}]"

    return StreamingResponse(proxy_generator(), media_type="text/plain")
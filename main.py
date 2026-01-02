from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ollama import AsyncClient

app = FastAPI()

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "deepseek-coder-v2"  # Model set to DeepSeek V2
    temperature: float = 0.6          # Coding ke liye thoda kam temperature behtar hai
    max_tokens: int = 4096            # Lambe code ke liye

# --- HOME ROUTE ---
@app.get("/")
def home():
    return {"status": "Online", "message": "DeepSeek Coder V2 API is Running Publicly!"}

# --- GENERATION ROUTE (Public) ---
@app.post("/generate")
async def generate_text(request: QueryRequest):
    async def stream_generator():
        try:
            client = AsyncClient()
            messages = [
                {'role': 'system', 'content': 'You are an intelligent coding assistant. Write clean and efficient code.'},
                {'role': 'user', 'content': request.prompt}
            ]
            
            # Streaming Response
            async for part in await client.chat(
                model=request.model,
                messages=messages,
                stream=True,
                options={
                    'temperature': request.temperature,
                    'num_predict': request.max_tokens
                }
            ):
                content = part['message']['content']
                if content:
                    yield content

        except Exception as e:
            yield f"[Error: {str(e)}]"

    return StreamingResponse(stream_generator(), media_type="text/plain")
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ollama import AsyncClient

app = FastAPI()

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-pro-preview"
    temperature: float = 0.7
    max_tokens: int = 4096

# --- HOME ROUTE ---
@app.get("/")
def home():
    return {"status": "Online", "message": "Public AI API is Running!"}

# --- GENERATION ROUTE (No Password Required) ---
@app.post("/generate")
async def generate_text(request: QueryRequest):
    async def stream_generator():
        try:
            client = AsyncClient()
            messages = [
                {'role': 'system', 'content': 'You are a helpful coding assistant.'},
                {'role': 'user', 'content': request.prompt}
            ]
            
            # Request processing
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
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from ollama import AsyncClient
import asyncio # Import asyncio for waiting on non-streaming responses

app = FastAPI()

# --- DATA MODEL ---
class QueryRequest(BaseModel):
    prompt: str
    model: str = "deepseek-coder-v2"  # Model set to DeepSeek V2
    temperature: float = 0.6          # Coding ke liye thoda kam temperature behtar hai
    max_tokens: int = 4096            # Lambe code ke liye
    stream: bool = True               # New field: whether to stream or not

# --- HOME ROUTE ---
@app.get("/")
def home():
    return {"status": "Online", "message": "DeepSeek Coder V2 API is Running Publicly!"}

# --- GENERATION ROUTE (Public) ---
@app.post("/generate")
async def generate_text(request: QueryRequest):
    client = AsyncClient()
    messages = [
        {'role': 'system', 'content': 'You are an intelligent coding assistant. Write clean and efficient code.'},
        {'role': 'user', 'content': request.prompt}
    ]

    if request.stream:
        async def stream_generator():
            try:
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
    else:
        # Non-streaming response
        full_response_content = []
        try:
            # The client.chat call for non-streaming still uses stream=True internally
            # to efficiently get the data from Ollama. We then collect it.
            async for part in await client.chat(
                model=request.model,
                messages=messages,
                stream=True, # We still stream from Ollama to this server
                options={
                    'temperature': request.temperature,
                    'num_predict': request.max_tokens
                }
            ):
                content = part['message']['content']
                if content:
                    full_response_content.append(content)

            # Join all parts to form the complete response
            final_text = "".join(full_response_content)
            return JSONResponse(content={"response": final_text})

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
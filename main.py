from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama
import json

app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str
    model: str = "deepseek-coder-v2"

@app.get("/")
def home():
    return {"message": "DeepSeek Coder V2 (Streaming) is Live!"}

@app.post("/generate")
def generate_text(request: QueryRequest):
    # Generator function jo data tukdon (chunks) me bhejega
    def stream_generator():
        try:
            stream = ollama.chat(
                model=request.model,
                messages=[{'role': 'user', 'content': request.prompt}],
                stream=True,  # Yahan streaming ON ki hai
            )
            
            for chunk in stream:
                # Sirf content nikal kar client ko bhejo
                content = chunk['message']['content']
                if content:
                    yield content

        except Exception as e:
            yield f"Error: {str(e)}"

    # FastAPI ko StreamingResponse return karein
    return StreamingResponse(stream_generator(), media_type="text/plain")
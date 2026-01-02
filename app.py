from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import requests

app = FastAPI(
    title="Free Ollama API",
    description="Ollama running in background. Model: llama3.2:1b",
    version="1.0"
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:1b"

@app.get("/")
def root():
    return {"message": "Ollama API live है! Swagger के लिए /docs खोलो। Model: llama3.2:1b"}

@app.post("/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        body["model"] = MODEL

        resp = requests.post(OLLAMA_URL, json=body, stream=True, timeout=300)
        resp.raise_for_status()

        def generate():
            for chunk in resp.iter_lines():
                if chunk:
                    yield chunk + b"\n"

        return StreamingResponse(generate(), media_type="application/x-ndjson")
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import requests

app = FastAPI(title="Ollama Phi-3 Mini API")

OLLAMA_URL = "http://localhost:11434/api/chat"

@app.get("/")
def root():
    return {"message": "Ollama Phi-3 Mini API चल रहा है! POST /chat पर messages भेजो।"}

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    body["model"] = "phi3:mini"   # fixed model

    resp = requests.post(OLLAMA_URL, json=body, stream=True)
    resp.raise_for_status()

    def generate():
        for chunk in resp.iter_lines():
            if chunk:
                yield chunk + b"\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
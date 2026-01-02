from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import requests
import json

app = FastAPI(title="Ollama Phi-3 Mini API")

OLLAMA_URL = "http://localhost:11434/api/chat"

@app.get("/")
def root():
    return {"message": "Ollama API चल रहा है! /chat POST करो।"}

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    body["model"] = "phi3:mini"  # अपना model

    resp = requests.post(OLLAMA_URL, json=body, stream=True)
    resp.raise_for_status()

    def generate():
        for chunk in resp.iter_lines():
            if chunk:
                yield chunk + b"\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

# Simple test endpoint
@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    body["model"] = "phi3:mini"
    resp = requests.post("http://localhost:11434/api/generate", json=body, stream=True)
    return StreamingResponse(resp.iter_content(), media_type="application/x-ndjson")
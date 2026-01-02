from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import requests
import subprocess
import time

app = FastAPI(title="Ollama Gemma-2-2B API")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma2:2b"

@app.get("/")
def root():
    return {"message": "Ollama API ready! पहली request पर gemma2:2b auto download होगा। /docs से test करो।"}

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    body["model"] = MODEL_NAME

    # Model check और auto pull (पहली बार)
    try:
        requests.get("http://localhost:11434/api/tags", timeout=5)
    except:
        subprocess.run(["ollama", "pull", MODEL_NAME])
        time.sleep(10)  # load hone ka time

    resp = requests.post(OLLAMA_URL, json=body, stream=True, timeout=300)
    if resp.status_code != 200:
        return JSONResponse(status_code=resp.status_code, content={"error": resp.text})

    def generate():
        for chunk in resp.iter_lines():
            if chunk:
                yield chunk + b"\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
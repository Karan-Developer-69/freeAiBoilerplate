from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse
import requests

app = FastAPI(title="Free Ollama API")

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:1b"  # या जो तुमने pull किया

# ये key fix – root पर HTML page दिखाओ HF को satisfy करने के लिए
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head>
            <title>Free Ollama API Live!</title>
            <style>
                body { font-family: system-ui, sans-serif; margin: 40px; background: #f0f0f0; text-align: center; }
                h1 { color: #0066cc; }
                a { color: #0066cc; font-size: 1.2em; }
            </style>
        </head>
        <body>
            <h1>🚀 Ollama API Running Hai Bhai!</h1>
            <p>Model: llama3.2:1b (या तुम्हारा model)</p>
            <p>Interactive docs यहाँ देखो:</p>
            <ul>
                <li><a href="/docs" target="_blank">Swagger UI (/docs)</a></li>
                <li><a href="/redoc" target="_blank">ReDoc (/redoc)</a></li>
            </ul>
            <p>API endpoint: POST /chat (messages array भेजो)</p>
            <hr>
            <small>Deployed on Hugging Face Spaces | Free CPU Tier</small>
        </body>
    </html>
    """

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    body["model"] = MODEL

    resp = requests.post(OLLAMA_URL, json=body, stream=True)
    resp.raise_for_status()

    def generate():
        for chunk in resp.iter_lines():
            if chunk:
                yield chunk + b"\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
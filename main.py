import os
import sqlite3
import uuid
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from ollama import AsyncClient

app = FastAPI()

# --- DATABASE SETUP (SQLite) ---
DB_FILE = "apikeys.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table banayein agar nahi hai
    c.execute('''CREATE TABLE IF NOT EXISTS keys 
                 (username TEXT, api_key TEXT PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# App start hone par DB initialize karein
init_db()

# --- SECURITY SETUP ---
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Ye wo key hai jo aapne HF Secrets mein set ki thi (Backup ke liye)
MASTER_KEY = 'lysis69'

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=403, detail="API Key is missing")
    
    # 1. Pehle check karo ki kya ye Master Key hai? (Admin Access)
    if MASTER_KEY and api_key == MASTER_KEY:
        return True

    # 2. Agar Master Key nahi hai, to Database check karo (User Access)
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username FROM keys WHERE api_key=?", (api_key,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return True # Key mil gayi
    else:
        # Debugging ke liye Logs mein print karein
        print(f"Failed Login Attempt with Key: {api_key}") 
        raise HTTPException(status_code=403, detail="Invalid API Key: Key not found in DB")
        
# --- DATA MODELS ---
class KeyGenerationRequest(BaseModel):
    username: str

class QueryRequest(BaseModel):
    prompt: str
    model: str = "gemini-3-pro-preview"
    temperature: float = 0.7
    max_tokens: int = 4096

# --- HTML DASHBOARD (UI) ---
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Get Your API Key</title>
        <style>
            body { font-family: sans-serif; background: #121212; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e1e1e; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); text-align: center; width: 350px; }
            input { width: 90%; padding: 10px; margin: 10px 0; border-radius: 5px; border: none; }
            button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
            button:hover { background: #0056b3; }
            .key-display { margin-top: 20px; word-break: break-all; color: #4CAF50; font-weight: bold; display: none; background: #2d2d2d; padding: 10px; border-radius: 5px; }
            h2 { color: #007bff; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🚀 Free AI API</h2>
            <p>Enter your name to generate a free API Key.</p>
            <input type="text" id="username" placeholder="Your Name" required>
            <button onclick="generateKey()">Generate API Key</button>
            <div id="result" class="key-display"></div>
        </div>

        <script>
            async function generateKey() {
                const name = document.getElementById('username').value;
                if(!name) return alert("Please enter a name");
                
                const btn = document.querySelector('button');
                btn.disabled = true;
                btn.innerText = "Generating...";

                const res = await fetch('/new-key', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: name})
                });

                const data = await res.json();
                const display = document.getElementById('result');
                display.style.display = 'block';
                display.innerText = data.api_key;
                
                btn.disabled = false;
                btn.innerText = "Generate Another";
            }
        </script>
    </body>
    </html>
    """

# --- NEW KEY GENERATION ENDPOINT ---
@app.post("/new-key")
def create_key(req: KeyGenerationRequest):
    new_key = f"sk-{uuid.uuid4()}" # Random Unique Key
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO keys (username, api_key) VALUES (?, ?)", (req.username, new_key))
    conn.commit()
    conn.close()
    
    return {"status": "success", "username": req.username, "api_key": new_key}

# --- CHAT GENERATION (SECURED) ---
@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_text(request: QueryRequest):
    async def stream_generator():
        try:
            client = AsyncClient()
            messages = [
                {'role': 'system', 'content': 'You are a helpful coding assistant.'},
                {'role': 'user', 'content': request.prompt}
            ]
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
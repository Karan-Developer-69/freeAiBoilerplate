from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama

app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str
    model: str = "tinyllama"  # Default model

@app.get("/")
def home():
    return {"message": "Ollama API is running on Hugging Face Spaces!"}

@app.post("/generate")
def generate_text(request: QueryRequest):
    try:
        # Ollama library ka use karke response generate karein
        response = ollama.chat(model=request.model, messages=[
          {
            'role': 'user',
            'content': request.prompt,
          },
        ])
        return {"response": response['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Note: App run command entrypoint.sh mein hoga

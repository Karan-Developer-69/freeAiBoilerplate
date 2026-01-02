from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import ollama

app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str
    # Default model ab coding expert wala set kar diya hai
    model: str = "deepseek-coder"

@app.get("/")
def home():
    return {"message": "Coding Expert AI is Live!"}

@app.post("/generate")
def generate_text(request: QueryRequest):
    try:
        # System prompt add kiya hai taaki wo ache se code likhe
        response = ollama.chat(model=request.model, messages=[
          {
            'role': 'system',
            'content': 'You are an expert coding assistant. Write clean, efficient, and well-commented code.'
          },
          {
            'role': 'user',
            'content': request.prompt,
          },
        ])
        return {"response": response['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
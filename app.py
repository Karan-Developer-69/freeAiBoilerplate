from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline
import torch

app = FastAPI(title="Gemma-2-2B Text Chat API")

# छोटा model, CPU पर perfect (low memory ~4-5GB)
generator = pipeline(
    "text-generation",
    model="google/gemma-2-2b-it",
    torch_dtype=torch.float32,
    device_map="cpu"
)

class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 256
    temperature: float = 0.7

@app.get("/")
def root():
    return {"message": "Gemma-2-2B API चल रहा है! /docs पर test करो।"}

@app.post("/chat")
def chat(request: ChatRequest):
    # Gemma chat format (simple prompt)
    full_prompt = f"<start_of_turn>user\n{request.prompt}<end_of_turn>\n<start_of_turn>model\n"

    outputs = generator(
        full_prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        do_sample=True,
        return_full_text=False
    )

    response = outputs[0]["generated_text"]
    return {"response": response}
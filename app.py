import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import io

app = FastAPI(title="Phi-3 Mini Text Generator API")

# Model load (CPU पर, bfloat16 अगर support हो वरना float32)
model_id = "microsoft/Phi-3-mini-4k-instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float32,  # CPU के लिए float32 safe (bfloat16 अगर error दे तो)
    device_map="cpu",           # Force CPU
    trust_remote_code=True      # Phi-3 के लिए जरूरी
)

# Text generation pipeline
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    device_map="cpu"
)

class ChatRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9

@app.get("/")
def root():
    return {"message": "Phi-3 Mini Text API चल रहा है! /docs पर Swagger UI देखो। POST /chat पर prompt भेजो।"}

@app.post("/chat")
async def chat(request: ChatRequest):
    outputs = generator(
        request.prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        do_sample=True,
        return_full_text=False
    )

    response_text = outputs[0]["generated_text"]

    # Streaming अगर चाहो (real-time words), नहीं तो direct text
    def stream_response():
        for token in response_text:
            yield token

    return StreamingResponse(stream_response(), media_type="text/plain")
    
    # या simple text return: return {"response": response_text}
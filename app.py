import torch
from diffusers import FluxPipeline
from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image
import io
import base64
from fastapi.responses import StreamingResponse

app = FastAPI(title="FLUX.1 Schnell Image Generator")

# Model load (पहली request पर load होगा, थोड़ा time लगेगा)
pipe = FluxPipeline.from_pretrained(
    "black-forest-labs/FLUX.1-schnell",
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
)
pipe.enable_model_cpu_offload()  # Memory save के लिए

class ImageRequest(BaseModel):
    prompt: str
    num_inference_steps: int = 4  # Schnell के लिए low steps fast
    height: int = 1024
    width: int = 1024
    guidance_scale: float = 3.5

@app.get("/")
def root():
    return {"message": "FLUX Image Generator API चल रहा है! /docs पर Swagger UI देखो।"}

@app.post("/generate")
async def generate_image(request: ImageRequest):
    image = pipe(
        prompt=request.prompt,
        num_inference_steps=request.num_inference_steps,
        height=request.height,
        width=request.width,
        guidance_scale=request.guidance_scale,
    ).images[0]

    # Image को bytes में convert (base64 या direct bytes)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")
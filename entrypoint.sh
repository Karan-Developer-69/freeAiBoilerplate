#!/bin/bash

# 1. Ollama server start karein
ollama serve &

# 2. Wait karein
echo "Waiting for Ollama server to start..."
sleep 5

# 3. DeepSeek Coder V2 Pull karein
# Note: Ye model bada hai, download hone me time lega.
echo "Pulling DeepSeek Coder V2..."
ollama pull deepseek-coder-v2

# 4. FastAPI start karein
echo "Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 7860
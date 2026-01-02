#!/bin/bash

# 1. Ollama Server Start
ollama serve &

echo "Waiting for Ollama server..."
sleep 5

# 2. DeepSeek Model Pull
# Note: Ye model bada hai, download hone mein 2-3 minute lag sakte hain
echo "Pulling DeepSeek Coder V2..."
ollama pull deepseek-coder-v2

# 3. FastAPI Start
echo "Starting Public API..."
uvicorn main:app --host 0.0.0.0 --port 7860
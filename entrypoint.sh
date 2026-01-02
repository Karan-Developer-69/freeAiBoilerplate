#!/bin/bash

# 1. Ollama server start karein
ollama serve &

# 2. Wait karein start hone ka
echo "Waiting for Ollama server to start..."
sleep 5

# 3. Best Coding Model Pull karein
# Note: 7b model thoda heavy hai, agar slow lage to 'qwen2.5-coder:1.5b' use karein
echo "Pulling Qwen 2.5 Coder model..."
ollama pull deepseek-coder

# 4. FastAPI start karein
echo "Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 7860
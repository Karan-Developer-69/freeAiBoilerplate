#!/bin/bash

# 1. Ollama Server Start (Background mein)
# Hum yahan API KEY pass kar rahe hain taaki Ollama Google se connect ho sake
GEMINI_API_KEY=$GEMINI_API_KEY ollama serve &

echo "Waiting for Ollama..."
sleep 5

# 2. Gemini Model Pull Karein
echo "Connecting to Gemini 3 Pro..."
# Note: Ye bohot fast hoga kyunki ye cloud model hai
ollama pull gemini-3-pro-preview

# 3. FastAPI Start
echo "Starting API Server..."
uvicorn main:app --host 0.0.0.0 --port 7860 --workers 4
#!/bin/bash

# Ollama server background में start
echo "Starting Ollama server in background..."
ollama serve &

# थोड़ा wait Ollama ready होने के लिए
sleep 15

# Model auto pull (पहली बार, छोटा model रखो stable के लिए)
if ! ollama list | grep -q "llama3.2:1b"; then
    echo "Pulling llama3.2:1b model..."
    ollama pull llama3.2:1b
fi

# FastAPI को main process बनाओ (foreground)
echo "Starting FastAPI on port 8000..."
exec uvicorn app:app --host 0.0.0.0 --port 8000
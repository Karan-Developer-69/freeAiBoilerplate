#!/bin/bash

# Ollama server background में start करो
ollama serve &

# थोड़ा wait server ready होने के लिए
sleep 10

# Optional: model auto pull अगर नहीं है (lazy)
if ! ollama list | grep -q "gemma2:2b"; then
    echo "Model pull कर रहा हूँ..."
    ollama pull gemma2:2b
fi

# FastAPI foreground में run करो (ये main process बनेगा)
exec uvicorn app:app --host 0.0.0.0 --port 8000
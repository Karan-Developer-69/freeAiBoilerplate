#!/bin/bash

# 1. Ollama server ko background mein start karein
ollama serve &

# 2. Server start hone ka wait karein
echo "Waiting for Ollama server to start..."
sleep 5

# 3. Model Pull karein 
# (CPU Free tier ke liye 'tinyllama' best hai. Agar GPU hai to 'llama3' use karein)
echo "Pulling model..."
ollama pull tinyllama

# 4. FastAPI Server start karein port 7860 par
echo "Starting FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 7860
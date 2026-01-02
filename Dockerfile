FROM ollama/ollama:latest

# Model pull (build समय पर download हो जाएगा, छोटा model चुनो)
RUN ollama pull phi3:mini   # या gemma2:2b, llama3.2:3b (3B तक ok free CPU पर)

# FastAPI dependencies
RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install fastapi uvicorn requests

# App copy
COPY app.py /app.py

# Expose ports (Ollama 11434 + FastAPI 8000)
EXPOSE 11434
EXPOSE 8000

# Ollama server background में + FastAPI foreground में
CMD ollama serve & uvicorn app.py:app --host 0.0.0.0 --port 8000
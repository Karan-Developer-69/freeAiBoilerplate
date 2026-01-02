FROM ollama/ollama:latest

WORKDIR /app

# Python packages install
RUN pip install --no-cache-dir fastapi uvicorn requests

# App copy
COPY app.py /app/app.py

EXPOSE 8000
EXPOSE 11434

# Ollama server background + FastAPI
CMD ollama serve & uvicorn app:app --host 0.0.0.0 --port 8000
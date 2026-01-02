FROM ollama/ollama:latest

WORKDIR /app

# Python और pip install
RUN apt-get update && apt-get install -y python3 python3-pip

# Packages install with break-system-packages (Docker safe)
RUN python3 -m pip install --no-cache-dir fastapi uvicorn requests --break-system-packages

# App copy
COPY app.py /app/app.py

EXPOSE 8000
EXPOSE 11434

# Ollama + FastAPI run
CMD ollama serve & uvicorn app:app --host 0.0.0.0 --port 8000
FROM ollama/ollama:latest

WORKDIR /app

# Python aur pip install करो (must step)
RUN apt-get update && apt-get install -y python3 python3-pip

# Python packages install
RUN python3 -m pip install --no-cache-dir fastapi uvicorn requests

# App copy
COPY app.py /app/app.py

EXPOSE 8000
EXPOSE 11434

# Ollama serve background + FastAPI
CMD ollama serve & uvicorn app:app --host 0.0.0.0 --port 8000
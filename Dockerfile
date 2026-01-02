FROM ollama/ollama:latest

WORKDIR /app

# Python और pip install
RUN apt-get update && apt-get install -y python3 python3-pip

# FastAPI dependencies
RUN python3 -m pip install --no-cache-dir fastapi uvicorn requests --break-system-packages

# entrypoint copy और executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# App copy
COPY app.py /app/app.py

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
FROM ollama/ollama:latest

WORKDIR /app

# Python और pip install
RUN apt-get update && apt-get install -y python3 python3-pip

# Packages install (--break-system-packages safe in Docker)
RUN python3 -m pip install --no-cache-dir fastapi uvicorn requests --break-system-packages

# entrypoint script copy और executable बना लो
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# App copy
COPY app.py /app/app.py

EXPOSE 8000
EXPOSE 11434

# entrypoint set करो
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
FROM ollama/ollama:latest

# Ollama image में पहले से UID 1000 user होता है, extra useradd मत करो

# Working directory set करो
WORKDIR /app

# Model build time पर pull करो (server background में start करके)
RUN ollama serve & \
    sleep 15 && \
    ollama pull gemma2:2b    # छोटा और fastest model (2B) – phi3:mini की जगह ये रखो ताकि free CPU पर super fast चले

# Python packages install (Ollama image में Python पहले से होता है)
RUN pip install --no-cache-dir fastapi uvicorn requests

# FastAPI wrapper code copy
COPY app.py /app/app.py

# Ports expose
EXPOSE 8000    
EXPOSE 11434   

# Runtime: Ollama server background + FastAPI foreground
CMD ollama serve & uvicorn app:app --host 0.0.0.0 --port 8000
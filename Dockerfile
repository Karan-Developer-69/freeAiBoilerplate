FROM ollama/ollama:latest

# HF Spaces के लिए user setup (जरूरी नहीं लेकिन safe)
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user

# पहले Ollama server background में start करो, फिर model pull
RUN ollama serve & \
    sleep 10 && \
    ollama pull phi3:mini

# FastAPI dependencies install
RUN pip install fastapi uvicorn requests --user

# App file copy
COPY app.py /home/user/app.py

# Ports expose
EXPOSE 11434   # Ollama direct API (optional)
EXPOSE 8000    # FastAPI wrapper

# Final command: Ollama serve background + FastAPI foreground
CMD ollama serve & uvicorn app.py:app --host 0.0.0.0 --port 8000
FROM ollama/ollama:latest

# HF Spaces के लिए user setup
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user

# Ollama server start करके model pull करो
RUN ollama serve & \
    sleep 10 && \
    ollama pull phi3:mini   # यहाँ comment अलग line पर है, safe

# Python dependencies install
RUN pip install fastapi uvicorn requests --user

# App file copy
COPY app.py /home/user/app.py

# Ports expose (comments अलग line पर)
EXPOSE 11434    # Ollama direct API (optional, लेकिन HF Spaces में proxy से काम करेगा)
EXPOSE 8000     # FastAPI wrapper port

# Runtime command
CMD ollama serve & uvicorn app.py:app --host 0.0.0.0 --port 8000
FROM python:3.11

# 1. Root bankar Ollama install karein
RUN curl -fsSL https://ollama.com/install.sh | sh

# 2. User create karein
RUN useradd -m -u 1000 user

# 3. Environment Variables set karein
ENV USER=user
ENV PATH="/home/user/.local/bin:$PATH"
ENV HOME=/home/user
# Gemini API Key ko pass karne ke liye (Runtime pe secret se uthayega)
ENV OLLAMA_KEEP_ALIVE=5m

# 4. User switch
USER user
WORKDIR $HOME/app

# 5. Libraries Install
RUN pip install --no-cache-dir fastapi uvicorn ollama

# 6. Copy Files
COPY --chown=user . .

# 7. Permissions
RUN chmod +x entrypoint.sh

# 8. Expose Port
EXPOSE 7860

# 9. Start
CMD ["./entrypoint.sh"]
FROM python:3.11

# 1. System dependencies (curl, zstd, zsh)
RUN apt-get update && apt-get install -y \
    curl \
    zstd \
    zsh \
    git \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# 3. User Setup
RUN useradd -m -u 1000 user
ENV USER=user
ENV HOME=/home/user
ENV PATH="$HOME/.local/bin:$PATH"
ENV OLLAMA_KEEP_ALIVE=5m

# 4. Workdir
WORKDIR $HOME/app

# 5. Switch to non-root user
USER user

# 6. Install Python Libraries
RUN pip install --no-cache-dir fastapi uvicorn ollama

# 7. Copy project files
COPY --chown=user . .

# 8. Entrypoint permission
RUN chmod +x entrypoint.sh

# 9. Expose Port
EXPOSE 7860

# 10. Default shell (zsh)
SHELL ["/bin/zsh", "-c"]

CMD ["./entrypoint.sh"]

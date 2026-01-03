FROM python:3.11

# 1. Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# 2. User Setup
RUN useradd -m -u 1000 user
ENV USER=user
ENV PATH="/home/user/.local/bin:$PATH"
ENV HOME=/home/user
ENV OLLAMA_KEEP_ALIVE=5m

# 3. Workdir
WORKDIR $HOME/app

# 4. Switch User
USER user

# 5. Install Python Libs
RUN pip install --no-cache-dir fastapi uvicorn ollama pydantic langchain langchain-community langchain-ollama duckduckgo-search httpx

# 6. Copy Files
COPY --chown=user . .

# 7. Start Script Permission
RUN chmod +x entrypoint.sh

# 8. Ports
EXPOSE 7860
CMD ["./entrypoint.sh"]
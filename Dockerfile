FROM python:3.11

# 1. Root bankar Ollama Binary install karein
RUN curl -fsSL https://ollama.com/install.sh | sh

# 2. User create karein
RUN useradd -m -u 1000 user

# 3. Env variables set karein
ENV USER=user
ENV PATH="/home/user/.local/bin:$PATH"
ENV HOME=/home/user

# 4. User switch karein
USER user
WORKDIR $HOME/app

# 5. Libraries Direct Install karein (requirements.txt ki zaroorat hata di hai taaki error fix ho jaye)
RUN pip install --no-cache-dir fastapi uvicorn ollama

# 6. Baaki files copy karein
COPY --chown=user . .

# 7. Permissions set karein
RUN chmod +x entrypoint.sh

# 8. Port expose
EXPOSE 7860

# 9. Start
CMD ["./entrypoint.sh"]
FROM python:3.11

# 1. Sabse pehle ROOT bankar Ollama install karein (User create karne se pehle)
RUN curl -fsSL https://ollama.com/install.sh | sh

# 2. Ab User create karein (Hugging Face security requirement)
RUN useradd -m -u 1000 user

# 3. Environment variables set karein
ENV USER=user
ENV PATH="/home/user/.local/bin:$PATH"
ENV HOME=/home/user

# 4. Ab User par switch karein
USER user
WORKDIR $HOME/app

# 5. Python requirements copy aur install karein
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 6. Baaki files copy karein
COPY --chown=user . .

# 7. Script ko executable banayein
RUN chmod +x entrypoint.sh

# 8. Port expose karein
EXPOSE 7860

# 9. Entrypoint script chalayein
CMD ["./entrypoint.sh"]
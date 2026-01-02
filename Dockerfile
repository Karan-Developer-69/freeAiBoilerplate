FROM python:3.11

# User create karein (Hugging Face security requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
ENV HOME=/home/user

WORKDIR $HOME/app

# Ollama install karein
RUN curl -fsSL https://ollama.com/install.sh | sh

# Python requirements copy aur install karein
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Baaki files copy karein
COPY --chown=user . .

# Script ko executable banayein
RUN chmod +x entrypoint.sh

# Port expose karein (Hugging Face 7860 use karta hai)
EXPOSE 7860

# Entrypoint script chalayein
CMD ["./entrypoint.sh"]
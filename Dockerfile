FROM python:3.9

# HF required user setup
RUN useradd -m -u 1000 user

USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements (बिना torch वाले)
COPY --chown=user requirements.txt .

# Pip upgrade
RUN pip install --no-cache-dir --upgrade pip

# Normal packages install (PyPI से fastapi आदि)
RUN pip install --no-cache-dir -r requirements.txt

# PyTorch CPU-only अलग install (custom index से)
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio

# App code copy
COPY --chown=user . .

# Port
EXPOSE 7860

# Run
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
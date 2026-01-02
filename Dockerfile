FROM python:3.10-slim

# User setup (HF requirement)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

# Dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# App code
COPY --chown=user app.py .

# Run
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
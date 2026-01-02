FROM python:3.9

# Hugging Face required user setup
RUN useradd -m -u 1000 user

# Switch to user
USER user

# Set home and PATH (important – pip user install के लिए)
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Working directory
WORKDIR $HOME/app

# Copy requirements
COPY --chown=user requirements.txt .

# Upgrade pip and install dependencies (user के बाद, PATH set के बाद)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY --chown=user . .

# Expose port
EXPOSE 7860

# Run FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
FROM python:3.9

# Hugging Face Spaces के लिए user setup (must)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
ENV PATH="\( {HOME}/.local/bin: \){PATH}"
WORKDIR ${HOME}/app

# Requirements copy और install
COPY --chown=user requirements.txt .
RUN pip install --upgrade pip  # पहले pip upgrade (important fix)
RUN pip install --no-cache-dir -r requirements.txt

# App code copy
COPY --chown=user . .

# Port expose (FastAPI के लिए 7860 common है, या 8000)
EXPOSE 7860

# Run
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
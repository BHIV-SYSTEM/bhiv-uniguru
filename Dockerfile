FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1

COPY backend/requirements.txt /app/backend/requirements.txt

# Install CPU-only PyTorch first.
# This avoids pulling NVIDIA/CUDA packages into the production image.
RUN python -m pip install --upgrade pip && \
    python -m pip install \
      --index-url https://download.pytorch.org/whl/cpu \
      "torch==2.11.0+cpu" && \
    python -m pip install \
      -r /app/backend/requirements.txt

COPY . /app

RUN python /app/backend/scripts/build_rag_index.py

EXPOSE 8000

CMD ["python", "/app/backend/main.py"]

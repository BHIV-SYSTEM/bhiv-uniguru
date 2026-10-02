FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["sh", "-c", "uvicorn service.api:app --host ${UNIGURU_HOST:-0.0.0.0} --port ${UNIGURU_PORT:-8000} --workers ${UNIGURU_WORKERS:-1}"]

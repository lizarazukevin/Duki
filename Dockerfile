FROM python:3.14.2-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 duky

EXPOSE 8000

USER duky

CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

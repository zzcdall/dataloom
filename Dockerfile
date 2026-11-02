FROM node:20-alpine AS web

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATALOOM_DATA_DIR=/data

WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./backend/
COPY backend/app ./backend/app
RUN pip install --no-cache-dir ./backend

COPY --from=web /app/frontend/dist ./frontend/dist
COPY examples ./examples

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]


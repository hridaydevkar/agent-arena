# UI is compiled inside the image build; host node_modules are never copied.
FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ARENA_DATA_DIR=/data \
    ARENA_FRONTEND_DIR=/app/frontend/dist
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY backend/ ./backend/
COPY sdk/ ./sdk/
COPY public-data/ ./public-data/
RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 arena \
    && mkdir -p /data \
    && chown -R arena:arena /data
COPY --from=web /web/dist ./frontend/dist
USER arena
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)" || exit 1
CMD ["python", "-m", "uvicorn", "arena_server.main:app", "--host", "0.0.0.0", "--port", "8000"]

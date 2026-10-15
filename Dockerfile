# syntax=docker/dockerfile:1

FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
COPY web/package.json ./web/package.json
# Optional CA is only for builds behind an HTTPS proxy; Railway needs no secret.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci --no-audit --no-fund
COPY web/ ./web/
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.12.23 AS uv
FROM python:3.12-slim-bookworm AS backend
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca; fi; \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOOP_STATE_DIR=/data/runtime \
    LOOP_DATA_DIR=/data/datasets \
    LOOP_WEB_DIST=/app/web/dist \
    LOOP_WORKER_AUTOSTART=true
COPY --from=backend /app/.venv /app/.venv
COPY --from=frontend /app/web/dist /app/web/dist
COPY configs/ ./configs/
COPY THIRD_PARTY_NOTICES.md ./
# Railway volumes are root-owned. Only /data contains mutable application data.
RUN mkdir -p /data
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/v1/health', timeout=3)"
CMD ["python", "-m", "loop_research.deploy"]

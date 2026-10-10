FROM ghcr.io/astral-sh/uv:0.6.4 AS uv
FROM python:3.12.11-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app
WORKDIR /app
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY shared /app/shared
COPY services/api /app/services/api
COPY data/sources.lock.json /app/data/sources.lock.json
COPY .cloudrun-bundle/data /data
COPY .cloudrun-bundle/model-cache /cache
ENV PATH="/app/.venv/bin:$PATH" VERTEX_AUTH_MODE=metadata QDRANT_MODE=bundled DATA_DIR=/data MODEL_CACHE=/cache
EXPOSE 8080
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM ghcr.io/astral-sh/uv:0.6.4 AS uv
FROM python:3.12.11-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app
WORKDIR /app
COPY services/chunk/pyproject.toml services/chunk/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY shared /app/shared
COPY services/chunk /app/services/chunk
COPY data/sources.lock.json /app/data/sources.lock.json
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "services/chunk/main.py"]

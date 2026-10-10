FROM ghcr.io/astral-sh/uv:0.6.4 AS uv
FROM python:3.12.11-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app
WORKDIR /app
COPY services/index/pyproject.toml services/index/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY shared /app/shared
COPY services/index /app/services/index
COPY data/sources.lock.json /app/data/sources.lock.json
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "services/index/main.py"]

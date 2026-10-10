FROM ghcr.io/astral-sh/uv:0.6.4 AS uv
FROM python:3.12.11-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONPATH=/app
WORKDIR /app
COPY services/web/pyproject.toml services/web/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY shared /app/shared
COPY services/web /app/services/web
COPY data/sources.lock.json /app/data/sources.lock.json
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8080
CMD ["uvicorn", "services.web.main:app", "--host", "0.0.0.0", "--port", "8080"]

FROM python:3.12.15-slim-bookworm AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Primero las dependencias para aprovechar la caché de capas.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --group api --group db

COPY backend/app ./app
COPY infra/migraciones ./infra/migraciones
COPY infra/seed ./infra/seed
RUN uv sync --frozen --no-dev --group api --group db

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --no-create-home app \
    && chown -R app:app /app

USER app

EXPOSE 8080

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

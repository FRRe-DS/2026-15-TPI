# syntax=docker/dockerfile:1

# uv con versión fija para instalaciones reproducibles.
FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Usuario sin privilegios para ejecutar la API.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app/backend

COPY --from=uv /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./

# Solo dependencias de ejecución: API (FastAPI, Uvicorn, PyJWT) y base de datos.
RUN uv sync --frozen --no-dev --group api --group db

COPY backend/app ./app
COPY infra/migraciones /app/infra/migraciones
COPY infra/seed /app/infra/seed

ENV PATH="/app/backend/.venv/bin:$PATH"

USER app

EXPOSE 8080

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

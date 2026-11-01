# Validación: Verificación de integración real de M3

## Requisitos

- Docker Engine + Docker Compose.
- Python 3.12 y `uv`.
- Git con el repositorio y contratos bilaterales acordados disponibles.

Las imágenes de Compose y Testcontainers se especifican con versiones fijas. No reemplazar por `latest`.

## Ejecutar suite de integración

Desde PowerShell en la raíz:

```powershell
Set-Location backend
uv sync --frozen --all-groups
uv run pytest tests/integracion tests/contrato -v
```

Las pruebas con Testcontainers levantan PostgreSQL y RabbitMQ efímeros. En CI Docker ausente, un test obligatorio omitido o un contrato incompleto debe ser un fallo, no un skip silencioso.

## Ejecutar flujo E2E del Compose

Completar `infra/.env` a partir de `infra/.env.example` usando solo credenciales efímeras de prueba. No versionar `.env`.

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build --wait -d
Set-Location backend
uv run pytest tests/e2e -v
Set-Location ..
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

El E2E solicita tokens a Keycloak local del Compose, realiza las altas y aprobaciones contra la API HTTP, valida historial y evento, reinicia la API sin reiniciar PostgreSQL y vuelve a leer los registros.

## Ejecución CI

Un único job de integración ejecuta ambas secciones: crea configuración efímera sin secretos de usuario, inicia Compose, ejecuta toda la suite requerida y reporta cobertura; la limpieza de contenedores/volúmenes corre siempre al finalizar el job.

## Resultados esperados

- Flujo autorizado completo: conductor y vehículo aprobados; historial consistente; token de conductor no autoriza acciones de operador.
- Dos solicitudes simultáneas con el mismo DNI: una respuesta `201`, otra `409 DNI_DUPLICADO`, una sola fila en PostgreSQL.
- Rollback: sin evento visible en la cola.
- RabbitMQ temporalmente fuera de servicio: el outbox conserva el evento y el publicador lo entrega tras recuperación; los duplicados conservan `event_id`.
- Reinicio de API: registros siguen consultables desde la API y presentes en PostgreSQL.
- Los dobles de M1/M4/M5/M6 aceptan solo operaciones conformes con los contratos bilaterales versionados.

Si una frontera contractual no tiene documento aprobado y no vacío, detener la validación de esa frontera y resolverla con el módulo propietario antes de implementar su doble.

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

Las pruebas con Testcontainers levantan PostgreSQL efímero. En CI Docker ausente, un test obligatorio omitido o un contrato incompleto debe ser un fallo, no un skip silencioso. Las pruebas de RabbitMQ quedan bloqueadas hasta la decisión sobre FR-007/FR-013.

## Ejecutar pruebas de contrato de las 17 operaciones

```powershell
Set-Location backend
uv run pytest tests/contrato/test_openapi_ejemplos.py -v
```

El test debe validar las 17 operaciones de `OPERACIONES_EN_ALCANCE`, el `410` y los códigos nuevos de `CODIGOS_POR_ESTADO`, y las respuestas reales de los 7 endpoints contra `docs/contract/openapi.yaml` con `openapi-core`. Si la copia local del YAML todavía no está en 1.2.0 o el backend de la Iteración 2 no está integrado, la prueba debe fallar; no se relaja el esquema para obtener verde.

## Ejecutar pruebas de los 7 endpoints de la Iteración 2

Requiere la migración `0002` y el backend de la Iteración 2 integrados.

```powershell
Set-Location backend
uv run pytest tests/integracion/estado tests/integracion/solicitudes tests/integracion/concurrencia tests/api/test_roles_servicio.py -v
```

Los tests crean datos propios, usan PostgreSQL real y tokens firmados para los roles `operador`, `conductor` y `servicio` (helper equivalente a `headers_conductor_de`/`headers_operador`). No se ejecutan contra `dev` mientras existan `conectado` y `disponible` en lugar de `estado`.

## Ejecutar cobertura

```powershell
Set-Location backend
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

`70 %` es el valor propuesto para la Iteración 2. El umbral vigente en `ci.yml` es `65 %` hasta que se acuerde el cambio; no se baja el vigente.

## Ejecutar flujo E2E del Compose

Copiar `.env.example` a `.env` en la raíz y completarlo usando solo credenciales efímeras de prueba. No versionar `.env`.

```powershell
Copy-Item .env.example .env
docker compose --env-file .env -f docker-compose.yml up --build --wait -d
Set-Location backend
uv run pytest tests/e2e -v
Set-Location ..
docker compose --env-file .env -f docker-compose.yml down
```

El E2E solicita tokens a Keycloak local del Compose, realiza las altas y aprobaciones contra la API HTTP, valida el historial, reinicia la API sin reiniciar PostgreSQL y vuelve a leer los registros. La validación de eventos en RabbitMQ queda bloqueada hasta la decisión sobre FR-007/FR-013; la persistencia se verifica sin broker.

## Ejecución CI

Los jobs `contrato`, `test` y `entorno` de `ci.yml` ejecutan las secciones de contrato, integración y E2E: crea configuración efímera sin secretos de usuario, inicia Compose, ejecuta toda la suite requerida y reporta cobertura con el umbral acordado; la limpieza de contenedores/volúmenes corre siempre al finalizar el job. Las pruebas nuevas de contrato e integración de los 7 endpoints deben estar dentro de este job.

## Resultados esperados

- Flujo autorizado completo: conductor y vehículo aprobados; historial consistente; token de conductor no autoriza acciones de operador.
- Dos solicitudes simultáneas con el mismo DNI: una respuesta `201`, otra `409 DNI_DUPLICADO`, una sola fila en PostgreSQL.
- Contrato: 17 operaciones en `OPERACIONES_EN_ALCANCE`, `410 SOLICITUD_VENCIDA` en `CODIGOS_POR_ESTADO` y respuestas reales de los 7 endpoints validadas con `openapi-core`.
- Estado: `DISPONIBLE` sin aprobación da `422 CONDUCTOR_NO_HABILITADO`; desde `DESCONECTADO` y cumpliendo queda `DISPONIBLE`; `OCUPADO` da `400`; quitar el vehículo activo baja a `CONECTADO`.
- Solicitudes: aceptar una vigente deja `OCUPADO`; vencida da `410 SOLICITUD_VENCIDA`; segunda respuesta da `409 SOLICITUD_YA_RESPONDIDA`; dos carreras simultáneas no pierden cambios.
- Promedio: coincide con el seed; sin calificaciones es `null` y `0`; ningún endpoint lo modifica.
- Ubicación: sin datos responde `200` con tres `null`, nunca `0,0`; el paso de `DESCONECTADO` a otro estado asigna la ubicación simulada fija.
- Rol `servicio`: solo lectura; cualquier operación de escritura con ese token responde `403`; el helper de token `servicio` se usa en las pruebas.
- Reinicio de API: registros siguen consultables desde la API y presentes en PostgreSQL.
- Rollback/eventos: quedan bloqueados con PR 3 hasta la decisión sobre FR-007/FR-013; no se ejecuta una prueba de RabbitMQ como si estuviera aprobada.
- Los dobles de M1/M4/M5 aceptan solo operaciones conformes con los contratos bilaterales versionados y se limitan a lo que M3 expone. M6 no forma parte de esta suite: sus operaciones se retiraron del contrato de M3 y no hay clientes HTTP salientes.

Si una frontera contractual no tiene documento aprobado y no vacío, detener la validación de esa frontera y resolverla con el módulo propietario antes de implementar su doble.

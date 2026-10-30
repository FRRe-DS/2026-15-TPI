# Guía de Arranque y Validación: Iteración 2

Complementa y actualiza la [guía de Iteración 1](../iteracion1/quickstart.md). Los pasos 1–3 son idénticos; los pasos 4–6 son nuevos.

## Requisitos previos

- Docker con Compose
- Python 3.12 y [uv](https://docs.astral.sh/uv/)
- Node 24 LTS y npm

## 1. Levantar el stack

```bash
cp infra/.env.example infra/.env
# Completar todos los valores vacíos de infra/.env.
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build
```

Resultado esperado: API en `http://localhost:8080/api/v1`, Keycloak en `http://localhost:8081`, migraciones y seed completados.

## 2. Verificar salud

```bash
curl http://localhost:8080/salud
```

Resultado esperado: `{"status": "ok"}` (o equivalente del contrato).

## 3. Obtener un token y listar conductores

```bash
# Token de operador
TOKEN=$(curl -s -X POST "http://localhost:8081/realms/m3/protocol/openid-connect/token" \
  -d "grant_type=password" \
  -d "client_id=$KEYCLOAK_CLIENT_ID" \
  -d "client_secret=$KEYCLOAK_CLIENT_SECRET" \
  -d "username=$TEST_USER" \
  -d "password=$TEST_PASSWORD" | jq -r '.access_token')

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/conductores | jq
```

Resultado esperado: lista con conductores del seed, incluyendo algunos con `latitud`/`longitud` no nulos.

## 4. Verificar los nuevos endpoints

```bash
# Historial de habilitación de un vehículo (reemplazar IDs)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/conductores/1/vehiculos/1/habilitacion | jq

# PATCH de conexión / disponibilidad (conductor sobre sí mismo)
TOKEN_CONDUCTOR=$(# obtener token con usuario conductor.m3)
curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN_CONDUCTOR" \
  -H "Content-Type: application/json" \
  -d '{"conectado": true, "disponible": true}' \
  http://localhost:8080/api/v1/conductores/2 | jq

# Listar documentos del conductor
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/v1/conductores/1/documentacion | jq

# Filtros nuevos en el listado
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/api/v1/conductores?tipo_servicio=PASAJEROS" | jq
```

## 5. Verificar control de acceso por conductor

```bash
# El conductor.m3 (id=2) intenta acceder a los vehículos del conductor id=1 → debe dar 403
TOKEN_C=$(# token de conductor.m3)
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN_C" \
  http://localhost:8080/api/v1/conductores/1/vehiculos
# Resultado esperado: 403
```

## 6. Pantalla del frontend con integración E2E

```bash
cd frontend
npm ci
cp .env.example .env.local
# Completar .env.local con los mismos valores de infra/.env:
#   API_URL=http://localhost:8080/api/v1
#   KEYCLOAK_URL=http://localhost:8081
#   KEYCLOAK_REALM=m3
#   KEYCLOAK_CLIENT_ID=<valor de infra/.env>
#   KEYCLOAK_CLIENT_SECRET=<valor de infra/.env>
#   TEST_USER=<valor de infra/.env>
#   TEST_PASSWORD=<valor de infra/.env>
npm run dev
```

Abrir `http://localhost:3000`. Resultado esperado:
- Se listan los conductores del seed con nombre, apellido, DNI y badge de color por estado de habilitación.
- Badge verde para `APROBADA`, amarillo para `PENDIENTE`/`OBSERVADA`, rojo para `SUSPENDIDA`/`RECHAZADA`.
- Con la API apagada (`docker compose stop api`) y recargando: mensaje de error claro sin pantalla en blanco.

## 7. Pruebas

```bash
cd backend
uv sync --frozen --all-groups
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov --cov-fail-under=70

cd ../frontend
npm run test
npm run lint
npm run build
```

Resultado esperado: pruebas en verde, cobertura ≥ 70 %, lint limpio, build exitoso.

## Referencias

- Contrato: `docs/contract/openapi.yaml`
- Modelo de datos Iteración 2: [data-model.md](./data-model.md)
- Modelo de datos Iteración 1: [../iteracion1/data-model.md](../iteracion1/data-model.md)
- Contrato de acceso: [contracts/acceso-conductor.md](./contracts/acceso-conductor.md)

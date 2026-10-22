# Guía de Arranque y Validación: Iteración 1

Cómo comprobar que la iteración funciona de punta a punta. Los comandos se vuelven ciertos a medida que cada stack entrega su parte.

## Requisitos previos

- Docker con Compose
- Python 3.12 y [uv](https://docs.astral.sh/uv/)
- Node 24 LTS y npm (para la pantalla)

## 1. Levantar API, base de datos e identidad

```bash
cp infra/.env.example infra/.env
docker compose -f infra/docker-compose.yml up --build
```

Resultado esperado: PostgreSQL, Keycloak y la API en marcha; las migraciones y el seed terminaron con éxito. API en `http://localhost:8080/api/v1`, Keycloak en `http://localhost:8081`.

## 2. Obtener un token y consultar

Con las credenciales de prueba definidas en `infra/.env`:

```bash
curl -s -X POST "http://localhost:8081/realms/m3/protocol/openid-connect/token" \
  -d "grant_type=password" -d "client_id=$CLIENTE" -d "client_secret=$SECRETO" \
  -d "username=$USUARIO_OPERADOR" -d "password=$CLAVE_OPERADOR"
```

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/v1/conductores
```

Resultado esperado: lista con los conductores de prueba. Sin el encabezado: `401`.

## 3. Flujo principal

Con un token de operador: crear conductor → cargar licencia vigente → aprobar → registrar vehículo → aprobar vehículo → consultar habilitación. Ver [spec.md](./spec.md) (historias 1 a 4) para los resultados esperados.

## 4. Pruebas

```bash
cd backend
uv sync
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov --cov-fail-under=65
```

Resultado esperado: pruebas en verde y cobertura mínima cumplida. Las de integración requieren Docker en marcha.

## 5. Pantalla

```bash
cd frontend
npm install
npm run dev
```

Resultado esperado: la pantalla muestra el listado de conductores de prueba; con la API apagada muestra un mensaje de error claro.

## Referencias

- Contrato: `docs/contract/openapi.yaml`
- Modelo de datos: [data-model.md](./data-model.md)
- Contratos internos: [contracts/](./contracts/)

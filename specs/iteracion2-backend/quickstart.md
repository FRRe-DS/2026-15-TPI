# Guía de Validación: Iteración 2 — Backend

Cómo comprobar que los endpoints nuevos funcionan, con un token de cada rol. Los comandos se vuelven ciertos a medida que se integran las PRs de [plan.md](./plan.md). El arranque del entorno (Compose, Keycloak, migraciones) es el de la [Iteración 1](../iteracion1/quickstart.md).

## Requisitos previos

- Los de la Iteración 1: Docker con Compose, Python 3.12 y [uv](https://docs.astral.sh/uv/).
- Para probar contra el entorno real: la migración, el seed, el rol `servicio` y el claim `id_conductor` del grupo de Datos y seguridad (ver [data-model.md](./data-model.md) y [contracts/token-jwt.md](./contracts/token-jwt.md)).

## 1. Pruebas automáticas (no necesitan Keycloak)

```bash
cd backend
uv sync --frozen --all-groups
uv run ruff check . && uv run ruff format --check .
uv run pytest tests/unitarios tests/api --cov --cov-fail-under=65
```

Resultado esperado: todo en verde. Los tests de API firman sus propios tokens con los tres roles; no hay que levantar nada.

Los repositorios SQL se prueban contra PostgreSQL real (requiere Docker en marcha):

```bash
uv run pytest tests/integracion/repositorios
```

## 2. Obtener un token de cada rol (entorno real)

Como en la Iteración 1, con las credenciales de `infra/.env`:

```bash
curl -s -X POST "http://localhost:8081/realms/m3/protocol/openid-connect/token" \
  -d "grant_type=password" -d "client_id=$CLIENTE" -d "client_secret=$SECRETO" \
  -d "username=$USUARIO" -d "password=$CLAVE"
```

| Rol | Cómo obtenerlo | Qué trae el token |
|---|---|---|
| operador | usuario operador de prueba | `id_operador` |
| conductor | usuario conductor de prueba | `id_conductor`, igual al de un conductor del seed |
| servicio | cuenta técnica de M4 | solo el rol |

Guardar cada token en `TOKEN_OPERADOR`, `TOKEN_CONDUCTOR` y `TOKEN_SERVICIO`. En lo que sigue, `ID` es el conductor del usuario conductor de prueba y `OTRO` es el de otro conductor del seed.

## 3. Estado y ubicación

```bash
# El conductor consulta y actualiza lo suyo
curl -s -H "Authorization: Bearer $TOKEN_CONDUCTOR" http://localhost:8080/api/v1/conductores/$ID/estado
curl -s -X PATCH -H "Authorization: Bearer $TOKEN_CONDUCTOR" -H "Content-Type: application/json" \
  -d '{"estado": "DISPONIBLE"}' http://localhost:8080/api/v1/conductores/$ID/estado
curl -s -H "Authorization: Bearer $TOKEN_SERVICIO" http://localhost:8080/api/v1/conductores/$ID/ubicacion
```

Resultado esperado:
- El estado devuelve `estado`, `id_vehiculo_activo` y `actualizado`, sin coordenadas.
- El `PATCH` deja `DISPONIBLE` solo si el conductor está `APROBADA` y su vehículo activo también; si no, `422` `CONDUCTOR_NO_HABILITADO`. Pedir `DISPONIBLE` estando `DESCONECTADO` lo conecta.
- Pedir `{"estado": "OCUPADO"}` da `400`: ese valor lo asigna M3 al aceptar una solicitud.
- Un conductor sin ubicación que pasa de `DESCONECTADO` a otro estado recibe la ubicación simulada fija (`-27.4511, -58.9867` por defecto).
- Con el token de servicio, `PATCH .../estado` da `403`.

## 4. Un conductor no ve lo de otro

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_CONDUCTOR" \
  http://localhost:8080/api/v1/conductores/$OTRO/estado
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_CONDUCTOR" \
  http://localhost:8080/api/v1/conductores
```

Resultado esperado: `403` en ambos (`ACCESO_PROHIBIDO` el primero y `SIN_PERMISOS` el segundo). Con `TOKEN_OPERADOR` y con `TOKEN_SERVICIO`, ambos responden `200`.

## 5. Solicitudes

```bash
curl -s -H "Authorization: Bearer $TOKEN_CONDUCTOR" "http://localhost:8080/api/v1/conductores/$ID/solicitudes?estado=PENDIENTE"
curl -s -X POST -H "Authorization: Bearer $TOKEN_CONDUCTOR" -H "Content-Type: application/json" \
  -d '{"respuesta": "ACEPTADO", "hora_rta": "2026-11-02T01:40:00Z"}' \
  http://localhost:8080/api/v1/solicitudes/$ID_SOLICITUD
```

Resultado esperado:
- La lista trae solo las solicitudes del conductor; una `PENDIENTE` ya vencida figura como `VENCIDA`.
- Aceptar una vigente da `200` (la respuesta trae `id_viaje`, como el contrato) y deja al conductor `OCUPADO` (si estaba `CONECTADO` o `DISPONIBLE` y cumple las reglas; si no, `422`); rechazar no cambia su estado.
- Para volver a `DISPONIBLE`, el conductor lo pide con `PATCH .../estado`.
- Una vencida da `410` `SOLICITUD_VENCIDA` y una ya respondida, `409` `SOLICITUD_YA_RESPONDIDA`.
- La solicitud de otro conductor da `403` `ACCESO_PROHIBIDO`; una inexistente, `404`.

Las solicitudes de prueba las carga el seed: el backend no las crea.

## 6. Vehículo

```bash
curl -s -H "Authorization: Bearer $TOKEN_CONDUCTOR" http://localhost:8080/api/v1/conductores/$ID/vehiculos/$ID_VEHICULO/tipos-servicio
curl -s -X POST -H "Authorization: Bearer $TOKEN_CONDUCTOR" -H "Content-Type: application/json" \
  -d '{"tipo": "SEGURO", "numero": "S-123", "fecha_emision": "2026-01-01", "fecha_vencimiento": "2027-01-01", "url_archivo": "https://ejemplo.test/seguro.pdf"}' \
  http://localhost:8080/api/v1/conductores/$ID/vehiculos/$ID_VEHICULO/documentacion
```

Resultado esperado:
- Los tipos de servicio salen con su `habilitado`: verdadero si el vehículo está aprobado.
- El documento se crea con `201` y estado `VIGENTE`; con vencimiento anterior a la emisión, `422`.
- `GET .../vehiculos/$ID_VEHICULO` incluye el documento en `documentos`.

## 7. Paridad con el contrato

```bash
cd backend
uv run pytest tests/api/test_paridad_rutas.py tests/contrato -q
```

Resultado esperado: la API genera las 17 operaciones del contrato 1.2.0 con sus `operationId`.

## Advertencias

- M4 y M6 no escriben en M3: el contrato 1.2.0 no tiene operaciones de entrada. Quién marca `OCUPADO` más allá de la aceptación de una solicitud, y de dónde salen los puntajes, queda por acordar con ellos.
- Los cambios de estado de un mismo conductor se serializan: un cambio de estado y la aceptación de una solicitud simultáneos se aplican uno tras otro, sin perder ninguno.

## Recorrido contra el entorno real (2026-11-08)

Se levantó Compose desde `dev` (con L9, L10, la migración 0002 y el seed) y se recorrieron las secciones 3 a 6 con los tokens de operador y de conductor (`conductor.m3`, `id_conductor` 1). Todo respondió como dice esta guía, con estas diferencias:

- **No se pudo comprobar con el rol `servicio` en vivo.** El `infra/.env` local es anterior a la cuenta técnica de M4 y no tiene `M3_SERVICIO_USERNAME` ni `M3_SERVICIO_PASSWORD`; hay que sumarlos desde `.env.example` y recrear Keycloak (el realm solo se importa con el volumen vacío). Los permisos del servicio quedan cubiertos por las pruebas de integración (`test_lectura_m4`) y de API.
- El seed trae 7 conductores, 5 vehículos, 3 documentos de vehículo y 5 solicitudes. El conductor 1 tiene una solicitud `PENDIENTE` y otra `VENCIDA`: aceptar la primera da `200` y lo deja `OCUPADO`, reaceptarla da `409`, y la vencida da `410`.
- `GET /conductores?disponible=true` responde `400` con el aviso de que se reemplazó por `estado`.
- Los mensajes de error salen con tildes en UTF-8; en la consola de Windows hay que fijar la codificación para leerlos bien.

## Referencias

- Contrato: `docs/contract/openapi.yaml`
- Modelo de datos: [data-model.md](./data-model.md)
- Decisiones: [research.md](./research.md)
- Contratos internos: [contracts/](./contracts/)

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
| servicio | cuenta técnica de M4 o de M6 | solo el rol |

Guardar cada token en `TOKEN_OPERADOR`, `TOKEN_CONDUCTOR` y `TOKEN_SERVICIO`. En lo que sigue, `ID` es el conductor del usuario conductor de prueba y `OTRO` es el de otro conductor del seed.

## 3. Estado y ubicación

```bash
# El conductor consulta y actualiza lo suyo
curl -s -H "Authorization: Bearer $TOKEN_CONDUCTOR" http://localhost:8080/api/v1/conductores/$ID/estado
curl -s -X PATCH -H "Authorization: Bearer $TOKEN_CONDUCTOR" -H "Content-Type: application/json" \
  -d '{"conectado": true, "disponible": true}' http://localhost:8080/api/v1/conductores/$ID/estado
curl -s -H "Authorization: Bearer $TOKEN_SERVICIO" http://localhost:8080/api/v1/conductores/$ID/ubicacion
```

Resultado esperado:
- El estado devuelve `conectado`, `disponible`, `id_vehiculo_activo` y `actualizado`, sin coordenadas.
- El `PATCH` deja disponible solo si el conductor está `APROBADA` y su vehículo activo también; si no, `422` `CONDUCTOR_NO_HABILITADO`.
- Un conductor sin ubicación que se conecta recibe la ubicación simulada fija (`-27.4511, -58.9867` por defecto).
- Con el token de servicio, `PATCH .../estado` da `403`.

## 4. Un conductor no ve lo de otro

```bash
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_CONDUCTOR" \
  http://localhost:8080/api/v1/conductores/$OTRO/estado
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN_CONDUCTOR" \
  http://localhost:8080/api/v1/conductores
```

Resultado esperado: `403` en ambos (`ACCESO_PROHIBIDO` el primero y `SIN_PERMISOS` el segundo). Con `TOKEN_OPERADOR` y con `TOKEN_SERVICIO`, ambos responden `200`.

## 5. Integración con M4 (solo rol servicio)

```bash
curl -s -X PATCH -H "Authorization: Bearer $TOKEN_SERVICIO" -H "Content-Type: application/json" \
  -d '{"disponible": false, "motivo": "OCUPADO", "actualizado": "2026-11-02T01:35:00Z"}' \
  http://localhost:8080/api/v1/integraciones/m4/conductores/$ID/disponibilidad
```

Resultado esperado:
- `200` con el estado; el conductor queda no disponible.
- Repetir el mismo pedido da el mismo resultado.
- Con un `actualizado` anterior al último cambio, `200` con el estado vigente y sin cambios.
- `disponible: true` para un conductor desconectado o no aprobado da `422`.
- Con `TOKEN_CONDUCTOR` o `TOKEN_OPERADOR`, `403` ("Se requiere el rol servicio").

## 6. Integración con M6 (solo rol servicio)

```bash
curl -s -X POST -H "Authorization: Bearer $TOKEN_SERVICIO" -H "Content-Type: application/json" \
  -d '{"id_conductor": '$ID', "estado": "FINALIZADO", "destino": {"latitud": -27.4698, "longitud": -58.8306}, "fecha_finalizacion": "2026-11-02T02:10:00Z", "puntaje_conductor": 5}' \
  http://localhost:8080/api/v1/integraciones/m6/viajes/5521/finalizacion
```

Resultado esperado:
- `200` con `procesado`, `ubicacion_actualizada` y `puntaje_registrado` en verdadero.
- `GET /conductores/$ID` ahora muestra `puntaje_promedio` y `cantidad_calificaciones` actualizados.
- Repetir el mismo pedido da `200` con la misma respuesta y sin cambiar el puntaje.
- Mismo `id_viaje` con datos distintos da `409` `VIAJE_EN_CONFLICTO`.
- Un puntaje de `6` o un `estado` distinto de `FINALIZADO` da `400`.

## 7. Solicitudes

```bash
curl -s -H "Authorization: Bearer $TOKEN_CONDUCTOR" "http://localhost:8080/api/v1/conductores/$ID/solicitudes?estado=PENDIENTE"
curl -s -X POST -H "Authorization: Bearer $TOKEN_CONDUCTOR" -H "Content-Type: application/json" \
  -d '{"respuesta": "ACEPTADO", "hora_rta": "2026-11-02T01:40:00Z"}' \
  http://localhost:8080/api/v1/solicitudes/$ID_SOLICITUD
```

Resultado esperado:
- La lista trae solo las solicitudes del conductor; una `PENDIENTE` ya vencida figura como `VENCIDA`.
- Aceptar una vigente da `200` y deja al conductor no disponible; rechazar no cambia su disponibilidad.
- Una vencida da `410` `SOLICITUD_VENCIDA` y una ya respondida, `409` `SOLICITUD_YA_RESPONDIDA`.
- La solicitud de otro conductor da `403` `ACCESO_PROHIBIDO`; una inexistente, `404`.

Las solicitudes de prueba las carga el seed: el backend no las crea.

## 8. Vehículo

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

## 9. Paridad con el contrato

```bash
cd backend
uv run pytest tests/api/test_paridad_rutas.py tests/contrato -q
```

Resultado esperado: la API genera las 19 operaciones del contrato 1.1.0 con sus `operationId`.

## Advertencias

- El reloj de M4 debe estar en UTC y sincronizado: un `actualizado` adelantado puede ganarle a cambios posteriores del conductor ([research.md](./research.md), decisión 3).
- Los cambios de estado de un mismo conductor se serializan: dos pedidos simultáneos se aplican uno tras otro, sin perder ninguno.

## Referencias

- Contrato: `docs/contract/openapi.yaml`
- Modelo de datos: [data-model.md](./data-model.md)
- Decisiones: [research.md](./research.md)
- Contratos internos: [contracts/](./contracts/)

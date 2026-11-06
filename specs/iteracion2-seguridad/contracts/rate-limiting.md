# Contrato interno: rate limiting de M3

Contrato entre infraestructura de plataforma, la API y Testing. No agrega rutas y no altera la matriz de acceso del [contrato JWT](../../iteracion2-backend/contracts/token-jwt.md).

## Alcance

- Aplicar el limitador a solicitudes de la API protegida bajo `/api/v1`.
- Excluir `GET /salud`, que usa Docker Compose y CI.
- Clasificar cada solicitud solo después de comprobar el JWT: usuario autenticado por el par `(iss, sub)` verificado; sin JWT válido por dirección IP del peer ASGI. `sub` debe estar presente y ser texto no vacío; un token firmado sin una identidad estable se rechaza y usa la cuota por IP.
- Un proxy reenviado solo es fuente de IP si el peer inmediato está configurado explícitamente como proxy confiable.

## Política inicial

| Clase | Identificador | Límite inicial | Ventana |
|---|---|---:|---:|
| Sin JWT válido | IP del peer ASGI | 60 solicitudes | 60 segundos deslizantes |
| JWT válido | Claim `sub` verificado | 120 solicitudes | 60 segundos deslizantes |

Se configuran mediante `RATE_LIMIT_ANON_REQUESTS`, `RATE_LIMIT_AUTH_REQUESTS` y `RATE_LIMIT_WINDOW_SECONDS`. El almacén compartido se configura mediante `REDIS_URL`; la contraseña se suministra por `REDIS_PASSWORD`, nunca se versiona ni se registra. Redis no publica puerto al host en Compose.

## Respuestas de limitación

Al alcanzar la cuota:

- Estado HTTP: `429 Too Many Requests`.
- Encabezado: `Retry-After`, segundos enteros hasta la próxima solicitud permitida.
- Cuerpo: `{"codigo": "LIMITE_DE_SOLICITUDES", "mensaje": "Se alcanzó el límite de solicitudes; reintente más tarde."}`.
- No almacenar en caché la respuesta de rate limiting.

Si Redis no responde o vence el timeout:

- Estado HTTP: `503 Service Unavailable` (fail-closed).
- Cuerpo: `{"codigo": "SERVICIO_TEMPORALMENTE_NO_DISPONIBLE", "mensaje": "El servicio no está disponible temporalmente."}`.
- No devolver detalles de host, conexión, query ni credenciales; registrar el error operativo sin incluir tokens o identificadores completos.

La respuesta 429 puede incluir `Retry-After`; la respuesta 503 no promete un tiempo de recuperación. Testing coordina su inclusión como respuestas comunes en OpenAPI y valida el formato estable.

## Requisitos para implementación y pruebas

- Los incrementos, limpieza de eventos, conteo y TTL son atómicos entre varias instancias.
- No confiar en claims de JWT antes de verificarlo ni en encabezados de IP reenviados por clientes.
- No registrar ni persistir JWT, cuerpo de requests o identidad sin necesidad.
- Probar límite exacto, exceso, `Retry-After`, expiración, separación de identidades, concurrencia, exclusión de `/salud` y falla de Redis.
- Las pruebas de unidad/API sustituyen Redis por un fake inyectado; integración/Compose valida un Redis real.
- Los tests de integración incluyen requests concurrentes con Redis real; los tests de API usan el lifespan de FastAPI y fixtures JWT con `iss` y `sub`.

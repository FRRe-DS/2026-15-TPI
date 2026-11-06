# Modelo de datos: rate limiting de la API

Este diseño describe el estado efímero almacenado en Redis para el rate limiting. No agrega tablas ni modifica el esquema PostgreSQL de M3.

Los cambios persistentes de Iteración 2 (`conductor`, `solicitud` y `vehiculo_documento`) siguen el [modelo acordado con Backend](../iteracion2-backend/data-model.md).

## Configuración

| Variable | Tipo | Valor inicial | Regla |
|---|---|---:|---|
| `REDIS_URL` | URL Redis | `redis://default:${REDIS_PASSWORD}@redis:6379/0` en Compose | Requerida por la API; la contraseña se inyecta por entorno |
| `REDIS_PASSWORD` | secreto | Generado fuera del repositorio | Obligatorio para Redis y la API; no se registra |
| `RATE_LIMIT_ANON_REQUESTS` | entero | `60` | Mayor que cero |
| `RATE_LIMIT_AUTH_REQUESTS` | entero | `120` | Mayor que cero |
| `RATE_LIMIT_WINDOW_SECONDS` | entero | `60` | Mayor que cero |

Los valores se pueden sustituir por entorno. Redis requiere autenticación, es interno a la red Compose y no se publica al host por defecto. Los contadores son temporales; no requieren volumen ni recuperación tras reinicio.

## Cuota de solicitudes

Concepto lógico, no entidad de negocio:

| Campo | Descripción |
|---|---|
| `scope` | `anon` para requests sin JWT válido; `user` para JWT validado |
| `identity` | IP del peer ASGI para `anon`; claim `sub` del payload verificado para `user` |
| `limit` | `60` para `anon`; `120` para `user`, configurable |
| `window` | Ventana deslizante de `60` segundos, configurable |
| `events` | Sorted set Redis con timestamp de Redis y miembro único por cada solicitud permitida |
| `expires_at` | TTL de la clave; vuelve a fijarse al agregar un evento y no supera la ventana de solicitudes activas |

### Clave y contenido Redis

- Prefijo: `m3:rate-limit:v1`.
- Clave lógica: `m3:rate-limit:v1:<scope>:<identity>`.
- El contenido es un sorted set; el score es el timestamp en milisegundos obtenido por `TIME` en Redis y el miembro es único por solicitud.
- No guardar JWT, cuerpos, nombres, datos personales ni encabezados. No escribir claves o identidades en logs.
- Un script Lua ejecuta atómicamente: obtener hora; retirar eventos anteriores a la ventana; consultar cantidad; si el límite ya se alcanzó, devolver denegación y espera; de lo contrario, agregar el evento y aplicar TTL.
- Un request denegado no agrega un evento ni reinicia el TTL.

### Identidad del cliente

1. Verificar el JWT según las reglas existentes (firma/JWKS, issuer y expiración) antes de leer `sub`.
2. Si el JWT es válido y tiene `iss` y `sub` como texto no vacío, usar ambos como identidad autenticada. Si `sub` falta o no es válido, aplicar el límite por IP y rechazar la autenticación; no crear una cuota autenticada sin identidad estable.
3. Si no hay JWT o no se valida, usar la dirección `request.client.host`.
4. No aceptar `X-Forwarded-For` desde cualquier cliente. Solo se puede usar si el peer inmediato está en una lista explícita de proxies confiables.

## Transiciones y respuestas

| Estado previo de la cuota | Solicitud | Estado Redis | Respuesta |
|---|---|---|---|
| Menos de `limit` eventos activos | Solicitud recibida | Agrega un evento; TTL de ventana | Continúa al chequeo de autenticación/endpoint |
| `limit` eventos activos | Nueva solicitud | No agrega evento | `429 LIMITE_DE_SOLICITUDES` con encabezado `Retry-After` |
| Redis no disponible o timeout | Cualquiera que requiere cuota | No se asume cuota disponible | `503 SERVICIO_TEMPORALMENTE_NO_DISPONIBLE` |
| Cualquier estado | `GET /salud` | No consulta ni modifica cuota | Respuesta normal de salud |

`Retry-After` es el entero en segundos redondeado hacia arriba hasta que el evento activo más antiguo deje de consumir cuota. Al expirar la ventana, los eventos dejan de contar y el cliente puede volver a solicitar.

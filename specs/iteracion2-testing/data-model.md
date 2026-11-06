# Modelo de datos: Verificación de integración real de M3

**Base**: PostgreSQL de M3. Los cambios de esquema se realizan con una migración Alembic versionada.

> **Alcance**: la migración `0002` de la Iteración 2 es parte del trabajo de verificación. La tabla `outbox_evento` y todo lo relacionado con RabbitMQ quedan **bloqueados** mientras la PR 3 no se desbloquee por la decisión FR-007/FR-013; se documentan solo para el caso de que la cátedra confirme esa publicación en un spec propio de Backend.

## Tabla nueva (condicional): `outbox_evento`

Almacena eventos de dominio que deben publicarse. Se inserta dentro de la misma transacción que el estado e historial M3.

| Campo | Tipo propuesto | Regla |
|---|---|---|
| `event_id` | UUID, PK | Identidad estable en todos los reintentos y entregas duplicadas. |
| `aggregate_type` | texto corto | Tipo de agregado M3, conductor o vehículo. |
| `aggregate_id` | bigint | Identificador propio de M3; no FK para conservar el evento aunque cambie la retención del agregado. |
| `event_type` | texto corto | Nombre establecido por el contrato de eventos acordado. |
| `payload` | JSONB | Envelope y datos del evento según contrato, no una copia arbitraria de tablas. |
| `occurred_at` | timestamptz | Instante del cambio de dominio. |
| `created_at` | timestamptz | Instante de inserción en outbox. |
| `available_at` | timestamptz | Próxima fecha de intento; inicialmente igual a `created_at`. |
| `attempts` | integer | Conteo de entregas fallidas, no negativo. |
| `lease_until` | timestamptz nullable | Vencimiento del claim temporal del publicador para recuperar tras su caída. |
| `published_at` | timestamptz nullable | Solo se completa tras confirmación RabbitMQ. Null significa pendiente/reintentable. |
| `last_error` | texto nullable | Diagnóstico sanitizado del intento más reciente; sin credenciales ni payload sensible. |

**Índices y restricciones**:

- Índice para leer mensajes pendientes ordenados por `available_at` y `created_at`, filtrado por `published_at IS NULL`.
- Restricción `CHECK (attempts >= 0)`.
- `event_id` único en toda la vida del registro.
- No guardar estados redundantes: pendiente/publicado se deriva de `published_at`.

**Ciclo de vida**:

1. El caso de uso modifica conductor/vehículo e historial y encola el evento por un puerto de aplicación en una unidad de trabajo SQL.
2. El commit confirma a la vez el estado y la fila outbox. El rollback elimina ambos.
3. El publicador reclama filas pendientes con bloqueo concurrente y lease limitado; no mantiene una transacción SQL abierta durante una operación de red.
4. RabbitMQ recibe un mensaje persistente a un exchange durable. El publicador espera publisher confirm y luego establece `published_at`.
5. En error de conexión, nack o timeout, registra el intento y programa `available_at` con backoff; el servicio HTTP continúa operando.
6. Si el proceso cae después de confirm y antes de marcar la fila, se vuelve a publicar tras vencer el lease. El mismo `event_id` permite deduplicar.

La retención/borrado de filas publicadas no forma parte del comportamiento de negocio; no se purgan eventos en esta feature.

## Cambios de esquema de la Iteración 2 (migración `0002`)

Los cambios de la migración `0002` los aporta el grupo de Datos y seguridad; las pruebas de los 7 endpoints se ejecutan después de integrarla.

- Reemplaza `conectado` y `disponible` por `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`).
- Mantiene `id_vehiculo_activo`, `fecha_ultimo_cambio_estado`, `suma_puntajes` y `cantidad_calificaciones`; `puntaje_promedio` se deriva y no se persiste.
- Agrega `solicitud` (estado, `vence_en`, respuesta y hora de respuesta) y `documento_vehiculo`.
- Mantiene `vehiculo_tipo_servicio.habilitado` sincronizado con la habilitación del vehículo.
- Los tests existentes que usan `conectado`/`disponible` deben migrarse a `estado` al recibir esta migración.

La tabla `outbox_evento` y cualquier publicación de eventos quedan **fuera de alcance mientras PR 3 esté bloqueada** por el conflicto FR-007/FR-013.

## Entidades de verificación (sin tablas permanentes)

- **Registro de prueba**: conductor y vehículo creados con DNI/patente únicos de esa ejecución.
- **Token de prueba**: JWT obtenido de Keycloak real en E2E o emitido por un doble contractual en pruebas de forma de token; nunca persiste en PostgreSQL. Incluye tokens con rol `servicio` firmados para las lecturas de M4 y la matriz de roles.
- **Mensaje capturado** (solo si se desbloquea la publicación): evento recibido por una cola temporal exclusiva de la prueba; desaparece al cerrar la cola.
- **Doble de módulo**: servidor HTTP/JWKS local que valida su solicitud o respuesta contra el artefacto OpenAPI acordado; no accede a las bases ajenas.

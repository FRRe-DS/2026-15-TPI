# Investigación: Verificación de integración real de M3

**Fecha**: 2026-11-01

**Fuentes locales**: `docs/constitucion.md`, `docs/contract/openapi.yaml`, `infra/docker-compose.yml`, `backend/pyproject.toml`, `backend/uv.lock`, `specs/iteracion1/contracts/token-jwt.md`.

**Fuente de contratos del grupo**: [`FRRe-DS/2026-TPI`](https://github.com/FRRe-DS/2026-TPI), commit `69e9481c754063fc054c8d0ecfdec18d71bf48e6`.

## Decisiones

### 1. Outbox transaccional, no publicación desde el handler

**Decisión**: registrar cada evento a publicar en una tabla outbox dentro de la misma unidad de trabajo SQL que modifica el agregado y su historial. Un proceso de despacho independiente enviará los registros pendientes a RabbitMQ. La fila se marca publicada solo después de una confirmación positiva del broker.

**Motivo**: la transacción DB no puede ser atómica con un publish AMQP. Publicar antes del commit puede dejar un mensaje fantasma si la DB revierte; publicar después del commit puede perder el evento si el proceso cae entre ambos pasos. El outbox elimina esas ventanas para la pérdida del lado productor.

**Entrega**: persistencia del mensaje, exchange durable, delivery mode persistente y publisher confirms. Una caída de Rabbit deja el evento pendiente y el worker reintenta. Si el proceso cae luego del confirm pero antes de marcar `published_at`, el evento puede entregarse de nuevo; cada evento tiene un identificador estable y los consumidores deben deduplicar por ese ID.

**Alternativas**:
- Publicar Rabbit directamente desde el caso de uso: rechazada porque no cumple atomicidad con PostgreSQL ni durabilidad durante la caída del broker.
- Ignorar errores de Rabbit y continuar: rechazada porque pierde eventos confirmados.
- Mantener Rabbit dentro de la transacción HTTP: rechazada porque acopla disponibilidad del broker a operaciones M3 y aún no elimina el caso de confirmación/commit.

### 2. Dos puertos con responsabilidades separadas

**Decisión**: el caso de uso escribe a través de un puerto de publicación que se implementa en producción como registro SQL del outbox sobre la sesión activa. El despachador usa otro puerto de mensajería, implementado con un adaptador RabbitMQ.

**Motivo**: conserva la dirección de dependencias de la arquitectura actual; el dominio/caso de uso no importa Pika y la operación con PostgreSQL permanece en la unidad de trabajo. El adaptador Rabbit no se ejecuta en el hilo del endpoint.

### 3. Pika para AMQP

**Decisión**: `pika==1.3.2`, dependencia exacta del grupo `api`, que ya instala la imagen de ejecución compartida por API y publicador.

**Motivo**: es cliente Python de AMQP 0-9-1, ofrece `BlockingConnection` y publisher confirms y no introduce un framework de mensajería. El stack actual es síncrono; una conexión confinada al proceso de despacho evita compartir objetos Pika no thread-safe. La versión se fija en `pyproject.toml` y `uv.lock`.

**Alternativas**:
- Cliente asíncrono AMQP adicional: descartado porque el publicador será un proceso síncrono independiente y el resto de la persistencia usa SQLAlchemy síncrono.
- Publicar usando HTTP hacia el management plugin: rechazado; no es el protocolo de mensajes y exige el plugin/credenciales administrativas.

### 4. Testcontainers RabbitMQ

**Decisión**: reutilizar Testcontainers Python ya presente y fijar `testcontainers[postgres,rabbitmq]==4.15.0`; especificar siempre imagen y credenciales de test. `4.15.0` ya está resuelto en `uv.lock`. Import `RabbitMqContainer` de `testcontainers.rabbitmq`.

**Motivo**: el módulo administra lifecycle/readiness del contenedor RabbitMQ y ofrece parámetros AMQP para Pika. El testcontainer por defecto usa `rabbitmq:latest`, por lo tanto cada fixture debe pasar una etiqueta fija.

### 5. Versiones de infraestructura

| Componente | Versión/tag fijado | Motivo |
|---|---|---|
| PostgreSQL test y Compose | `postgres:17.11-alpine` | Coincide con Compose y los tests de integración existentes. |
| Keycloak Compose | `quay.io/keycloak/keycloak:26.8.1` | Imagen ya usada por M3 y compatible con el realm actual. |
| RabbitMQ test y Compose | `rabbitmq:4.2.3-management-alpine` | Tag activo verificado en Docker Hub; habilita AMQP y healthcheck. No usar `latest`. |
| Testcontainers Python | `4.15.0` | Ya bloqueado en `uv.lock`; sumar el extra de RabbitMQ sin actualizar versión mayor/menor. |
| Pika | `1.3.2` | Dependencia runtime fija para AMQP 0-9-1. |

**Fuentes**: [Testcontainers Python RabbitMQ](https://testcontainers-python.readthedocs.io/en/latest/modules/rabbitmq/README.html), [Pika en PyPI](https://pypi.org/project/pika/1.3.2/), [etiqueta RabbitMQ en Docker Hub](https://hub.docker.com/layers/library/rabbitmq/4.2.3-management-alpine/images/sha256:40c1ad1f394a8f8e532686d3e861bdcd776635a71f624a7eb265d64276d3f823).

### 6. E2E real separado de las pruebas con Testcontainers

**Decisión**:
- Testcontainers: PostgreSQL + RabbitMQ para pruebas rápidas de repositorio/outbox/publicación y concurrencia.
- Docker Compose: PostgreSQL, Keycloak, migraciones, seed, API, RabbitMQ y publicador para flujo HTTP real con tokens y reinicio.
- Los dobles de módulos vecinos implementan contratos fijados y validados, no reemplazan a Keycloak en el flujo de negocio de M3.

**Motivo**: Keycloak ya tiene realm de prueba y configuración Compose; este camino comprueba autenticación y permisos reales. Testcontainers mantiene aislados los tests de infraestructura y no obliga a convertirlos en pruebas de sistema completas.

### 7. Un job de CI para la prueba de integración

**Decisión**: agregar un único job de GitHub Actions para las historias de esta feature. El job instala dependencias una sola vez, comprueba Docker, inicia Compose y ejecuta la suite pytest completa con cobertura; la limpieza se ejecuta aunque fallen los tests.

**Motivo**: todas las pruebas comparten disponibilidad de Docker y el job ofrece una señal de CI inequívoca para integración. Los jobs actuales de lint, OpenAPI general y frontend permanecen independientes y sin acoplarse al ciclo de vida del Compose.

## Contratos vecinos: hallazgos y decisión

La copia consultada de `FRRe-DS/2026-TPI` corresponde al commit `69e9481c754063fc054c8d0ecfdec18d71bf48e6`:

- `contratos/m3_conductores/openapi.yml`, `contratos/m4_ubicacion/openapi.yml` y `contratos/m5_solicitud/openapi.yml` solo contienen versión, título y descripción: no validan operaciones ni modelos.
- No aparece `contratos/m1_identidad`; la forma del token descrita por M6 y M2 no coincide con `specs/iteracion1/contracts/token-jwt.md`.
- `contratos/m6_viajes/openapi.yml` sí define rutas en inglés `/trips/{id}`, `/complete` y `/cancel`; el OpenAPI de M3 describe rutas externas en español `/viajes/{id_viaje}`, `/finalizar` y `/cancelar`. La identidad también difiere (UUID en M6 vs. IDs enteros en M3).
- El contrato M6 declara un evento `TripCompleted` dirigido a M3, mientras que la decisión de alcance de esta feature es que M3 no consume eventos externos.

**Resolución del plan**: crear dobles solo desde contrato bilateral aprobado. Antes de completar pruebas M1/M4/M5/M6, el equipo debe resolver y publicar las diferencias de token, rutas, tipos/IDs, errores y eventos. No se toma el contrato M6 existente como equivalente al OpenAPI local de M3 ni se inventa una normalización local.

## Validación de concurrencia y aislamiento

La restricción `uq_conductor_dni` es la autoridad para arbitrar la carrera; la aplicación debe mapear la violación de unicidad a `409 DNI_DUPLICADO`. La prueba enviará requests independientes coordinados por una barrera, esperará ambas respuestas y consultará PostgreSQL fuera de las conexiones de escritura. Cada ejecución recibe DNI, patente y claves de evento únicas. No se usa un `TRUNCATE` global de datos compartidos durante pruebas paralelas.

## Riesgos de ejecución

- La suite existente marca integración como `skip` si no detecta Docker. El nuevo job requerido debe convertir Docker ausente o un skip de tests de integración obligatorios en fallo explícito.
- Reiniciar el servicio `api` de Compose no debe reiniciar PostgreSQL; la prueba verificará la misma fila por API y con lectura directa de la base.
- Un exchange/routing key no se fijará en configuración de producción hasta que conste en el contrato de eventos; la configuración de CI deriva del mismo artefacto.
- Las pruebas de contrato no pueden dar verde con documentos vacíos: validar su presencia, versión y que las operaciones requeridas existan antes de levantar dobles.

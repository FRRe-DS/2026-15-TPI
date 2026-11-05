# Investigación: Verificación de integración real de M3

**Fecha**: 2026-11-01

**Fuentes locales**: `docs/constitucion.md`, `docs/contract/openapi.yaml`, `infra/docker-compose.yml`, `backend/pyproject.toml`, `backend/uv.lock`, `specs/iteracion1/contracts/token-jwt.md`.

**Fuente de contratos del grupo**: [`FRRe-DS/2026-TPI`](https://github.com/FRRe-DS/2026-TPI). La versión vigente acordada es la que contiene las 17 operaciones de M3 y la matriz [`contracts/integraciones-modulos.md`](./contracts/integraciones-modulos.md).

## Decisiones

> **Alcance**: las decisiones 1–4 y las partes de RabbitMQ de las decisiones 5 y 6 están **condicionadas**. No se implementan mientras la PR 3 permanezca bloqueada por el conflicto FR-007/FR-013. Se documentan para el caso de que la cátedra confirme que M3 debe publicar eventos en un spec propio de Backend. Las decisiones 8–12 son las que guían el trabajo documental y de verificación de esta rama.

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
| RabbitMQ test y Compose | `rabbitmq:4.2.3-management-alpine` | Solo si se desbloquea la publicación: tag activo verificado en Docker Hub; habilita AMQP y healthcheck. No usar `latest`. |
| Testcontainers Python | `4.15.0` | Ya bloqueado en `uv.lock`; sumar el extra de RabbitMQ solo si se desbloquea la publicación, sin actualizar versión mayor/menor. |
| Pika | `1.3.2` | Dependencia runtime condicionada a la publicación de eventos para AMQP 0-9-1. |

**Fuentes**: [Testcontainers Python RabbitMQ](https://testcontainers-python.readthedocs.io/en/latest/modules/rabbitmq/README.html), [Pika en PyPI](https://pypi.org/project/pika/1.3.2/), [etiqueta RabbitMQ en Docker Hub](https://hub.docker.com/layers/library/rabbitmq/4.2.3-management-alpine/images/sha256:40c1ad1f394a8f8e532686d3e861bdcd776635a71f624a7eb265d64276d3f823).

### 6. E2E real separado de las pruebas con Testcontainers

**Decisión**:
- Testcontainers: PostgreSQL y, solo si se desbloquea la publicación, RabbitMQ, para pruebas rápidas de repositorio/outbox/publicación y concurrencia.
- Docker Compose: PostgreSQL, Keycloak, migraciones, seed y API para el flujo HTTP real con tokens y reinicio. Si se desbloquea la publicación, se agregan RabbitMQ y el publicador.
- Los dobles de módulos vecinos implementan contratos fijados y validados, no reemplazan a Keycloak en el flujo de negocio de M3.

**Motivo**: Keycloak ya tiene realm de prueba y configuración Compose; este camino comprueba autenticación y permisos reales. Testcontainers mantiene aislados los tests de infraestructura y no obliga a convertirlos en pruebas de sistema completas.

### 7. Un job de CI para la prueba de integración

**Decisión**: agregar un único job de GitHub Actions para las historias de esta feature. El job instala dependencias una sola vez, comprueba Docker, inicia Compose y ejecuta la suite pytest completa con cobertura; la limpieza se ejecuta aunque fallen los tests.

**Motivo**: todas las pruebas comparten disponibilidad de Docker y el job ofrece una señal de CI inequívoca para integración. Los jobs actuales de lint, OpenAPI general y frontend permanecen independientes y sin acoplarse al ciclo de vida del Compose.

### 8. Contrato de 17 operaciones y validación con openapi-core

**Decisión**: `backend/tests/contrato/test_openapi_ejemplos.py` pasa de 10 a 17 operaciones en `OPERACIONES_EN_ALCANCE`. Se agregan las 7 operaciones nuevas: `GET .../vehiculos/{id}/tipos-servicio`, `POST .../vehiculos/{id}/documentacion`, `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. `CODIGOS_POR_ESTADO` incorpora `410` con `SOLICITUD_VENCIDA` y los códigos nuevos `409 SOLICITUD_YA_RESPONDIDA`, `422 CONDUCTOR_NO_HABILITADO` y `403 ACCESO_PROHIBIDO`. Además de los ejemplos, las respuestas reales de los 7 endpoints se validan contra el YAML con `openapi-core`.

**Motivo**: el test actual de 10 operaciones deja fuera toda la superficie nueva y no detecta que `410` ya aparece en el contrato pero no en el catálogo de códigos. Validar solo ejemplos no comprueba que la respuesta real respete el esquema.

**Estado del YAML**: el contrato vigente del grupo es 1.2.0. La copia local `docs/contract/openapi.yaml` todavía refleja el contrato anterior; no se modifica en esta tanda documental. La validación con `openapi-core` se activa cuando la copia local esté actualizada y el backend de la Iteración 2 esté integrado.

### 9. Cobertura PostgreSQL de los 7 endpoints

**Decisión**: las pruebas de integración con PostgreSQL real cubren estos casos, con datos propios por prueba:

| Caso | Verificación |
|---|---|
| Estado | `DISPONIBLE` da `422 CONDUCTOR_NO_HABILITADO` si el conductor no está aprobado o su vehículo activo no está aprobado; desde `DESCONECTADO` y cumpliendo queda `DISPONIBLE`; `OCUPADO` da `400`. |
| Vehículo activo | Quitarlo o cambiarlo por uno no aprobado baja de `DISPONIBLE` a `CONECTADO`. |
| Aceptar solicitud | Un conductor `CONECTADO` o `DISPONIBLE` queda `OCUPADO`; si está `DESCONECTADO` u `OCUPADO`, da `422`. |
| Concurrencia | `PATCH /estado` y la aceptación de una solicitud sobre el mismo conductor, a la vez, no pierden cambios. |
| Solicitudes | Aceptar o rechazar una vigente funciona; una vencida da `410 SOLICITUD_VENCIDA`; responder dos veces da `409 SOLICITUD_YA_RESPONDIDA`, también en paralelo. |
| Promedio | `puntaje_promedio` y `cantidad_calificaciones` se leen del seed; sin calificaciones son `null` y `0`; ningún endpoint los modifica. |
| Ubicación | Sin ubicación responde `200` con los tres campos en `null`, nunca `0,0`; al pasar de `DESCONECTADO` a otro estado sin ubicación, M3 asigna una ubicación simulada fija. |

**Motivo**: son las reglas de negocio y las carreras donde una implementación que solo pasa tests unitarios puede fallar contra la base real. La migración `0002` reemplaza `conectado`/`disponible` por `estado`, así que los tests existentes que usan esas columnas se ajustan al recibirla.

### 10. Roles y helper de token `servicio`

**Decisión**:
- El rol `servicio` es de solo lectura. Recibe `403` en acciones de operador, `PATCH /conductores/{id}/estado` y `POST /solicitudes/{id}`; puede leer `GET /conductores`, detalle, habilitación, vehículos, tipos de servicio, `/estado` y `/ubicacion`.
- Un conductor solo opera sobre su propio `id_conductor`: `403` al consultar o modificar datos de otro conductor y `403` en `GET /conductores`. En `POST /solicitudes/{id}`, una solicitud inexistente da `404` y una ajena da `403 ACCESO_PROHIBIDO`.
- Se agrega un helper para firmar tokens con rol `servicio`, equivalente a `headers_conductor` y `headers_operador`; acepta la lista de roles y los claims `id_conductor`/`id_operador` del caso.

**Motivo**: sin el helper no se puede cubrir la matriz de roles completa sin Keycloak. La cuenta técnica de servicio la define el grupo de Datos y seguridad; en las pruebas se representa con un token firmado con rol `servicio`.

### 11. Conflictos de planificación

1. **Eventos RabbitMQ vs. FR-013**: el contrato 1.2.0 no define eventos y el backend de la Iteración 2 no los incluye. FR-013 pide no introducir funcionalidades de negocio nuevas. Hay que decidir entre confirmar con la cátedra que M3 publica eventos (trabajo propio de Backend) o retirar la Historia 3/FR-007–FR-009. Mientras tanto, **PR 3 queda bloqueada**.
2. **T008–T010 no prueban clientes salientes**: M3 no consume APIs de M4 ni M6 en esta iteración. La PR 4 se limita a lo que M3 expone: lecturas de M4 (`estado` y `/ubicacion`, además de listado y detalle) y solicitudes de M5.
3. **Dobles de M4/M6**: ya no hay endpoints que M4 o M6 llamen para escribir en M3. Para lecturas con rol `servicio` el doble es un token firmado; no se crean endpoints de escritura ni se accede a bases ajenas.
4. **Orden**: PR 1 y PR 2 usan endpoints existentes y pueden avanzar sin esperar. La migración `0002` reemplaza `conectado`/`disponible`; los tests que usan esas columnas se ajustan cuando llegue. Las pruebas de los 7 endpoints dependen de esa migración y del backend, y van después.
5. **PR 4 no depende de PR 3**: puede avanzar cuando los contratos de M4/M5 estén aprobados y versionados, sin inventar esquemas locales.

### 12. Cobertura y CI para la Iteración 2

**Decisión**: conservar el umbral vigente de `65 %` en `ci.yml` durante la transición y proponer `70 %` para la Iteración 2. Las pruebas nuevas de contrato (17 operaciones, `openapi-core`, catálogo con `410`) y de integración PostgreSQL (estado, vehículo activo, solicitudes, concurrencia, promedio y ubicación) se ejecutan en el job `integracion-real-m3`.

**Motivo**: la lógica nueva es principalmente dominio y casos de uso con tests unitarios, donde subir cobertura es barato. Dejar las pruebas nuevas fuera del job obligatorio permitiría que CI quede verde sin ejecutarlas.

## Contratos vecinos: estado vigente y decisión

El contrato de M3 tiene 17 operaciones (antes 19). Se retiraron `PATCH /integraciones/m4/.../disponibilidad` y `POST /integraciones/m6/.../finalizacion`; M3 no expone escrituras para otros módulos. `conectado` y `disponible` se reemplazan por `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`); `GET /conductores` filtra por `estado` y `OCUPADO` solo lo asigna M3 al aceptar una solicitud, no se puede pedir por `PATCH /conductores/{id}/estado` (responde `400`).

- **M1**: `specs/iteracion1/contracts/token-jwt.md` describe `realm_access.roles`, `id_operador` e `id_conductor`; incorpora `operador`, `conductor` y `servicio` (solo lectura). La cuenta técnica de servicio la define Datos y seguridad. No se encontró OpenAPI de M1 en el repo común. Para las pruebas, el helper de token debe aceptar `roles=[...]` y los claims `id_conductor`/`id_operador`.
- **M4**: consume M3 en solo lectura: `GET /conductores`, `GET /conductores/{id}`, `GET /conductores/{id}/estado` y `GET /conductores/{id}/ubicacion`. M4 no escribe en M3. `estado` tiene cuatro valores; la ubicación ausente son tres `null`, nunca `0,0`. El doble de lectura es un token firmado con rol `servicio`.
- **M5**: `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}` pertenecen a la Iteración 2 y todavía no existen en `dev`. Se verifican aceptar/rechazar vigente, `410 SOLICITUD_VENCIDA`, `409 SOLICITUD_YA_RESPONDIDA` y las reglas de `OCUPADO`.
- **M6**: no es una frontera de esta iteración. Sus operaciones se retiraron del contrato de M3, M3 no implementa clientes HTTP salientes y M6 tampoco escribe en M3.

**Resolución del plan**: crear dobles solo desde contratos bilaterales aprobados y versionados para M1, M4 y M5, limitados a lo que M3 expone. No se toman documentos vacíos como contrato ni se inventa una normalización local. M6 queda fuera del alcance de verificación. La publicación de eventos no se planifica mientras FR-007/FR-013 siga sin decisión: PR 3 está bloqueada y no se crea un contrato de eventos local.

## Validación de concurrencia y aislamiento

La restricción `uq_conductor_dni` es la autoridad para arbitrar la carrera; la aplicación debe mapear la violación de unicidad a `409 DNI_DUPLICADO`. La prueba enviará requests independientes coordinados por una barrera, esperará ambas respuestas y consultará PostgreSQL fuera de las conexiones de escritura. Cada ejecución recibe DNI, patente y claves de evento únicas. No se usa un `TRUNCATE` global de datos compartidos durante pruebas paralelas.

## Riesgos de ejecución

- La suite existente marca integración como `skip` si no detecta Docker. El nuevo job requerido debe convertir Docker ausente o un skip de tests de integración obligatorios en fallo explícito.
- Reiniciar el servicio `api` de Compose no debe reiniciar PostgreSQL; la prueba verificará la misma fila por API y con lectura directa de la base.
- Un exchange/routing key no se fijará en configuración de producción hasta que conste en el contrato de eventos; la configuración de CI deriva del mismo artefacto. Mientras la decisión esté pendiente, no se implementa el publicador.
- Las pruebas de contrato no pueden dar verde con documentos vacíos: validar su presencia, versión y que las operaciones requeridas existan antes de levantar dobles.
- Las pruebas de los 7 endpoints darían falsos negativos si se ejecutan antes de la migración `0002` o del backend de la Iteración 2; deben esperar esas dependencias y migrar los tests de `conectado`/`disponible` a `estado`.
- El contrato local debe actualizarse a 1.2.0 antes de validar respuestas reales con `openapi-core`; validar contra el YAML anterior haría fallar las operaciones o esquemas nuevos.
- Sin el helper de token `servicio`, la matriz de roles queda incompleta y el job podría quedar verde sin probar los `403` del rol de solo lectura.

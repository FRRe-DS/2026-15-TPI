# Plan de implementación: Verificación de integración real de M3

**Rama**: `001-verificacion-integracion-m3` | **Fecha**: 2026-11-01 | **Spec**: [spec.md](./spec.md)

**Entrada**: Especificación de [verificación de integración real de M3](./spec.md).

## Resumen

Demostrar en CI el flujo de habilitación con tokens reales de Keycloak, la unicidad ante altas concurrentes, la persistencia PostgreSQL tras reiniciar la API y los contratos con M1/M4/M5. La publicación de eventos a RabbitMQ queda **bloqueada** hasta una decisión de cátedra: el contrato 1.2.0 no define eventos, el backend de la Iteración 2 no los incluye y FR-013 prohíbe introducir funcionalidades de negocio nuevas. Si se confirma que M3 debe publicarlos, se especifican e implementan en un trabajo propio de Backend; mientras tanto, la PR 3 no avanza y la persistencia en PostgreSQL se verifica por separado. Las pruebas de adaptadores usarán PostgreSQL real mediante Testcontainers; el flujo HTTP y la persistencia golpearán el stack de Docker Compose con Keycloak real. Todos los conjuntos de pruebas nuevos se ejecutarán en el job `integracion-real-m3` de GitHub Actions.

La planificación parte del contrato vigente de M3, que tiene 17 operaciones (antes 19). Se retiraron `PATCH /integraciones/m4/.../disponibilidad` y `POST /integraciones/m6/.../finalizacion`: M3 no expone escrituras para otros módulos ni implementa clientes HTTP salientes en la Iteración 2. M4 es un consumidor de solo lectura de `GET /conductores`, `GET /conductores/{id}`, `GET /conductores/{id}/estado` y `GET /conductores/{id}/ubicacion`; M5 queda para la Iteración 2 y M1 incorpora el rol `servicio` de solo lectura. Se respetarán los contratos bilaterales aprobados; no se fijarán payloads ni nombres de eventos a partir de borradores incompatibles.

La verificación de la Iteración 2 cubre además los 7 endpoints nuevos: `GET .../vehiculos/{id}/tipos-servicio`, `POST .../vehiculos/{id}/documentacion`, `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. Esas pruebas se ejecutan después de la migración `0002` y del backend de la Iteración 2.

## Contexto técnico

**Lenguaje/versión**: Python 3.12; `uv` y `uv.lock`.

**Dependencias principales**: FastAPI, SQLAlchemy síncrono, Alembic, PyJWT; Pika `1.3.2` en el grupo runtime `api` solo si se desbloquea la publicación de eventos. Testcontainers Python se fijará en `4.15.0` con extras PostgreSQL/RabbitMQ, versión ya resuelta en el lockfile; el extra RabbitMQ solo se usa si se desbloquea esa publicación.

**Almacenamiento**: PostgreSQL 17.11, base propia de M3; la migración `0002` de la Iteración 2 y, solo si se desbloquea la publicación de eventos, una tabla outbox mediante migración Alembic.

**Mensajería**: RabbitMQ `4.2.3-management-alpine`, etiqueta fija, exchange durable según el contrato que apruebe el equipo; los mensajes publicados serán persistentes y confirmados. Esta parte queda bloqueada hasta la decisión sobre FR-007/FR-013 y no se implementa en la PR 3 mientras siga pendiente.

**Pruebas**: pytest + pytest-cov; Testcontainers para PostgreSQL y, si se desbloquea la publicación, RabbitMQ; OpenAPI para validación contractual; E2E HTTP contra API y Keycloak levantados por Docker Compose.

**Plataforma objetivo**: Linux en GitHub Actions; Docker disponible en CI y desarrollo.

**Tipo de proyecto**: API REST en capas con dominio/casos de uso, puertos y adaptadores; servicio auxiliar de despacho del outbox solo si se desbloquea la publicación de eventos.

**Metas de rendimiento**: Sin nueva meta cuantitativa; el retry del outbox, si se desbloquea, no bloqueará pedidos HTTP.

**Restricciones**: no publicar si la transacción falla; conservar eventos durante caída de RabbitMQ y reintentar con entrega al menos una vez; deduplicación mediante `event_id`; datos de prueba aislados; secretos exclusivamente por entorno; imágenes con versión fija, nunca `latest`. Las restricciones de mensajería aplican solo si se desbloquea la publicación de eventos.

**Alcance**: flujo de habilitación; concurrencia de alta de DNI; persistencia a través de reinicio de API; contrato de 17 operaciones y cobertura de los 7 endpoints nuevos; contratos M1, M4 y M5 limitados a lo que M3 expone; sin cambios de negocio, sin clientes salientes y sin pruebas frontend. La publicación de eventos queda fuera mientras FR-007/FR-013 siga sin decisión.

## Verificación de constitución

Fuente disponible: [`docs/constitucion.md`](../../docs/constitucion.md), versión declarada 1.0.0. `.specify/memory/constitution.md` conserva la plantilla sin completar; no se encontró en el worktree una enmienda posterior. Se aplica el texto normativo versionado en `docs/constitucion.md`.

| Principio | Decisión de diseño | Resultado |
|---|---|---|
| I. TDD no negociable | Escribir primero pruebas unitarias, de concurrencia, de contrato y E2E; las pruebas del outbox y del adaptador Rabbit solo se agregan si se desbloquea la publicación. Ninguna funcionalidad de producción se acepta sin el ciclo Red/Green/Refactor. | Cumple |
| II. Cobertura | Conservar el umbral CI vigente de 65 % durante la transición y proponer 70 % para la Iteración 2; ejecutar cobertura sobre el paquete `app` incluyendo la suite nueva. No bajar el umbral vigente. | Cumple |
| III. Pirámide | Unitarios de puertos/casos de uso; integración con Testcontainers PostgreSQL (RabbitMQ solo si se desbloquea); contratos OpenAPI; flujo E2E con Compose y Keycloak real. | Cumple |
| IV. API-first | Mantener el OpenAPI local de 17 operaciones como contrato de endpoints M3; ampliar `test_openapi_ejemplos.py` de 10 a 17 y validar respuestas reales con `openapi-core`. Fijar y comprobar los contratos bilaterales de M1/M4/M5 solo para lo que M3 expone. M4 es solo lectura y no hay clientes salientes a M4 ni M6. | Cumple con puerta contractual |
| V. Migraciones | La migración `0002` y, solo si se desbloquea la publicación, la tabla outbox se crean exclusivamente con Alembic; pruebas de migración hacia delante y atrás. | Cumple |
| VI. Sin secretos/versiones | Credenciales efímeras inyectadas por entorno; versiones fijas de imágenes y dependencias; ninguna etiqueta `latest`. | Cumple |
| VII. Código claro | Puertos pequeños, adaptadores explícitos, ruff check/format. El cliente Rabbit síncrono, si se desbloquea, corre en el proceso publicador, fuera de handlers HTTP. | Cumple |
| VIII. Trabajo en paralelo | Los contratos compartidos y, si se desbloquea, el esquema outbox son puntos de sincronización; dueños de rutas delimitados en la matriz siguiente. | Cumple |
| IX. Documentación breve | Especificación y guías de ejecución bajo `specs/001-verificacion-integracion-m3/`; README se actualiza al implementar. | Cumple |
| X. Propiedad de datos | M3 solo consulta su PostgreSQL; dobles de módulos externos exponen contratos, no sus tablas. | Cumple |
| XI. Concurrencia | Restricción única de DNI permanece como árbitro; dos peticiones HTTP concurrentes verifican un único alta y respuesta perdedora 409. Para los endpoints nuevos, el bloqueo de fila del conductor serializa `PATCH /estado` y la aceptación de solicitudes, y una segunda respuesta de solicitud da 409. | Cumple |

**Puerta previa a integrar dobles**: el contrato vigente de M3 tiene 17 operaciones. Se retiraron `PATCH /integraciones/m4/.../disponibilidad` y `POST /integraciones/m6/.../finalizacion`, por lo que M3 no expone escrituras para otros módulos. `Conductor.estado` reemplaza a `conectado`/`disponible` con `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`; `OCUPADO` lo asigna M3 al aceptar una solicitud y no se puede pedir por `PATCH /conductores/{id}/estado` (responde `400`). M4 solo lee (`GET /conductores`, detalle, estado y ubicación), M5 queda para la Iteración 2 y M1 incluye el rol `servicio` de solo lectura. Antes de dar por cubierta una frontera se deberá acordar y versionar su contrato bilateral y hacer que el test contractual falle ante cualquier incompatibilidad. La suite no aprobará tests basados solo en los esqueletos.

**Resultado de gate**: principios constitucionales cumplidos. El diseño técnico está resuelto; la implementación de pruebas contractuales M1/M4/M5 queda condicionada a publicar la matriz bilateral acordada. Este gate no autoriza a inventar un contrato.

## Cobertura de los 7 endpoints nuevos (Iteración 2)

Estas pruebas se ejecutan **después** de la migración `0002` y del backend de la Iteración 2. No se adelantan contra `dev` con `conectado`/`disponible`.

| Endpoint | Casos que debe cubrir |
|---|---|
| `GET /conductores/{id}/vehiculos/{id_vehiculo}/tipos-servicio` | Respuesta `200` con `tipo`/`habilitado`, `404` de vehículo o conductor inexistente y acceso de operador, conductor propio y `servicio`. |
| `POST /conductores/{id}/vehiculos/{id_vehiculo}/documentacion` | `201` con documento persistido, `422 DATOS_INVALIDOS` con vencimiento anterior a la emisión, `404` de vehículo y `403` para `servicio` y para un conductor ajeno. |
| `GET /conductores/{id}/estado` | `200` con `estado`, `id_vehiculo_activo` y `actualizado`; `404`; acceso de operador, conductor propio y `servicio`. |
| `PATCH /conductores/{id}/estado` | `DISPONIBLE` responde `422 CONDUCTOR_NO_HABILITADO` sin conductor aprobado o sin vehículo activo aprobado; desde `DESCONECTADO` y cumpliendo queda `DISPONIBLE`; `OCUPADO` responde `400`; quitar/cambiar el vehículo activo baja de `DISPONIBLE` a `CONECTADO`; sin ubicación se asigna la simulada fija; concurrencia con aceptación de solicitud sin perder cambios. |
| `GET /conductores/{id}/ubicacion` | `200` con `latitud`, `longitud` y `fecha_act_ubic`; sin ubicación los tres son `null` y nunca `0,0`; `404`; acceso de operador, conductor propio y `servicio`. |
| `GET /conductores/{id}/solicitudes` | `200` con solicitudes del conductor; el filtro `estado` usa el estado efectivo y una `PENDIENTE` vencida aparece como `VENCIDA`; `404`; acceso de operador y conductor propio, no `servicio`. |
| `POST /solicitudes/{id}` | Aceptar o rechazar una vigente responde `200`; aceptar deja `OCUPADO` a un conductor `CONECTADO`/`DISPONIBLE` y `422 CONDUCTOR_NO_HABILITADO` si está `DESCONECTADO`/`OCUPADO`; vencida responde `410 SOLICITUD_VENCIDA`; segunda respuesta responde `409 SOLICITUD_YA_RESPONDIDA`, también en paralelo; conductor ajeno responde `403 ACCESO_PROHIBIDO`. |

**Contrato y errores**: `backend/tests/contrato/test_openapi_ejemplos.py` pasa de 10 a 17 operaciones en `OPERACIONES_EN_ALCANCE`. `CODIGOS_POR_ESTADO` incorpora `410` con `SOLICITUD_VENCIDA` y los códigos nuevos `SOLICITUD_YA_RESPONDIDA`, `CONDUCTOR_NO_HABILITADO` y `ACCESO_PROHIBIDO`. Las respuestas reales de los 7 endpoints se validan contra `docs/contract/openapi.yaml` con `openapi-core`; no alcanza con validar los ejemplos. Los tests existentes que leen `conectado` y `disponible` se migran a `estado`.

**Promedio y ubicación**: `puntaje_promedio` y `cantidad_calificaciones` se leen del seed; sin calificaciones son `null` y `0`, y ningún endpoint de esta historia los escribe. La ubicación ausente se representa con tres `null`, nunca con `(0, 0)`.

## Roles y tokens de prueba

- El rol `servicio` es de **solo lectura**: recibe `403` en acciones de operador, en `PATCH /conductores/{id}/estado` y en `POST /solicitudes/{id}`. Puede leer `GET /conductores`, detalle, habilitación, vehículos, tipos de servicio, `/estado` y `/ubicacion`.
- Un conductor solo opera sobre su propio `id_conductor`: recibe `403` al consultar o modificar datos de otro conductor y `403` en `GET /conductores`.
- El conductor dueño de una solicitud puede responderla; la de otro conductor responde `403 ACCESO_PROHIBIDO` (inexistente responde `404`).
- Se agrega un helper de token con rol `servicio`, equivalente a `headers_conductor` y `headers_operador`; debe aceptar la lista de roles y los claims `id_conductor`/`id_operador` del caso.
- La cuenta técnica de servicio la define el grupo de Datos y seguridad; en las pruebas se representa con un token firmado con rol `servicio`, no con un endpoint de escritura.

## Conflictos de planificación

1. **Eventos RabbitMQ vs. FR-013**: el contrato 1.2.0 no define eventos y el backend de la Iteración 2 no los incluye. FR-013 prohíbe introducir funcionalidades de negocio nuevas. Se debe confirmar con la cátedra si M3 publica eventos (trabajo propio de Backend) o si se retira la Historia 3/FR-007–FR-009. Mientras tanto, **PR 3 queda bloqueada**.
2. **Clientes salientes M4/M6**: las tareas T008–T010 no prueban clientes salientes porque M3 no consume APIs de M4 ni M6 en esta iteración. La PR 4 se limita a lo que M3 expone: lecturas de M4 (`estado` y `/ubicacion`, además del listado y detalle) y solicitudes de M5.
3. **Dobles de M4/M6**: ya no hay endpoints que M4 o M6 llamen para escribir en M3. Para las lecturas con rol `servicio` el doble es un token firmado con ese rol; no se crean endpoints HTTP de escritura ni se accede a bases ajenas.
4. **Orden**: PR 1 (flujo de habilitación) y PR 2 (alta concurrente con DNI duplicado) usan endpoints existentes y pueden avanzar sin esperar. La migración `0002` reemplaza `conectado` y `disponible` por `estado`, así que los tests que usan esas columnas se ajustan cuando llegue. Las pruebas de los 7 endpoints dependen de esa migración y del backend, y van después.
5. **PR 4**: no depende de PR 3; puede avanzar cuando los contratos de M4/M5 estén aprobados y versionados, sin inventar esquemas locales.

## Cobertura y CI

El umbral vigente en `.github/workflows/ci.yml` es `--cov-fail-under=65`. Para la Iteración 2 se propone `70 %`, una vez integradas las pruebas de los 7 endpoints. Las pruebas nuevas de contrato (`test_openapi_ejemplos.py` con 17 operaciones, `openapi-core` y catálogo ampliado) y las de integración con PostgreSQL real (estado, vehículo activo, solicitudes, concurrencia, promedio y ubicación) deben ejecutarse dentro del job `integracion-real-m3`, no en jobs separados que puedan quedar verdes por omisión.

## Estructura del proyecto

### Documentación de esta funcionalidad

```text
specs/001-verificacion-integracion-m3/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── eventos-m3.md
│   └── integraciones-modulos.md
└── checklists/requirements.md
```

### Código fuente previsto

```text
backend/
├── app/
│   ├── aplicacion/
│   │   └── puertos/                 # Puerto de eventos transaccionales (solo si se desbloquea)
│   ├── infraestructura/
│   │   ├── db/                      # Modelo SQLAlchemy del outbox (solo si se desbloquea)
│   │   └── repositorios/            # Escritura/claim SQL del outbox (solo si se desbloquea)
│   └── infraestructura/mensajeria/  # Adaptador RabbitMQ (solo si se desbloquea)
├── tests/
│   ├── api/                         # Routers, matriz de roles y helper de token servicio
│   ├── contrato/                    # test_openapi_ejemplos (17 ops) y openapi-core
│   ├── e2e/                         # API/Keycloak reales del Compose
│   └── integracion/
│       ├── concurrencia/            # Peticiones HTTP paralelas y estado PostgreSQL
│       ├── estado/                  # Estado, vehículo activo, promedio y ubicación
│       ├── solicitudes/             # Solicitudes vigentes, vencidas y duplicadas
│       └── mensajeria/              # Testcontainers PostgreSQL + RabbitMQ (bloqueado)
├── pyproject.toml
└── uv.lock

infra/
├── docker-compose.yml                # RabbitMQ y despacho (bloqueado)
└── migraciones/versions/             # Migración 0002 y tabla outbox (esta última bloqueada)

.github/workflows/ci.yml              # Un job de verificación real M3
docs/contract/openapi.yaml            # Actualización solo tras acuerdo bilateral
```

**Decisión de estructura**: mantener las capas existentes y reutilizar la unidad de trabajo SQL. Si se desbloquea la publicación de eventos, el adaptador de aplicación escribe el evento en el outbox usando la misma sesión/transacción que guarda entidad e historial, y un proceso independiente reclama pendientes, los publica por un puerto de mensajería implementado con RabbitMQ y los marca publicados solo después de recibir confirmación del broker. Mientras la decisión esté pendiente, no se crean esas piezas.

## Estrategia de verificación

1. **Pruebas aisladas con Testcontainers**: fixtures pytest levantan PostgreSQL `17.11-alpine` con etiquetas explícitas y, solo si se desbloquea la publicación, RabbitMQ `4.2.3-management-alpine`. Migraciones aplicadas a la base de prueba. Cada prueba usa identificadores propios; no se truncan datos compartidos en paralelo.
2. **Atomicidad/outbox (bloqueado)**: si se desbloquea, comprobar que la fila de outbox y el cambio de dominio se confirman juntos; rollback elimina ambos. Consumir desde una cola exclusiva temporal ligada al exchange/routing key del contrato. Validar `event_id`, nombre, cabeceras y payload contra el contrato acordado.
3. **Entrega durable (bloqueado)**: si se desbloquea, parar/disponibilizar RabbitMQ durante una creación, comprobar que el API confirma el cambio guardando el outbox y que el publicador reintenta al recuperar el broker. Simular crash tras confirmación antes del marcado de outbox y aceptar duplicado con el mismo `event_id`.
4. **Concurrencia**: generar DNI único por prueba; dos workers con clientes HTTP independientes y barrera de sincronización disparan el mismo `POST /conductores`. Aserciones exactas: respuestas `[201, 409]`, error perdedor `DNI_DUPLICADO`, exactamente una fila y un único evento `ALTA` correspondiente. Para la Iteración 2 se agregan dos carreras: `PATCH /conductores/{id}/estado` contra aceptar una solicitud sobre el mismo conductor, y dos respuestas paralelas de la misma solicitud (`200` y `409 SOLICITUD_YA_RESPONDIDA`).
5. **E2E Compose**: iniciar PostgreSQL, Keycloak, migraciones, seed y API; conseguir tokens por el endpoint OIDC del realm real de Compose; recorrer alta, licencia, vehículo y aprobaciones; validar roles e historial. Si se desbloquea la publicación, agregar RabbitMQ/publicador, confirmar el mensaje en cola temporal y reiniciar solo API/publicador. En todos los casos, reiniciar la API sin reiniciar PostgreSQL y comprobar que los datos siguen disponibles.
6. **Contratos vecinos**: cada doble se construye a partir del OpenAPI/esquema bilateral aprobado y valida request/response con los mismos documentos versionados. Un documento faltante, vacío, desactualizado o incompatible falla el job antes de considerar completa la historia.
7. **CI**: el job Linux `integracion-real-m3` prepara variables de prueba, arranca Compose, verifica salud, corre pytest completo con cobertura (incluyendo Testcontainers, E2E y las pruebas de los 7 endpoints) y siempre ejecuta `docker compose down -v` en `if: always()`. Un fallo de Docker, servicio requerido, test marcado como skip o contrato no disponible hace fallar este job. La cobertura se ejecuta con `--cov-fail-under=70` para la Iteración 2; 65 % es el umbral vigente hasta que se integre la suite nueva. Los jobs de lint y frontend existentes conservan su independencia.
8. **Endpoints nuevos**: contrato de 17 operaciones y `CODIGOS_POR_ESTADO` con `410`; pruebas de estado y vehículo activo, aceptación de solicitudes, concurrencia `PATCH`/aceptación, solicitudes vencidas y duplicadas, promedio del seed, ubicación nula/simulada y matriz de roles con token `servicio`. Se ejecutan después de la migración `0002` y del backend de la Iteración 2.

## Complejidad

La tabla outbox es la complejidad mínima para cumplir simultáneamente atomicidad y recuperación ante caída del broker: publicar directamente desde el caso de uso antes/después del commit deja una ventana de pérdida o evento fantasma. El proceso de despacho usa confirmaciones y reintentos; no se introducen nuevos servicios de negocio ni una plataforma de eventos adicional. **Esta complejidad no se implementa mientras la decisión sobre FR-007/FR-013 siga pendiente**: la persistencia PostgreSQL se verifica sin RabbitMQ y la PR 3 permanece bloqueada.

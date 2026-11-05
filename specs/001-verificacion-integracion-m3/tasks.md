# Tareas: Verificación de integración real de M3

**Entrada**: Diseño en `specs/001-verificacion-integracion-m3/`

**Requisitos previos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Límite**: 16 tareas en total. Las tareas T001–T010 forman las cuatro PR originales; T011–T016 cubren los 7 endpoints nuevos de la Iteración 2 y se ejecutan después de la migración `0002` y del backend. Cada cambio de implementación queda precedido por una tarea Red identificada por su ID.

**TDD**: El test se escribe y se confirma fallando antes del código/configuración que lo hace pasar. Luego se aplica la implementación mínima (Green) y refactor solo si mejora el diseño sin alterar contratos. No se modifica un test para ocultar un fallo de comportamiento.

**Convención de tarea**: `- [ ] TNNN [USn] Descripción concreta con rutas`

## PR 1 — Flujo completo con Keycloak real

**Entrega**: recorrido HTTP completo de alta, licencia, vehículo y habilitaciones en Compose con tokens reales de Keycloak, controles por rol e historial. Primer job de CI para la feature, ejecutando las pruebas E2E sin skips.

**Rama**: `001-verificacion-integracion-m3-pr1-flujo-completo`

**Base**: `dev`. Abrir PR contra `dev` y dejar CI verde antes de integrar; PR 2 parte de `dev` con esta PR ya integrada.

- [ ] T001 [US1] Red: agregar `backend/tests/e2e/test_flujo_habilitacion.py` contra la API y Keycloak reales de Docker Compose. Obtener tokens mediante el endpoint OIDC del realm `m3`; probar alta, licencia vigente, vehículo, aprobación de conductor y vehículo, respuestas de historial con eventos `ALTA` y aprobación, denegación de acción de operador con token de conductor y rechazo de aprobación sin licencia vigente sin cambios de estado/historial. Usar DNI y patente exclusivos por ejecución. Ejecutar contra el stack actual y registrar los fallos observados antes de implementar.
- [ ] T002 [US1] Green: hacer pasar T001 con los cambios mínimos a `infra/docker-compose.yml`, `infra/.env.example`, `backend/tests/e2e/conftest.py`, `backend/app/` y `.github/workflows/ci.yml`. Crear el job único `integracion-real-m3` que genere credenciales efímeras, levante Compose con `postgres:17.11-alpine` y `quay.io/keycloak/keycloak:26.8.1` (sin `latest`), espere salud de PostgreSQL/Keycloak/API, ejecute E2E sin permitir skips y limpie con `if: always()`. No reemplazar Keycloak por tokens firmados en el test.

**Criterio independiente**: T001 pasa en Compose desde entorno limpio; token operador completa flujo; token conductor no puede aprobar; se conservan resultados e historial esperados.

## PR 2 — Concurrencia real de alta

**Entrega**: demostración repetible de dos altas concurrentes del mismo DNI a través del endpoint HTTP y contra PostgreSQL real.

**Rama**: `001-verificacion-integracion-m3-pr2-concurrencia-real`

**Base**: `dev` con PR 1 integrada. Integrar solo con CI verde.

- [ ] T003 [US2] Red: agregar `backend/tests/integracion/concurrencia/test_alta_dni_http_concurrente.py`. Coordinar dos clientes HTTP independientes con una barrera de inicio (sin `sleep` para inducir carrera), autenticarse con token válido, enviar simultáneamente el mismo DNI y afirmar exactamente una respuesta `201`, una `409` con `codigo=DNI_DUPLICADO`, exactamente una fila para ese DNI en PostgreSQL y un solo evento de alta asociado. Generar DNI propio de la prueba; ejecutar y registrar el fallo antes de modificar el manejo de concurrencia.
- [ ] T004 [US2] Green: ajustar lo mínimo en `backend/app/infraestructura/repositorios/`, `backend/app/aplicacion/`, `backend/app/api/` y `backend/tests/integracion/conftest.py` para que T003 pase bajo PostgreSQL real. La restricción única de la base sigue siendo la autoridad de exclusión; traducir la colisión concurrente a `409 DNI_DUPLICADO`, asegurar rollback de datos parciales y mantener el aislamiento por prueba. Incorporar el test al job `integracion-real-m3` de `.github/workflows/ci.yml`.

**Criterio independiente**: T003 demuestra el par exacto de respuestas y una sola fila en ejecuciones repetidas; no depende del orden de planificación ni de datos ajenos.

## PR 3 — Persistencia real y eventos RabbitMQ — **BLOQUEADA**

> **No implementar hasta decisión de cátedra**: el contrato 1.2.0 no define eventos, el backend de la Iteración 2 no los incluye y FR-013 prohíbe introducir funcionalidades de negocio nuevas. Si se confirma que M3 publica eventos, T005–T007 pasan a un spec propio de Backend. La persistencia en PostgreSQL puede verificarse sin RabbitMQ (ver T011–T016).

**Entrega**: outbox transaccional, adaptador RabbitMQ durable y pruebas de publicación, rollback, caída/recuperación del broker y persistencia tras reiniciar API.

**Rama**: `001-verificacion-integracion-m3-pr3-postgres-rabbitmq`

**Base**: `dev` con PR 2 integrada. Integrar solo con CI verde.

- [ ] T005 [US3] Red: agregar pruebas fallidas antes de producción en `backend/tests/integracion/mensajeria/test_outbox_rabbitmq.py` y `backend/tests/e2e/test_persistencia_eventos.py`. Con Testcontainers PostgreSQL `17.11-alpine` y RabbitMQ `4.2.3-management-alpine`, probar escritura atómica entidad/historial/evento, rollback sin mensaje, consumo desde cola exclusiva temporal con payload conforme al contrato aprobado, conservación/reintento tras caída del broker y duplicado tolerable con el mismo `event_id`. El E2E debe leer el registro antes y después de reiniciar solo la API, sin reiniciar PostgreSQL. Ejecutar tests y confirmar fallos por ausencia de outbox/publicador antes del cambio productivo. No inventar nombres, exchange, routing keys o payloads: mantener T005 bloqueada no solo hasta que `specs/001-verificacion-integracion-m3/contracts/eventos-m3.md` contenga el contrato acordado, sino hasta que la cátedra resuelva el conflicto entre FR-007 y FR-013. Si se retira la Historia 3, T005–T007 se eliminan de esta feature.
- [ ] T006 [US3] Green: hacer pasar T005 implementando la migración Alembic y modelo/repositorio `outbox_evento` en `infra/migraciones/versions/`, `backend/app/infraestructura/db/` y `backend/app/infraestructura/repositorios/`; agregar el puerto de aplicación y conectarlo a la unidad de trabajo SQL existente en `backend/app/aplicacion/puertos/` y los casos de uso afectados. Implementar adaptador y despachador RabbitMQ en `backend/app/infraestructura/mensajeria/`, con exchange/mensaje durable, publisher confirms, lease de mensajes, reintento con backoff y `event_id` estable; marcar como publicado solo tras confirm. Añadir `pika==1.3.2` al grupo runtime que ejecuta el publicador y `testcontainers[postgres,rabbitmq]==4.15.0` al grupo de pruebas de `backend/pyproject.toml`; regenerar `backend/uv.lock`. No compartir conexiones Pika entre hilos.
- [ ] T007 [US3] Red→Green de Compose: ampliar primero `backend/tests/e2e/test_persistencia_eventos.py` para que falle si Compose no inicia RabbitMQ/publicador o si no se recibe el evento tras la acción y tras la recuperación del broker; luego conectar `rabbitmq` y el servicio publicador al `infra/docker-compose.yml`, con healthcheck, configuración exclusivamente por entorno y etiquetas fijas, hasta pasar el test. Extender el job existente `integracion-real-m3` de `.github/workflows/ci.yml` para ejecutar T005/T007 y toda la suite requerida en el mismo job; validar migraciones, espera de salud y limpieza aunque falle pytest. Actualizar `specs/001-verificacion-integracion-m3/quickstart.md` con los comandos reales de ejecución.

**Criterio independiente**: rollback no produce mensaje; commit confirmado sobrevive a caída del broker y termina publicado; duplicados comparten `event_id`; PostgreSQL conserva los datos a través del reinicio de API.

## PR 4 — Contratos de lo que M3 expone: M1, M4 y M5 — **LIMITADA**

**Entrega**: artefactos bilaterales versionados y dobles que validan solo lo que M3 expone: JWT/roles de M1, lecturas de M4 (`GET /conductores`, detalle, `/estado` y `/ubicacion`) y solicitudes de M5. No se prueban clientes salientes ni escrituras de M4/M6.

**Rama**: `001-verificacion-integracion-m3-pr4-contratos-expuestos`

**Base**: `dev` con PR 2 integrada; **no depende de PR 3**. Integrar solo con CI verde. La PR queda bloqueada si los módulos propietarios no aprobaron los contratos indicados en T008; no crear esquemas locales para simular ese acuerdo.

- [ ] T008 [US4] Red: agregar `backend/tests/contrato/test_contratos_modulos_vecinos.py` y `backend/tests/contrato/fixtures/` con expectativas mínimas para M1 (emisor/JWKS/claims/roles, incluido `servicio` de solo lectura), M4 (lecturas de conductor, `estado`, ubicación nullable e IDs) y M5 (solicitudes y estados, Iteración 2). Validar que cada documento bilateral fijado en `specs/001-verificacion-integracion-m3/contracts/integraciones-modulos.md` existe, no es solo metadata y contiene las operaciones/esquemas requeridos; demostrar que el test falla con los documentos actuales incompletos o incompatibles. Antes de desbloquear Green, solicitar/fijar con cada grupo propietario la versión exacta de contrato; en particular resolver la discrepancia JWT de M1 y confirmar que M5 todavía no existe en `dev`. Esta tarea **no prueba clientes salientes hacia M4 ni M6**: M3 no consume esas APIs en esta iteración. Tampoco prueba escrituras de M4/M6 en M3, porque esas operaciones se retiraron del contrato. No inferir nombres, campos ni equivalencias.
- [ ] T009 [US4] Green: una vez aprobados y versionados los contratos, guardar sus copias inmutables/referenciadas en `specs/001-verificacion-integracion-m3/contracts/` y hacer pasar T008 con dobles HTTP/JWKS en `backend/tests/contrato/dobles/`. Validar las respuestas de M3 para M4/M5 con los esquemas acordados, el JWT de M1 con los claims canónicos (incluido `servicio` de solo lectura) y las operaciones M4/M5 convenidas. En esta iteración M3 no implementa clientes HTTP salientes: los dobles cubren los contratos que M3 expone. Para las lecturas con rol `servicio`, el doble es un token firmado con ese rol; no se crean endpoints HTTP de escritura de M4/M6. Implementar únicamente los mapeos/adaptadores faltantes en `backend/app/` precedidos por el test de T008; si el acuerdo requiere cambiar un endpoint, actualizar primero `docs/contract/openapi.yaml` según API-first. No cubrir con dobles una frontera que siga sin contrato aprobado.
- [ ] T010 [US4] Green final: integrar `backend/tests/contrato/test_contratos_modulos_vecinos.py` en el job único `integracion-real-m3` de `.github/workflows/ci.yml`, con fallo explícito ante archivos ausentes, incompatibles o pruebas omitidas. Ejecutar la suite de PR 1–4, `ruff check`, `ruff format --check` y cobertura `pytest --cov=app --cov-fail-under=70` (propuesto para la Iteración 2; 65 % es el umbral vigente hasta el acuerdo); actualizar `specs/001-verificacion-integracion-m3/contracts/integraciones-modulos.md` con referencias/versiones finales y verificar que no quedan acuerdos implícitos.

**Criterio independiente**: los dobles de M1/M4/M5 validan solo documentos aprobados; una incompatibilidad deliberada del request, response, claim o esquema de evento hace fallar el test específico y el job de CI.

## PR 5 — Cobertura de los 7 endpoints nuevos (Iteración 2, posterior a migración `0002`)

**Entrega**: contrato de 17 operaciones, catálogo de errores ampliado, pruebas de rol `servicio`, integración PostgreSQL de estado/vehículo/solicitudes/concurrencia/promedio/ubicación y ejecución en el job `integracion-real-m3`.

**Rama**: `001-verificacion-integracion-m3-pr5-endpoints-iteracion2`

**Base**: `dev` con la migración `0002` y el backend de la Iteración 2 integrados. No se adelanta contra `dev` con `conectado`/`disponible`.

- [ ] T011 [US5] Red contrato: ampliar `backend/tests/contrato/test_openapi_ejemplos.py` de 10 a 17 operaciones en `OPERACIONES_EN_ALCANCE` para `GET .../vehiculos/{id}/tipos-servicio`, `POST .../vehiculos/{id}/documentacion`, `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. Agregar `410` con `SOLICITUD_VENCIDA` y los códigos `SOLICITUD_YA_RESPONDIDA`, `CONDUCTOR_NO_HABILITADO` y `ACCESO_PROHIBIDO` a `CODIGOS_POR_ESTADO`. Agregar la validación de las respuestas reales con `openapi-core` contra `docs/contract/openapi.yaml`, no solo los ejemplos. Confirmar que falla con el estado actual (10 operaciones y sin `410`).
- [ ] T012 [US5] Red roles: agregar el helper de token `servicio` en `backend/tests/api/conftest.py` (equivalente a `headers_conductor`/`headers_operador`, con roles y claims configurables) y `backend/tests/api/test_roles_servicio.py`. Verificar `403` de `servicio` en acciones de operador, `PATCH /conductores/{id}/estado` y `POST /solicitudes/{id}`, y lectura permitida de `GET /conductores`, detalle, `/estado` y `/ubicacion`. Verificar `403` de un conductor sobre otro conductor y en `GET /conductores`.
- [ ] T013 [US5] Red estado y ubicación PostgreSQL: agregar `backend/tests/integracion/estado/test_estado_conductor_pg.py`. Cubrir `DISPONIBLE` con `422 CONDUCTOR_NO_HABILITADO` sin aprobación o sin vehículo activo aprobado; `DESCONECTADO` `+` condiciones `→` `DISPONIBLE`; `OCUPADO` `→` `400`; quitar o cambiar el vehículo activo `→` `CONECTADO`; `GET /ubicacion` sin datos `→` `200` con tres `null` y nunca `0,0`; paso de `DESCONECTADO` a otro estado sin ubicación `→` ubicación simulada fija. Ejecutar y registrar el fallo antes de la implementación.
- [ ] T014 [US5] Red solicitudes, concurrencia y promedio PostgreSQL: agregar `backend/tests/integracion/solicitudes/test_solicitudes_pg.py` y `backend/tests/integracion/concurrencia/test_estado_aceptacion.py`. Cubrir aceptar/rechazar vigente, aceptar `→` `OCUPADO` desde `CONECTADO`/`DISPONIBLE`, `422` desde `DESCONECTADO`/`OCUPADO`, vencida `→` `410 SOLICITUD_VENCIDA`, doble respuesta `→` `409 SOLICITUD_YA_RESPONDIDA` también en paralelo, `PATCH /estado` concurrente con aceptación sin perder cambios, y lectura de `puntaje_promedio`/`cantidad_calificaciones` del seed (`null`/`0` sin calificaciones) sin que ningún endpoint los modifique. Ejecutar y registrar el fallo antes de la implementación.
- [ ] T015 [US5] Green: una vez integradas la migración `0002` y el backend, hacer pasar T011–T014 con los ajustes mínimos de tests/fixtures. Migrar los tests existentes que leen `conectado` y `disponible` para que lean `estado`; no cambiar aserciones de negocio para ocultar fallos. Actualizar `backend/tests/api/conftest.py` y las fixtures de integración con el helper `servicio` y datos propios por prueba.
- [ ] T016 [US5] Green CI: incorporar T011–T015 al job `integracion-real-m3` de `.github/workflows/ci.yml`, con fallo ante tests omitidos y contrato incompleto. Ejecutar cobertura `pytest --cov=app --cov-fail-under=70` (propuesto; 65 % vigente hasta el acuerdo) y actualizar `specs/001-verificacion-integracion-m3/quickstart.md` con los comandos de las pruebas nuevas.

**Criterio independiente**: las 17 operaciones validan contra el YAML con `openapi-core`; los casos PostgreSQL producen exactamente los estados y códigos acordados; las carreras no pierden cambios; el rol `servicio` solo lee; la cobertura y el job de CI quedan verdes con el umbral acordado.

## Dependencias y orden de integración

- **PR 1 / T001 → T002**: el test E2E define el comportamiento; los cambios Compose/API/CI se hacen después del fallo reproducible. **Puede avanzar sin esperar la migración `0002` ni los 7 endpoints**, porque usa endpoints existentes.
- **PR 2 / T003 → T004**: prueba HTTP simultánea y consulta DB preceden el ajuste de concurrencia. PR 2 parte de `dev` después de integrar PR 1. **También puede avanzar sin esperar los 7 endpoints**.
- **PR 3 / T005 → T006 → T007**: **bloqueada**. No se implementa hasta que la cátedra resuelva el conflicto entre publicar eventos (FR-007) e introducir funcionalidades nuevas (FR-013). Si se confirma, va a un spec propio de Backend; si se retira, T005–T007 desaparecen. La persistencia PostgreSQL se cubre en T013–T016 sin RabbitMQ.
- **PR 4 / T008 → T009 → T010**: los contratos propietarios aprobados son prerequisito para dobles; luego se habilitan y se conectan al job común. **No depende de PR 3** y se limita a lo que M3 expone: JWT/roles de M1, lecturas de M4 (`estado` y `/ubicacion`) y solicitudes de M5. No prueba clientes salientes ni escrituras de M4/M6.
- **PR 5 / T011 → T012 → T013 → T014 → T015 → T016**: va **después** de la migración `0002` y del backend de la Iteración 2. T011–T014 son Red y deben fallar primero; T015 hace pasar con los ajustes mínimos y migra los tests de `conectado`/`disponible` a `estado`; T016 lo incorpora al job `integracion-real-m3` con cobertura 70 %.
- No se paralelizan PRs dentro de la misma rama: cada PR se crea desde `dev` y se integra en `dev` secuencialmente, con CI verde antes de avanzar a la siguiente. Excepciones explícitas: PR 1 y PR 2 pueden avanzar sobre endpoints existentes sin esperar `0002`; PR 4 no depende de PR 3. La migración `0002` reemplaza `conectado`/`disponible`; los tests que usan esas columnas se ajustan al recibirla.

## Estrategia de entrega

1. **MVP verificable**: PR 1, flujo de habilitación real con Keycloak y Compose.
2. **Integridad de alta**: PR 2, carrera HTTP respaldada por PostgreSQL real.
3. **Durabilidad**: PR 3, outbox transaccional y RabbitMQ real con recuperación. **Bloqueada** hasta decisión sobre FR-007/FR-013.
4. **Cierre contractual**: PR 4, contratos reales y dobles fieles de lo que M3 expone, sujeto a aprobación bilateral.
5. **Cobertura Iteración 2**: PR 5, contrato de 17 operaciones y pruebas de los 7 endpoints con PostgreSQL real, después de la migración `0002` y del backend.

## Validación de formato

- Tareas totales: **16**.
- Distribución: **PR 1 = 2**, **PR 2 = 2**, **PR 3 = 3 (bloqueada)**, **PR 4 = 3 (limitada)**, **PR 5 = 6 (Iteración 2)**.
- Cada línea de tarea incluye checkbox, ID secuencial, etiqueta de historia y rutas concretas.
- Cada bloque de implementación indica el test Red previo y la condición Green.

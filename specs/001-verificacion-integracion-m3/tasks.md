# Tareas: Verificación de integración real de M3

**Entrada**: Diseño en `specs/001-verificacion-integracion-m3/`

**Requisitos previos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Límite**: 10 tareas en total, organizadas en cuatro PR secuenciales; cada PR contiene 2 o 3 tareas. Cada cambio de implementación queda precedido por una tarea Red identificada por su ID.

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

## PR 3 — Persistencia real y eventos RabbitMQ

**Entrega**: outbox transaccional, adaptador RabbitMQ durable y pruebas de publicación, rollback, caída/recuperación del broker y persistencia tras reiniciar API.

**Rama**: `001-verificacion-integracion-m3-pr3-postgres-rabbitmq`

**Base**: `dev` con PR 2 integrada. Integrar solo con CI verde.

- [ ] T005 [US3] Red: agregar pruebas fallidas antes de producción en `backend/tests/integracion/mensajeria/test_outbox_rabbitmq.py` y `backend/tests/e2e/test_persistencia_eventos.py`. Con Testcontainers PostgreSQL `17.11-alpine` y RabbitMQ `4.2.3-management-alpine`, probar escritura atómica entidad/historial/evento, rollback sin mensaje, consumo desde cola exclusiva temporal con payload conforme al contrato aprobado, conservación/reintento tras caída del broker y duplicado tolerable con el mismo `event_id`. El E2E debe leer el registro antes y después de reiniciar solo la API, sin reiniciar PostgreSQL. Ejecutar tests y confirmar fallos por ausencia de outbox/publicador antes del cambio productivo. No inventar nombres, exchange, routing keys o payloads: bloquear la aprobación de T005 hasta que `specs/001-verificacion-integracion-m3/contracts/eventos-m3.md` contenga el contrato acordado.
- [ ] T006 [US3] Green: hacer pasar T005 implementando la migración Alembic y modelo/repositorio `outbox_evento` en `infra/migraciones/versions/`, `backend/app/infraestructura/db/` y `backend/app/infraestructura/repositorios/`; agregar el puerto de aplicación y conectarlo a la unidad de trabajo SQL existente en `backend/app/aplicacion/puertos/` y los casos de uso afectados. Implementar adaptador y despachador RabbitMQ en `backend/app/infraestructura/mensajeria/`, con exchange/mensaje durable, publisher confirms, lease de mensajes, reintento con backoff y `event_id` estable; marcar como publicado solo tras confirm. Añadir `pika==1.3.2` al grupo runtime que ejecuta el publicador y `testcontainers[postgres,rabbitmq]==4.15.0` al grupo de pruebas de `backend/pyproject.toml`; regenerar `backend/uv.lock`. No compartir conexiones Pika entre hilos.
- [ ] T007 [US3] Red→Green de Compose: ampliar primero `backend/tests/e2e/test_persistencia_eventos.py` para que falle si Compose no inicia RabbitMQ/publicador o si no se recibe el evento tras la acción y tras la recuperación del broker; luego conectar `rabbitmq` y el servicio publicador al `infra/docker-compose.yml`, con healthcheck, configuración exclusivamente por entorno y etiquetas fijas, hasta pasar el test. Extender el job existente `integracion-real-m3` de `.github/workflows/ci.yml` para ejecutar T005/T007 y toda la suite requerida en el mismo job; validar migraciones, espera de salud y limpieza aunque falle pytest. Actualizar `specs/001-verificacion-integracion-m3/quickstart.md` con los comandos reales de ejecución.

**Criterio independiente**: rollback no produce mensaje; commit confirmado sobrevive a caída del broker y termina publicado; duplicados comparten `event_id`; PostgreSQL conserva los datos a través del reinicio de API.

## PR 4 — Contratos distribuidos M1, M4, M5 y M6

**Entrega**: artefactos bilaterales versionados y dobles que validan las fronteras acordadas; cualquier cambio incompatible falla en CI.

**Rama**: `001-verificacion-integracion-m3-pr4-contratos-distribuidos`

**Base**: `dev` con PR 3 integrada. Integrar solo con CI verde. La PR queda bloqueada si los módulos propietarios no aprobaron los contratos indicados en T008; no crear esquemas locales para simular ese acuerdo.

- [ ] T008 [US4] Red: agregar `backend/tests/contrato/test_contratos_modulos_vecinos.py` y `backend/tests/contrato/fixtures/` con expectativas mínimas para M1 (emisor/JWKS/claims/roles), M4 (lecturas de conductor, ubicación nullable e IDs), M5 (solicitudes y estados) y M6 (operaciones consumidas, payloads, errores e identidad). Validar que cada documento bilateral fijado en `specs/001-verificacion-integracion-m3/contracts/integraciones-modulos.md` existe, no es solo metadata y contiene las operaciones/esquemas requeridos; demostrar que el test falla con los documentos actuales incompletos o incompatibles. Antes de desbloquear Green, solicitar/fijar con cada grupo propietario la versión exacta de contrato; en particular resolver rutas y UUID vs. entero de M6, discrepancia JWT de M1 y la dirección del evento `TripCompleted`. No inferir nombres, campos ni equivalencias.
- [ ] T009 [US4] Green: una vez aprobados y versionados los contratos, guardar sus copias inmutables/referenciadas en `specs/001-verificacion-integracion-m3/contracts/` y hacer pasar T008 con dobles HTTP/JWKS en `backend/tests/contrato/dobles/`. Validar requests salientes y respuestas de M3/M6 con los esquemas acordados, JWT de M1 con los claims canónicos y contratos M4/M5 para todas las operaciones convenidas. Implementar únicamente los mapeos/adaptadores faltantes en `backend/app/` precedidos por el test de T008; si el acuerdo requiere cambiar un endpoint, actualizar primero `docs/contract/openapi.yaml` según API-first. No cubrir con dobles una frontera que siga sin contrato aprobado.
- [ ] T010 [US4] Green final: integrar `backend/tests/contrato/test_contratos_modulos_vecinos.py` en el job único `integracion-real-m3` de `.github/workflows/ci.yml`, con fallo explícito ante archivos ausentes, incompatibles o pruebas omitidas. Ejecutar la suite de PR 1–4, `ruff check`, `ruff format --check` y cobertura `pytest --cov=app --cov-fail-under=65`; actualizar `specs/001-verificacion-integracion-m3/contracts/integraciones-modulos.md` con referencias/ versiones finales y verificar que no quedan acuerdos implícitos.

**Criterio independiente**: los cuatro dobles validan solo documentos aprobados; una incompatibilidad deliberada del request, response, claim o esquema de evento hace fallar el test específico y el job de CI.

## Dependencias y orden de integración

- **PR 1 / T001 → T002**: el test E2E define el comportamiento; los cambios Compose/API/CI se hacen después del fallo reproducible.
- **PR 2 / T003 → T004**: prueba HTTP simultánea y consulta DB preceden el ajuste de concurrencia. PR 2 parte de `dev` después de integrar PR 1.
- **PR 3 / T005 → T006 → T007**: contrato de eventos y tests de outbox primero; después adaptación SQL/Rabbit; por último stack Compose y prueba de recuperación E2E. PR 3 parte de `dev` después de integrar PR 2.
- **PR 4 / T008 → T009 → T010**: los contratos propietarios aprobados son prerequisito para dobles; luego se habilitan y se conectan al job común. PR 4 parte de `dev` después de integrar PR 3.
- No se paralelizan PRs: cada PR se crea desde `dev` y se integra en `dev` secuencialmente, con CI verde antes de avanzar a la siguiente. Dentro de una tarea pueden repartirse revisión de contratos y preparación de tests en archivos distintos, pero no se integra la implementación antes del Red correspondiente.

## Estrategia de entrega

1. **MVP verificable**: PR 1, flujo de habilitación real con Keycloak y Compose.
2. **Integridad de alta**: PR 2, carrera HTTP respaldada por PostgreSQL real.
3. **Durabilidad**: PR 3, outbox transaccional y RabbitMQ real con recuperación.
4. **Cierre distribuido**: PR 4, contratos reales y dobles fieles, sujeto a aprobación bilateral.

## Validación de formato

- Tareas totales: **10**.
- Distribución: **PR 1 = 2**, **PR 2 = 2**, **PR 3 = 3**, **PR 4 = 3**.
- Cada línea de tarea incluye checkbox, ID secuencial, etiqueta de historia y rutas concretas.
- Cada bloque de implementación indica el test Red previo y la condición Green.

# Tareas: Iteración 2 — Seguridad y plataforma

**Fuentes**: `specs/iteracion2-seguridad/plan.md`, `research.md`, `data-model.md`, `contracts/rate-limiting.md`, `quickstart.md` y el modelo compartido `specs/iteracion2-backend/data-model.md`. Todavía no hay `spec.md` en esta carpeta (pendiente, lo agrega Seguridad); las historias y prioridades se derivan de las áreas, criterios de aceptación y acuerdos de integración del plan.

**Constitución**: No existe `.specify/memory/constitution.md` en este checkout.

**Numeración**: T501–T599, reservada para Datos y seguridad según `specs/iteracion2-seguridad/plan.md`.

**Criterio de pruebas**: Se incluyen tareas de pruebas porque el plan y el quickstart definen explícitamente pruebas de migración, esquema, seed, realm, rate limiting, contrato y CI.

## Historias y orden de entrega

| Fase | Historia | Prioridad | Objetivo | Criterio de prueba independiente |
|---|---|---|---|---|
| 3 | US1 — Esquema y persistencia | P1 | Migrar el esquema 0001 al modelo de Iteración 2 y conservar compatibles ORM y consumidor SQL existente | PostgreSQL verifica los mapeos de estados, restricciones, índices, upgrade/downgrade y compatibilidad del ORM y repositorio |
| 4 | US2 — Datos de prueba | P1 | Proveer datos reproducibles para los escenarios de conductores, solicitudes, vehículos y documentos | Ejecutar el seed dos veces produce los mismos registros y cubre los escenarios requeridos en ambos planes de datos |
| 5 | US3 — Identidad de servicio | P1 | Configurar el rol técnico `servicio` y un usuario conductor vinculado al seed sin credenciales versionadas | El realm importa con variables de entorno; los tokens contienen roles y claims tipados correctos, y la cuenta técnica no puede escribir |
| 6 | US4 — Rate limiting distribuido | P1 | Aplicar cuotas atómicas en Redis con respuestas 429/503 y exclusión de `/salud` | Pruebas API e integración con Redis verifican límites, identidades, expiración, concurrencia, `Retry-After`, fail-closed y salud |
| 7 | US5 — Publicación de imagen | P2 | Publicar solo la imagen M3 después de CI verde en pushes a `dev` o `main` | El workflow no publica en PR, exige CI verde y produce tags SHA y de rama usables por Compose |

US1 se integra antes de los repositorios SQL L9/L10 de Backend. US2 depende del esquema de US1 y US3 necesita el conductor del seed. US4 puede desarrollarse inicialmente en paralelo con US1, pero sus cambios a configuración compartida de Compose y CI se serializan después de US3. US5 modifica esos mismos archivos y se integra después de US4.

## Fase 1: Setup

- [x] T501 Agregar `redis` como dependencia de ejecución al grupo `api` en `backend/pyproject.toml` y regenerar `backend/uv.lock`, sin añadir una dependencia de rate limiting que duplique la lógica propia definida en `specs/iteracion2-seguridad/research.md`.

## Fase 2: Fundacional

- [x] T502 [P] Extender `backend/tests/api/test_configuracion.py` con casos para URL/contraseña Redis y límites por defecto `RATE_LIMIT_ANON_REQUESTS=60`, `RATE_LIMIT_AUTH_REQUESTS=120`, `RATE_LIMIT_WINDOW_SECONDS=60`; comprobar rechazo de valores no enteros o menores o iguales a cero y que los errores no revelen la contraseña.
- [x] T503 Implementar en `backend/app/api/configuracion.py` la lectura de `REDIS_URL`, `REDIS_PASSWORD` y límites del rate limiting con los valores predeterminados indicados; validar enteros positivos al iniciar la configuración y evitar incluir secretos en representaciones o mensajes de error.

## Fase 3: US1 — Esquema y persistencia de Iteración 2

**Meta**: Aplicar una migración reversible desde `0001`, actualizar SQLAlchemy y mantener compatible el repositorio SQL actual mientras el dominio de Backend todavía usa booleanos.

**Prueba independiente**: Con PostgreSQL, ejecutar `pytest backend/tests/infra/test_migraciones.py backend/tests/infra/test_esquema.py backend/tests/integracion/repositorios/test_sql_conductores.py`; verificar mapeos de datos, restricciones, índices y reversibilidad.

- [x] T504 [P] [US1] Extender `backend/tests/infra/test_migraciones.py` para comprobar `0001 -> 0002 -> head`, el mapeo de `conectado=false` a `DESCONECTADO`, `conectado=true AND disponible=true` a `DISPONIBLE` y `conectado=true AND disponible=false` a `CONECTADO`; comprobar también el downgrade `DESCONECTADO -> false/false`, `DISPONIBLE -> true/true` y `CONECTADO u OCUPADO -> true/false`.
- [x] T505 [US1] Crear `infra/migraciones/versions/0002_iteracion2.py` con upgrade/downgrade funcional: migrar el estado antes de quitar `conectado`, `disponible` y su índice; agregar las columnas del conductor y crear `solicitud` y `vehiculo_documento` con claves foráneas, defaults, índices y restricciones de `specs/iteracion2-backend/data-model.md`.
- [x] T506 [P] [US1] Extender `backend/tests/infra/test_esquema.py` para comprobar que el metadata ORM coincide con el esquema migrado, incluyendo estados permitidos, `cantidad_calificaciones >= 0`, `suma_puntajes >= 0`, suma cero cuando la cantidad es cero y las restricciones de solicitud y documento del modelo compartido.
- [x] T507 [US1] Actualizar `backend/app/infraestructura/db/modelos.py` para representar `estado`, los campos nuevos de `conductor`, las tablas `solicitud` y `vehiculo_documento`, sus claves foráneas, índices y restricciones de `specs/iteracion2-backend/data-model.md`; no persistir `puntaje_promedio`.
- [x] T508 [P] [US1] Extender `backend/tests/integracion/repositorios/test_sql_conductores.py` para verificar que el repositorio vigente trabaja contra el esquema 0002 y no consulta ni escribe las columnas retiradas `conectado` y `disponible`.
- [x] T509 [US1] Adaptar `backend/app/infraestructura/repositorios/sql_conductores.py` al modelo ORM de 0002 mapeando directamente `estado` (el dominio ya usa `estado` y los campos nuevos); conservar las consultas/escrituras existentes sin referencias a las columnas eliminadas.

## Fase 4: US2 — Datos de prueba

**Meta**: Extender el seed determinista e idempotente para todos los casos del contrato, sin duplicar ni sustituir datos existentes.

**Prueba independiente**: Ejecutar `pytest backend/tests/infra/test_seed.py` y correr `cargar_datos` dos veces sobre una base migrada; comparar escenarios y registros.

- [x] T510 [P] [US2] Extender `backend/tests/infra/test_seed.py` para exigir conductores en los cuatro estados, casos sin ubicación y sin vehículo activo, con y sin calificaciones, solicitudes en los cuatro estados más una pendiente vigente y otra vencida (medidas contra la hora real), documentos vigentes/vencidos y un conductor `CONECTADO` con vehículo activo `APROBADA` que pueda aceptar las solicitudes pendientes vigentes (escenario pedido en `specs/iteracion2-backend/data-model.md`, «Datos de prueba mínimos»). El usuario conductor vinculado por `id_conductor` y la garantía de que ese id coincide quedan para S2 (T512-T514).
- [x] T511 [US2] Actualizar `infra/seed/cargar_datos.py` para insertar esos escenarios con claves naturales deterministas, relaciones válidas y acumuladores de calificaciones coherentes; garantizar idempotencia al ejecutarlo repetidamente y no agregar escrituras de viajes o calificaciones.

## Fase 5: US3 — Identidad de servicio en Keycloak

**Meta**: Importar un realm con la cuenta técnica M4 de solo lectura y un usuario conductor cuyo claim entero coincida con un conductor del seed.

**Prueba independiente**: Ejecutar `pytest backend/tests/infra/test_realm.py backend/tests/infra/test_keycloak_claim.py` e importar el realm con las variables configuradas; verificar firma, issuer, audiencia y expiración de los tokens.

- [x] T512 [P] [US3] Extender `backend/tests/infra/test_realm.py` y `backend/tests/infra/test_keycloak_claim.py` para verificar rol `servicio`, parametrización de la cuenta técnica, usuario conductor del seed, claim JSON entero `id_conductor` y ausencia de credenciales literales versionadas.
- [x] T513 [US3] Actualizar `infra/keycloak/realm-m3.json` para declarar el rol de realm `servicio`, la cuenta técnica de M4 y el mapper entero `id_conductor` en el token de acceso; leer identidad y credenciales desde placeholders de entorno y no asignar permisos de escritura al usuario técnico.
- [x] T514 [US3] Agregar en `.env.example` los placeholders `M3_SERVICIO_USERNAME` (valor de ejemplo `servicio.m4`) y `M3_SERVICIO_PASSWORD` (vacío) para la cuenta técnica de M4, con el mismo patrón que `M3_OPERADOR_*`; el usuario conductor del seed reutiliza `M3_CONDUCTOR_USERNAME` y `M3_CONDUCTOR_PASSWORD` ya existentes. Testing (T612) y los e2e leen esos nombres exactos; pasar las variables al servicio `keycloak` en `docker-compose.yml` y generarlas en «Preparar variables de entorno» de `.github/workflows/ci.yml`, sin versionar secretos.

## Fase 6: US4 — Rate limiting distribuido con Redis

**Meta**: Aplicar una ventana deslizante de 60 segundos en Redis: 60/min por IP del peer ASGI para requests sin JWT válido y 120/min por `(iss, sub)` para JWT verificado. Exceder la cuota responde 429 con `Retry-After`; Redis inaccesible responde 503 fail-closed; `/salud` queda excluida.

**Prueba independiente**: Ejecutar las pruebas unitarias/API y de integración descritas abajo; verificar límite exacto, exceso, identidades separadas, expiración, concurrencia, rechazo de `sub` inválido, error Redis y disponibilidad de `/salud`.

- [x] T515 [P] [US4] Crear `backend/tests/api/test_rate_limit.py` (los tokens de prueba incluyen `sub` desde Backend V1/T359; no se edita `conftest.py` aquí) con pruebas deterministas del límite exacto, ventana deslizante, claves separadas por identidad/scope, `Retry-After` redondeado hacia arriba, no contabilización de solicitudes denegadas, límites configurables y errores de Redis mediante cliente/reloj falso.
- [x] T516 [US4] Implementar `backend/app/api/rate_limit.py` con sorted set y script Lua atómico usando `TIME` de Redis; eliminar eventos fuera de ventana, agregar solo solicitudes permitidas, asignar TTL y calcular el reintento sin extender la ventana en una denegación.
- [x] T517 [US4] Integrar el limitador como dependencia/middleware propio de `backend/app/api/rate_limit.py` y conectarlo en `backend/app/api/seguridad.py` **después de que Backend integre V1 (T364)**, que reescribe las dependencias de acceso del mismo archivo; el cambio aquí se limita a obtener la identidad verificada y llamar al limitador, sin tocar `ROLES_VALIDOS` ni `Identidad`: verificar firma, issuer y expiración antes de usar claims; usar `(iss, sub)` solo si ambos son texto no vacío, y aplicar cuota por `request.client.host` cuando no haya JWT válido o `sub` válido; no confiar en `X-Forwarded-For` sin proxy confiable configurado.
- [x] T518 [US4] Actualizar `backend/app/api/errores.py` y `backend/tests/api/test_errores.py` para emitir 429 `LIMITE_DE_SOLICITUDES` con `Retry-After` y 503 `SERVICIO_TEMPORALMENTE_NO_DISPONIBLE` ante timeout/falla Redis; mantener el cuerpo común `{"codigo": "...", "mensaje": "..."}` sin detalles internos ni caché de 429.
- [x] T519 [US4] Actualizar el ciclo de vida de `backend/app/api/main.py` para crear y cerrar el cliente Redis sin hacer `PING` obligatorio al iniciar; excluir `/salud` del limitador y permitir que la API arranque aunque Redis no responda, traduciendo errores de solicitudes limitadas a 503.
- [x] T520 [US4] Agregar Redis con versión fijada, contraseña obligatoria, red privada y healthcheck mediante `REDISCLI_AUTH` en `docker-compose.yml`; no publicar puerto ni agregar volumen; documentar `REDIS_URL`, `REDIS_PASSWORD` y límites en `.env.example`, con contraseña vacía y valores de límite por defecto.
- [x] T521 [US4] Actualizar `.github/workflows/ci.yml` para generar aleatoriamente `REDIS_PASSWORD` para el smoke test y esperar Redis saludable; extender `.github/scripts/humo.sh` para comprobar healthcheck, respuesta 429 con `Retry-After`, respuesta 503 al detener Redis y disponibilidad de `/salud` durante esa falla. Esas comprobaciones son el **último paso** del job `entorno`, después de los e2e de Testing: la ráfaga anónima agota el cupo de la IP durante la ventana y detener Redis dejaría el stack en 503.
- [x] T522 [US4] Crear `backend/tests/integracion/test_rate_limit_redis.py` para probar concurrencia, expiración y cuotas compartidas contra Redis real; configurar en `.github/workflows/ci.yml` un Redis aislado para el job `test` y un `REDIS_URL` de integración independiente del smoke test.
- [ ] T523 [US4] Entregar a Testing el texto de las respuestas comunes 429/503 (códigos, cuerpo y `Retry-After`) tal como están en `specs/iteracion2-seguridad/contracts/rate-limiting.md`. **Testing edita** `docs/contract/openapi.yaml` y `backend/tests/contrato/test_openapi_ejemplos.py` en su tarea T617; el contrato **sigue en la versión 1.2.0** (son respuestas transversales, sin rutas ni permisos nuevos). Esta tarea se cierra cuando T617 está integrada.

> Seguimiento de S3: el texto de respuestas quedó documentado en el contrato interno; T523 permanece abierto hasta integrar Testing T617.
- [x] T529 [US4] Configurar los límites de CI para no interferir con otros grupos: en «Preparar variables de entorno» de `.github/workflows/ci.yml` (jobs `entorno` y `test`) fijar `RATE_LIMIT_AUTH_REQUESTS=1000` y dejar `RATE_LIMIT_ANON_REQUESTS=60`; los e2e y las pruebas de concurrencia de Testing usan JWT (cuota por `(iss, sub)`), y las pocas llamadas anónimas no alcanzan 60. Documentar en `quickstart.md` que bajar esos valores en CI rompe a Testing.

## Fase 7: US5 — Publicación de imagen de API en Docker Hub

**Meta**: Publicar solo la imagen M3 de Backend después de CI verde en pushes a `dev` o `main`, nunca en eventos `pull_request`.

**Prueba independiente**: Revisar condiciones y permisos del workflow y verificar que una etiqueta publicada puede seleccionarse en Compose mediante `M3_API_IMAGE`.

- [x] T524 [US5] Parametrizar `image` de `api`, `migraciones` y `seed` en `docker-compose.yml` con `${M3_API_IMAGE:-m3-backend:local}`, conservar el build local desde `backend/Dockerfile` y permitir levantar una imagen descargada sin build.
- [x] T525 [US5] Agregar a `.github/workflows/ci.yml` un job de publicación dependiente de `ci`, limitado a eventos `push` en `dev`/`main`; autenticarse con `DOCKER_USERNAME`/`DOCKER_PASSWORD` (este último contiene un access token de Docker Hub), tomar el destino `usuario/repositorio` del secreto `DOCKER_IMAGE`, publicar solo Backend con tag SHA completo y tag de rama, fijar acciones externas por SHA, usar permisos mínimos y no publicar en PR.
- [x] T526 [US5] Actualizar `DESPLIEGUE.md` (una sola vez, incluyendo `REDIS_*`, límites y las cuentas `M3_SERVICIO_*` que agregan T514 y T520) para documentar configuración de secretos Docker Hub, build local, `docker compose pull` y despliegue por tag SHA usando `M3_API_IMAGE`, sin incluir credenciales en texto plano.

## Fase 8: Pulido y coordinación transversal

- [x] T527 Actualizar `specs/iteracion2-seguridad/quickstart.md` para que preparación de entorno, comandos Compose y resultados esperados coincidan con la configuración Redis, migración, seed, realm, rate limiting, smoke test y publicación de imagen.
- [ ] T528 Ejecutar las validaciones de `specs/iteracion2-seguridad/quickstart.md`, migración/esquema/seed/realm, pruebas de rate limiting y contrato, `docker compose config` y smoke test; confirmar que `/salud` sigue disponible ante una falla Redis y que el workflow nunca publica en `pull_request`.

## Dependencias

```text
Fundacional: T501 -> T502 -> T503

US1: T504 -> T505
     T506 -> T507
     T508 -> T509 (requiere T505 y T507)

US2: T510 -> T511 (requiere US1: T505 y T507)
US3: T512 -> T513 -> T514 (requiere US2: T511 para vincular el usuario al seed)

US4: T515 -> T516 -> T517
     T518 y T519 requieren T517
     T520 requiere T503; se integra después de T514 por cambios compartidos en Compose/env
     T521 requiere T519 y T520
     T522 requiere T516 y T520; serializar cambios al workflow después de T521
     T523 requiere T518 (códigos definidos); se cierra cuando Testing integra T617
     T529 requiere T520 y T521 (mismo ci.yml); el humo del 429 va último en el job `entorno`
     T517 requiere que Backend haya integrado V1 (T364) en `seguridad.py`

US5: T524 requiere T520 (mismo docker-compose.yml)
     T525 requiere T521 y T522 (mismo workflow y CI verde)
     T526 requiere T524 para documentar la referencia de imagen publicada

Pulido: T527 requiere US1–US5; T528 requiere T527

T501–T503 (configuración de Redis) no bloquean a US1–US3: US1 se integra primero para desbloquear a Backend L9/L10.
```

US1 y el desarrollo inicial de US4 son independientes en esquema. Los cambios sobre `.env.example`, `docker-compose.yml` y `.github/workflows/ci.yml` se integran en secuencia para evitar conflictos entre US3, US4 y US5.

## Oportunidades de paralelismo

- **US1**: T504, T506 y T508 modifican archivos de prueba distintos y pueden prepararse en paralelo; T505 y T507 son implementaciones separables, pero T509 espera ambos.
- **US2**: T510 puede escribirse en paralelo con las pruebas de realm T512; T511 espera esquema/modelos de US1 y debe completar el conductor de referencia antes de integrar la cuenta de US3.
- **US3**: T512 puede prepararse en paralelo con T510; T513 requiere T512 y T514 se serializa con las tareas de Redis que modifican Compose/env/CI.
- **US4**: T515 (tests/unitarios) y T523 (contrato/OpenAPI, coordinado con Testing) pueden desarrollarse en paralelo; T516–T519 implementan el flujo API; T520–T522 integran secuencialmente configuración compartida y pruebas de stack.
- **US5**: T526 (documentación de despliegue) puede prepararse en paralelo con T525 cuando la referencia de imagen esté definida; T524 y T525 esperan la estabilización de Compose y CI de US4.

## PRs de implementación (todas contra `dev`, en este orden)

| PR | Tareas | Contenido | Depende de |
|---|---|---|---|
| S1 | T504–T511 | Migración `0002`, modelos, adaptación mínima de `sql_conductores.py` y seed | — (desbloquea Backend L9/L10) |
| S2 | T512–T514 | Rol `servicio`, cuenta M4 y usuario conductor en Keycloak | S1 |
| S3 | T501–T503, T515–T523, T529 | Redis y rate limiting | S2 (Compose/env/CI) y Backend V1 para T517 |
| S4 | T524–T526 | Publicación de la imagen | S3 |
| S5 | T527–T528 | Quickstart y validación integrada | S1–S4 |

Orden de edición sobre `docker-compose.yml`, `.env.example` y `.github/workflows/ci.yml` entre grupos: Seguridad S2 → Testing PR 1 → Seguridad S3 → Testing PR 5 → Seguridad S4. Detalle en `specs/iteracion2-testing/plan.md` («Reparto con Backend y Seguridad»).

## Estrategia de implementación

1. **MVP de persistencia (US1)**: entregar migración reversible, modelos y adaptación del repositorio para habilitar la integración L9/L10 de Backend.
2. **Datos e identidad (US2–US3)**: cargar escenarios deterministas y configurar Keycloak con el conductor seed y el rol técnico de solo lectura.
3. **Seguridad de plataforma (US4)**: implementar límites distribuidos y validar fallos de Redis, respuestas comunes y salud.
4. **Entrega de imagen (US5)**: habilitar publicación de Backend después de estabilizar Compose y CI; usar tag SHA para despliegues reproducibles.
5. **Cierre**: alinear quickstart/contratos y ejecutar la validación integrada.

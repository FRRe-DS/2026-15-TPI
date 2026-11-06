# Tareas: Iteración 2 — Seguridad y plataforma

**Entrada**: Diseño de `specs/iteracion2-seguridad/plan.md`, `research.md`, `data-model.md`, `contracts/rate-limiting.md` y `quickstart.md`. No hay `spec.md` en este feature; las historias y su prioridad se derivan de las áreas, dependencias y criterios de aceptación explícitos del plan vigente.

**Constitución**: No existe `.specify/memory/constitution.md` en este checkout. Las tareas mantienen la organización de las demás iteraciones y sus requisitos de test descritos en el plan.

**Numeración**: T501–T599, reservada para Datos y seguridad según el plan de Iteración 2.

**Organización**: tareas agrupadas por historia verificable. Los tests preceden a la implementación en cada entrega; las pruebas cubren los criterios de aceptación del plan.

## Historias y orden de entrega

| Fase | Historia | Prioridad derivada | Objetivo | Criterio de prueba independiente |
|---|---|---|---|---|
| 3 | US1 — Esquema y persistencia de Iteración 2 | P1 | Migrar el esquema 0001 al modelo 1.2.0 y mantener compatibles ORM y consumidor SQL existente | Sobre PostgreSQL, upgrade/downgrade preservan los estados definidos y ORM, tablas, índices, restricciones y repo SQL coinciden con el modelo acordado |
| 4 | US2 — Datos de prueba | P1 | Sembrar los escenarios requeridos de conductores, solicitudes, vehículos y documentos | Ejecutar el seed dos veces produce el mismo resultado e incluye cada caso enumerado en el plan |
| 5 | US3 — Identidad de servicio en Keycloak | P1 | Emitir rol `servicio` y claim entero `id_conductor` sin secretos en el repositorio | El realm importa con variables configuradas; los tokens de los usuarios de prueba tienen rol/claims esperados y la cuenta de servicio no puede escribir |
| 6 | US4 — Rate limiting distribuido con Redis | P1 | Limitar tráfico anónimo/autenticado con Redis, 429/Retry-After y fail-closed 503 | Pruebas API/integración verifican límites, separación de identidades, expiración, atomicidad, exclusión de `/salud` y falla de Redis |
| 7 | US5 — Imagen de API en Docker Hub | P2 | Publicar la imagen propia de M3 solo tras CI verde en pushes a `dev`/`main` | El job no corre en PR, publica tags SHA y de rama tras CI exitoso y la referencia publicada se puede usar en Compose |

US1 es la primera entrega implementable; US2 depende del esquema de US1. US3 depende de que el conductor referenciado esté en el seed. US4 puede desarrollarse separada de la migración, pero su configuración comparte `.env.example`, Compose y CI con US3. US5 comparte Compose/CI con US4 y se integra después para evitar cambios simultáneos en esos archivos.

## Fase 1: Setup

- [ ] T501 Agregar `redis` como dependencia de ejecución al grupo `api` en `backend/pyproject.toml` y regenerar `backend/uv.lock`, sin agregar una dependencia de rate limiting que duplique la lógica documentada en `specs/iteracion2-seguridad/research.md`.

## Fase 2: Fundacional

- [ ] T502 [P] Agregar a `backend/app/api/configuracion.py` y `backend/tests/api/test_configuracion.py` la configuración requerida para `REDIS_URL`, `REDIS_PASSWORD`, `RATE_LIMIT_ANON_REQUESTS=60`, `RATE_LIMIT_AUTH_REQUESTS=120` y `RATE_LIMIT_WINDOW_SECONDS=60`; rechazar límites o ventanas no enteros o menores o iguales a cero y no exponer la contraseña en representaciones o errores.

## Fase 3: US1 — Esquema y persistencia de Iteración 2

**Meta**: upgrade y downgrade reversibles desde `0001`, modelos ORM compatibles y repositorio actual sin consultas a las columnas retiradas.

**Prueba independiente**: `pytest backend/tests/infra/test_migraciones.py backend/tests/infra/test_esquema.py backend/tests/integracion/repositorios/test_sql_conductores.py`; con PostgreSQL disponible, verificar migración de datos y reversibilidad.

- [ ] T503 [P] [US1] Extender `backend/tests/infra/test_migraciones.py` para comprobar `0001 -> 0002 -> head`, el mapeo `conectado=false -> DESCONECTADO`, `conectado=true AND disponible=true -> DISPONIBLE`, `conectado=true AND disponible=false -> CONECTADO`, y el downgrade `DESCONECTADO -> false/false`, `DISPONIBLE -> true/true`, `CONECTADO u OCUPADO -> true/false`.
- [ ] T504 [US1] Crear `infra/migraciones/versions/0002_iteracion2.py` con upgrade/downgrade reversible y las restricciones de `specs/iteracion2-backend/data-model.md`: `estado` en `DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`; `suma_puntajes` y `cantidad_calificaciones` no negativos y suma cero si cantidad cero; solicitud con estado `PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`, respuesta/hora ambos nulos o ambos con valor y estado igual a respuesta; documento con tipo `SEGURO`, `CEDULA_VERDE` o `VTV` y `fecha_vencimiento > fecha_emision`. Añadir `id_vehiculo_activo`, `fecha_ultimo_cambio_estado`, FK, índices y defaults; quitar las columnas viejas solo después de mapear sus datos.
- [ ] T505 [P] [US1] Extender `backend/tests/infra/test_esquema.py` para comparar el metadata ORM con el esquema 0002 y probar `estado IN ('DESCONECTADO', 'CONECTADO', 'DISPONIBLE', 'OCUPADO')`, `cantidad_calificaciones >= 0`, `suma_puntajes >= 0` y la regla de suma cero cuando la cantidad es cero.
- [ ] T506 [US1] Actualizar `backend/app/infraestructura/db/modelos.py` para representar todas las columnas, tablas, claves foráneas, índices y restricciones de `specs/iteracion2-backend/data-model.md`, incluyendo que `puntaje_promedio` no se persiste.
- [ ] T507 [P] [US1] Extender `backend/tests/integracion/repositorios/test_sql_conductores.py` para probar que el repositorio SQL vigente lee/escribe `estado` usando la migración 0002 y no genera SQL con las columnas `conectado` o `disponible`.
- [ ] T508 [US1] Adaptar `backend/app/infraestructura/repositorios/sql_conductores.py` al esquema 0002 mediante la traducción transitoria acordada para el dominio booleano vigente; conservar las consultas/escrituras existentes y evitar referencias ORM a las columnas eliminadas.

## Fase 4: US2 — Datos de prueba

**Meta**: seed determinista e idempotente para los escenarios de Iteración 2, sin sustituir ni duplicar los datos existentes.

**Prueba independiente**: `pytest backend/tests/infra/test_seed.py`; la prueba de integración ejecuta `cargar_datos` dos veces sobre una base migrada y compara conteos y escenarios.

- [ ] T509 [P] [US2] Extender `backend/tests/infra/test_seed.py` para exigir conductores en `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`; casos sin ubicación y sin vehículo activo; casos con y sin calificaciones; solicitudes `PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA` más pendientes vigente/vencida; documentos de vehículo vigentes/vencidos; y usuario de prueba vinculado al conductor sembrado.
- [ ] T510 [US2] Actualizar `infra/seed/cargar_datos.py` para poblar esos escenarios con claves naturales deterministas, `id_vehiculo_activo` válido cuando corresponda y acumuladores de calificaciones coherentes; ejecutar el seed de forma idempotente sin crear operaciones de escritura de viajes o calificaciones.

## Fase 5: US3 — Identidad de servicio en Keycloak

**Meta**: importar el realm con la cuenta técnica de M4 con rol `servicio` de solo lectura y un usuario conductor cuyo claim entero coincida con el seed.

**Prueba independiente**: `pytest backend/tests/infra/test_realm.py backend/tests/infra/test_keycloak_claim.py`; importar Keycloak desde Compose con variables de prueba y validar que los tokens conserven firma, issuer, audiencia y expiración configurados.

- [ ] T511 [P] [US3] Extender `backend/tests/infra/test_realm.py` y `backend/tests/infra/test_keycloak_claim.py` para comprobar el rol `servicio`, la cuenta técnica parametrizada, el usuario conductor vinculado al seed y el claim JSON entero `id_conductor`; afirmar que no hay credenciales literales versionadas.
- [ ] T512 [US3] Actualizar `infra/keycloak/realm-m3.json` para declarar el rol de realm `servicio`, la cuenta técnica de M4 y el mapeador de `id_conductor` como entero en el token de acceso; leer usuario/credenciales/ID mediante placeholders de entorno y mantener al usuario técnico sin roles de escritura.
- [ ] T513 [US3] Agregar placeholders vacíos para las credenciales e identificador del usuario técnico y conductor en `.env.example`, pasarlos al servicio `keycloak` de `docker-compose.yml` y generarlos en el paso «Preparar variables de entorno» de `.github/workflows/ci.yml`; nunca guardar contraseñas reales en esos archivos.

## Fase 6: US4 — Rate limiting distribuido con Redis

**Meta**: controlar solicitudes con una ventana deslizante de 60 segundos en Redis. Requests sin JWT válido tienen 60/min por IP; JWT verificado con `iss` y `sub` textuales no vacíos tiene 120/min por `(iss, sub)`. Exceder la cuota responde 429 con `Retry-After`; Redis inaccesible responde 503 fail-closed. `/salud` no consume cuota.

**Prueba independiente**: `pytest backend/tests/api/test_rate_limit.py backend/tests/api/test_seguridad.py` y prueba de integración contra Redis real; probar límite exacto, exceso, vencimiento, concurrencia, identidades separadas, anonimato por IP, error Redis y salud.

- [ ] T514 [P] [US4] Crear `backend/tests/api/test_rate_limit.py` con casos que primero fallen para ventana deslizante exacta, claves separadas por scope/identidad, `Retry-After` redondeado hacia arriba, no contar solicitudes rechazadas, error Redis y límites configurables; usar reloj/cliente Redis falso determinista.
- [ ] T515 [US4] Implementar `backend/app/api/rate_limit.py` con sorted set y script Lua atómico usando `TIME` de Redis; retirar eventos anteriores a la ventana, permitir solo si el conteo es menor al límite, asignar TTL a la clave y devolver el tiempo de reintento sin extender la ventana con solicitudes denegadas.
- [ ] T516 [US4] Integrar el limitador en `backend/app/api/seguridad.py` para contar por `request.client.host` cuando falte el JWT o falle su validación, y por `(iss, sub)` solo después de validar firma, issuer y expiración; exigir `sub` texto no vacío y mantener la autenticación y permisos existentes.
- [ ] T517 [US4] Actualizar `backend/app/api/errores.py` y `backend/tests/api/test_errores.py` para responder 429 `LIMITE_DE_SOLICITUDES` con encabezado `Retry-After` y 503 `SERVICIO_TEMPORALMENTE_NO_DISPONIBLE` ante errores/timeout Redis; conservar `{"codigo": "...", "mensaje": "..."}`, no exponer detalles internos y no cachear el 429.
- [ ] T518 [US4] Agregar al ciclo de vida de `backend/app/api/main.py` la creación/cierre del cliente Redis sin hacer `PING` requisito de startup; excluir `/salud` del rate limiting y traducir errores operativos de Redis a 503 sin impedir que la API arranque.
- [ ] T519 [US4] Agregar el servicio Redis con versión fijada, contraseña requerida, red privada y healthcheck mediante `REDISCLI_AUTH` en `docker-compose.yml`; no publicar puerto ni agregar volumen de datos; agregar `REDIS_URL`, `REDIS_PASSWORD` y límites vacíos/por defecto en `.env.example`, y configurar `M3_API_IMAGE` conservando `m3-backend:local` como default de desarrollo.
- [ ] T520 [US4] Actualizar `.github/workflows/ci.yml` para generar aleatoriamente `REDIS_PASSWORD`, pasar límites de prueba acotados al smoke y esperar Redis saludable; extender `.github/scripts/humo.sh` para verificar el healthcheck, respuesta 429 con `Retry-After`, 503 al detener Redis y disponibilidad de `/salud` durante esa falla.
- [ ] T521 [US4] Crear `backend/tests/integracion/test_rate_limit_redis.py` para ejercitar concurrencia y expiración contra Redis real, usando URL externa de prueba y marcador `integration`; configurar el job `test` de `.github/workflows/ci.yml` para proporcionar un Redis aislado y `REDIS_URL` sin reutilizar los datos del smoke.
- [ ] T522 [US4] Agregar respuestas comunes 429 y 503 a `docs/contract/openapi.yaml` y a `backend/tests/contrato/test_openapi_ejemplos.py`, con los códigos y encabezados definidos en `specs/iteracion2-seguridad/contracts/rate-limiting.md`; no agregar rutas ni alterar la matriz de acceso.

## Fase 7: US5 — Publicación de imagen de API en Docker Hub

**Meta**: publicar únicamente la imagen propia de Backend M3 después de CI verde en pushes a `dev`/`main`, sin publicar imágenes en eventos `pull_request`.

**Prueba independiente**: revisar condiciones y permisos del workflow; comprobar que `M3_API_IMAGE` selecciona la imagen publicada y que el tag SHA permite un despliegue reproducible.

- [ ] T523 [US5] Parametrizar `image` de `api`, `migraciones` y `seed` en `docker-compose.yml` con `${M3_API_IMAGE:-m3-backend:local}`, manteniendo el build local desde `backend/Dockerfile` y la opción de levantar la imagen descargada con `--no-build`.
- [ ] T524 [US5] Agregar a `.github/workflows/ci.yml` un job de publicación que dependa de `ci`, se ejecute solo si el evento es `push` y la rama sea `dev` o `main`, use `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` como secretos y `DOCKERHUB_IMAGE` como variable, y publique solo el backend con tag SHA completo y tag de rama; fijar las acciones externas por SHA, no ampliar permisos del token y no publicar en `pull_request`.
- [ ] T525 [US5] Actualizar `DESPLIEGUE.md` para documentar variables/secretos de Docker Hub, build local, `docker compose pull` y despliegue por tag SHA con `M3_API_IMAGE`, sin publicar instrucciones con credenciales en texto plano.

## Fase 8: Pulido y coordinación transversal

- [ ] T526 Verificar y actualizar `specs/iteracion2-seguridad/quickstart.md` para que sus comandos y resultados esperados coincidan con Compose, los checks CI y las pruebas finales de migración, seed, realm, rate limiting y publicación Docker Hub.
- [ ] T527 Revisar `specs/iteracion2-seguridad/plan.md`, `specs/iteracion2-seguridad/data-model.md` y `specs/iteracion2-seguridad/contracts/rate-limiting.md` para eliminar contradicciones de variables, códigos HTTP, límites, identidad, fail-closed y propiedad de archivos entre Seguridad, Backend y Testing.
- [ ] T528 Ejecutar las validaciones de `specs/iteracion2-seguridad/quickstart.md`, la suite `backend` y `docker compose config`; confirmar que migraciones, seed y realm pasan, que `/salud` sigue disponible ante una falla Redis y que CI no publica en PR antes de dar por cerradas las tareas del grupo.

## Dependencias

```text
T501 -> T502

US1: T503 -> T504 -> T505 -> T506
     T507 -> T508 (T504 y T506 deben estar completos)

US2: T509 -> T510 (requiere US1: T504 y T506)
US3: T511 -> T512 -> T513 (requiere US2: T510 para el usuario conductor)

US4: T514 -> T515 -> T516 -> T517 -> T518 -> T519 -> T520 -> T521 -> T522
     T501 y T502 preceden US4; T513 precede las modificaciones compartidas de CI/Compose.

US5: T523 -> T524 -> T525 (requiere T519 y T520 para serializar Compose/CI)

Pulido: T526 -> T527 -> T528 (requiere US1–US5)
```

US1 y el desarrollo de US4 pueden avanzar en paralelo inicialmente; los cambios a `.env.example`, `docker-compose.yml` y `.github/workflows/ci.yml` se integran en secuencia para evitar conflictos. US2 y US3 siguen la dependencia de datos de conductor. US5 integra después del smoke de Redis porque toca los mismos archivos de Compose/CI. No se crea pull request como parte de estas tareas.

## Oportunidades de paralelismo

- Después de T502, T503 (pruebas de migración) y T514 (pruebas unitarias del limitador) pueden prepararse en paralelo, ya que tienen archivos distintos.
- Dentro de US1, T503 y T505 pueden escribirse en paralelo antes de sus implementaciones; T507 puede prepararse en paralelo con ellas, pero T508 espera migración y modelos.
- Dentro de US2/US3, los tests de seed (T509) y tests de realm (T511) pueden diseñarse en paralelo; integrar realm/claim requiere que T510 defina el conductor de referencia.
- En US4, T514 no comparte archivos con US1; luego el código Lua (T515) es separable de la integración FastAPI (T516) solo una vez definidos por T514 sus puertos/contratos. La modificación del workflow y Compose se mantiene serial.
- Las historias US1 y US4 son independientes en esquema; US5 puede preparar documentación separada, pero publicar y modificar Compose espera a la configuración Redis.

## Estrategia de implementación

1. **MVP de persistencia (US1)**: entregar la migración reversible y los modelos compatibles primero; habilita a Backend para integrar L9/L10.
2. **Datos y credenciales de prueba (US2–US3)**: seed reproducible y realm técnico después de que existan el esquema y el conductor estable.
3. **Seguridad de plataforma (US4)**: habilitar Redis distribuido, validar fallos y sincronizar códigos/contrato con Testing.
4. **Entrega de imagen (US5)**: habilitar Docker Hub solo con CI verde y después de estabilizar Compose.
5. **Cierre**: quickstart, despliegue, contratos y suite integrada.

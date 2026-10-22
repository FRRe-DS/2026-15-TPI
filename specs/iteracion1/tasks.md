# Tareas: Iteración 1 — Base de M3 (Conductores y Vehículos)

**Entrada**: Documentos de diseño en `specs/iteracion1/`
**Requisitos previos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Pruebas**: obligatorias en todo el proyecto (constitución, principio I). Cada tarea de implementación va precedida por su tarea de **test que falla primero** (Red → Green → Refactor). Los tests no se modifican para hacerlos pasar. Los archivos de configuración sin lógica de producción (Dockerfile, Compose, `.env.example`, workflow de CI) no llevan test propio: se verifican con la prueba de humo T107.

**Organización**: las tareas se agrupan por **stack de trabajo** (una fase por stack). Dentro de cada stack, cada tarea lleva su historia de usuario (`[US1]`…`[US7]`) cuando corresponde.

## Formato: `- [ ] ID [P] [Stack] [Historia] Descripción con ruta`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin depender de tareas incompletas).
- **[S1]…[S5]**: stack dueño de la tarea (ver abajo).
- **[US1]…[US7]**: historia de [spec.md](./spec.md): US1 conductores, US2 habilitación del conductor, US3 licencia, US4 vehículos, US5 entorno y seguridad, US6 verificación automática, US7 pantalla.
- Las tareas de **test** dicen "Test (Red)"; las de **implementación**, "Impl (Green)" y nombran el test que cumplen.

## Stacks y PRs (todas contra `dev`)

| Stack | Grupo | Fase | PRs sugeridas (una rama cada una) |
|---|---|---|---|
| S1 | Backend: lógica | Fase 1 | `feat/s1-base-dominio` (T001–T013) · `feat/s1-casos-de-uso-conductor` (T014–T025) · `feat/s1-casos-de-uso-vehiculo` (T026–T033) · `feat/s1-repositorios-sql` (T034–T040) |
| S2 | Backend: servidor | Fase 2 | `feat/s2-base-api` (T041–T052) · `feat/s2-endpoints-conductor` (T053–T064) · `feat/s2-endpoints-vehiculo` (T065–T075) |
| S3 | Datos y seguridad | Fase 3 | `feat/s3-esquema` (T076–T083) · `feat/s3-seed-realm-compose` (T084–T089) |
| S4 | Testing y CI | Fase 4 | `test/s4-base-ci` (T090–T093) · `test/s4-contrato-openapi` (T094–T095) · `test/s4-ci` (T096) · `test/s4-fixture-integracion` (T097) · `test/s4-contrato` (T098–T103) · `test/s4-concurrencia-humo` (T104–T108) |
| S5 | Frontend | Fase 5 | `feat/s5-pantalla` (T109–T119) |
| — | Cierre | Fase 6 | Integración, documentación y verificación final (T120–T125) |

## Dependencias entre stacks

Los cinco stacks **arrancan en paralelo** el día uno, cada uno con lo que le entregan los contratos:

| Si trabajás en… | Podés avanzar solo con… | Hasta que llegue… |
|---|---|---|
| S1 (lógica) | repositorios en memoria (T013) | S3 (modelos) y S4 (fixture T097) para los repositorios SQL (T034–T039) |
| S2 (servidor) | casos de uso simulados y tokens de prueba (T042) | S1 (casos de uso reales) y S3 (sesión) para el cableado final (T074) |
| S3 (datos) | `data-model.md` | — |
| S4 (testing) | OpenAPI y `ruff`/cobertura (T091–T093); luego migraciones de S3 para la fixture (T097) | S1, S2 y S3 integrados para que pasen los tests de contrato y concurrencia |
| S5 (front) | `fetch` simulado y la forma de `ConductorConUbicacion` del OpenAPI | S2 y S3 para la verificación manual (T119) |

**Puntos de sincronización**: `docs/contract/openapi.yaml` · [data-model.md](./data-model.md) · [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) · [contracts/token-jwt.md](./contracts/token-jwt.md) · [contracts/errores.md](./contracts/errores.md).

**Orden de merge sugerido**: `feat/s1-base-dominio` primero (crea `pyproject.toml`); después el resto en cualquier orden, con estas excepciones: `feat/s1-repositorios-sql`, `test/s4-fixture-integracion` y `test/s4-contrato` después de `feat/s3-esquema` (`test/s4-contrato` además después de S1 y S2); `feat/s2-endpoints-vehiculo` (T074) después de `feat/s1-repositorios-sql`. `test/s4-contrato-openapi` (cambia el contrato) se mergea temprano y se avisa a todos.

**Dueños de archivos**: ver la tabla de [plan.md](./plan.md). Cada tarea toca solo archivos de su stack, salvo las que lo aclaran.

---

## Fase 1: Stack 1 — Lógica del backend

**Meta**: dominio, casos de uso y repositorios de los 10 endpoints, con TDD y sin depender de FastAPI ni de la base.

### PR `feat/s1-base-dominio`

- [X] T001 [S1] Crear `backend/pyproject.toml` (paquete `app`, `requires-python = ">=3.12,<3.13"`) con grupos de dependencias separados por stack: `dev` (S1: pytest, pytest-cov, ruff), `api` (S2), `db` (S3) y `test` (S4), los tres últimos vacíos. Versiones según [research.md](./research.md)
- [X] T002 [S1] Generar `backend/uv.lock` con `uv lock` y verificar `uv sync --group dev`
- [X] T003 [P] [S1] Crear los paquetes vacíos con `__init__.py`: `backend/app/__init__.py`, `backend/app/dominio/`, `backend/app/aplicacion/casos_de_uso/`, `backend/app/aplicacion/puertos/`, `backend/app/infraestructura/repositorios/` y `backend/tests/unitarios/`
- [X] T004 [S1] [US1] Test (Red) `backend/tests/unitarios/dominio/test_conductor.py`: DNI válido de 7 u 8 dígitos (`^[0-9]{7,8}$`) y rechazo de `"1234567a"`, 6 y 9 dígitos; `nombre`, `apellido` y `telefono` obligatorios; email con formato válido; un conductor nuevo queda con habilitación `PENDIENTE`, `conectado` falso y `disponible` falso
- [X] T005 [S1] [US1] Impl (Green) `backend/app/dominio/errores.py` (`NoEncontrado`, `DniDuplicado`, `PatenteDuplicada`, `TransicionInvalida`, `LicenciaVigenteRequerida`, `DatosInvalidos`) y `backend/app/dominio/conductor.py` (entidad y creación) hasta que pase T004
- [X] T006 [S1] [US2] Test (Red) `backend/tests/unitarios/dominio/test_habilitacion.py`: todas las transiciones de la matriz (`PENDIENTE` → `APROBADA`/`OBSERVADA`/`RECHAZADA`; `OBSERVADA` → `APROBADA`/`RECHAZADA`; `APROBADA` → `SUSPENDIDA`; `SUSPENDIDA` → `APROBADA`/`RECHAZADA`; `RECHAZADA` final), rechazo de cada combinación no listada con `TransicionInvalida`, `motivo` obligatorio y no vacío (`DatosInvalidos`), y evento con `estado_anterior`, `estado_nuevo`, `motivo`, `id_operador` y `fecha`
- [X] T007 [S1] [US2] Impl (Green) `backend/app/dominio/habilitacion.py`: enums `EstadoHabilitacion` y `AccionHabilitacion` (`ALTA`, `APROBAR`, `OBSERVAR`, `SUSPENDER`, `RECHAZAR`), tabla de transiciones y `aplicar_accion(...)` que devuelve el evento, hasta que pase T006
- [X] T008 [S1] [US3] Test (Red) `backend/tests/unitarios/dominio/test_documento.py`: estado `VIGENTE` si `fecha_vencimiento` es igual o posterior a hoy y `VENCIDO` si es anterior (con reloj fijo); `fecha_vencimiento` posterior a `fecha_emision`; `tipo` `LICENCIA`; `url_archivo` con URI válida; `numero` obligatorio y `categoria` opcional
- [X] T009 [S1] [US3] Impl (Green) `backend/app/dominio/documento.py` hasta que pase T008
- [X] T010 [S1] [US4] Test (Red) `backend/tests/unitarios/dominio/test_vehiculo.py`: `tipo` `AUTO` o `MOTO`; al menos un tipo de servicio (`PASAJEROS`/`ENVIOS`) sin repetidos; el vehículo inicia en `PENDIENTE` con todos sus tipos de servicio con `habilitado` falso; `patente`, `marca`, `modelo` obligatorios y `anio` entero
- [X] T011 [S1] [US4] Impl (Green) `backend/app/dominio/vehiculo.py` hasta que pase T010
- [X] T012 [P] [S1] Crear los puertos de [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) como clases abstractas, sin lógica: `backend/app/aplicacion/puertos/` con `repositorio_conductores.py`, `repositorio_vehiculos.py`, `repositorio_documentos.py`, `repositorio_habilitaciones.py`, `unidad_de_trabajo.py` y `reloj.py`
- [X] T013 [S1] Test + Impl `backend/tests/unitarios/fakes/` (`repositorios_en_memoria.py`, `reloj_fijo.py`, `test_fakes.py`): repositorios en memoria que implementan los puertos y lanzan `DniDuplicado` y `PatenteDuplicada` igual que lo hará la base; el test se escribe primero

### PR `feat/s1-casos-de-uso-conductor`

- [X] T014 [S1] [US1] Test (Red) `backend/tests/unitarios/aplicacion/test_crear_conductor.py`: crea con habilitación `PENDIENTE` y evento `ALTA` (`estado_anterior` nulo, `id_operador` nulo); `DniDuplicado` si el DNI ya existe; `DatosInvalidos` con datos inválidos
- [X] T015 [S1] [US1] Impl (Green) `backend/app/aplicacion/casos_de_uso/crear_conductor.py` hasta que pase T014
- [X] T016 [S1] [US1] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_conductores.py`: sin filtros devuelve todos; `habilitado=true` solo con habilitación `APROBADA` y `habilitado=false` con cualquier otro estado; `disponible`; `tipo_vehiculo` (al menos un vehículo de ese tipo); filtros combinados; lista vacía sin error
- [X] T017 [S1] [US1] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_conductores.py` hasta que pase T016
- [X] T018 [S1] [US1] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_conductor.py`: devuelve el conductor con sus documentos (estado calculado) y vehículos resumidos; `NoEncontrado` si no existe
- [X] T019 [S1] [US1] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_conductor.py` hasta que pase T018
- [X] T020 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_consultar_habilitacion_conductor.py`: devuelve estado actual e historial en orden cronológico; `NoEncontrado`
- [X] T021 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/consultar_habilitacion_conductor.py` hasta que pase T020
- [X] T022 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_accionar_habilitacion_conductor.py`: `APROBAR` con licencia `VIGENTE` pasa a `APROBADA` y guarda el evento con el `id_operador`; `APROBAR` sin licencia o con licencia `VENCIDO` lanza `LicenciaVigenteRequerida` y el estado no cambia; transición no permitida lanza `TransicionInvalida`; `SUSPENDER` y luego `APROBAR` son válidos y quedan en el historial; `NoEncontrado`; se pide el bloqueo de fila a la unidad de trabajo
- [X] T023 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/accionar_habilitacion_conductor.py` hasta que pase T022
- [ ] T024 [S1] [US3] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_licencia.py`: guarda la licencia y devuelve el estado calculado `VIGENTE` o `VENCIDO`; `NoEncontrado` si el conductor no existe; `DatosInvalidos` si el vencimiento no es posterior a la emisión
- [ ] T025 [S1] [US3] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_licencia.py` hasta que pase T024

### PR `feat/s1-casos-de-uso-vehiculo`

- [ ] T026 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_vehiculo.py`: crea en `PENDIENTE` con tipos de servicio sin habilitar y evento `ALTA`; `PatenteDuplicada`; `NoEncontrado` si el conductor no existe; `DatosInvalidos` sin tipos de servicio
- [ ] T027 [S1] [US4] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_vehiculo.py` hasta que pase T026
- [ ] T028 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_vehiculos.py`: solo los del conductor; filtros `tipo` y `habilitacion`; `NoEncontrado` si el conductor no existe
- [ ] T029 [S1] [US4] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_vehiculos.py` hasta que pase T028
- [ ] T030 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_vehiculo.py`: devuelve el vehículo con `documentos` vacío; un vehículo de otro conductor lanza `NoEncontrado`
- [ ] T031 [S1] [US4] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_vehiculo.py` hasta que pase T030
- [ ] T032 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_accionar_habilitacion_vehiculo.py`: matriz de transiciones del vehículo; sin regla de licencia; vehículo de otro conductor lanza `NoEncontrado`; guarda el evento con el `id_operador`
- [ ] T033 [S1] [US4] Impl (Green) `backend/app/aplicacion/casos_de_uso/accionar_habilitacion_vehiculo.py` hasta que pase T032

### PR `feat/s1-repositorios-sql`

> **Depende de**: S3 (T081 modelos y T083 migración) y S4 (T097 fixture de Testcontainers).

- [ ] T034 [S1] [US1] Test (Red) `backend/tests/integracion/repositorios/test_sql_conductores.py` con Testcontainers: guardar y buscar; el error de unicidad de DNI se traduce a `DniDuplicado`; filtros del listado; vehículos y documentos cargados en consultas agrupadas (sin una consulta por fila)
- [ ] T035 [S1] [US1] Impl (Green) `backend/app/infraestructura/repositorios/sql_conductores.py` hasta que pase T034
- [ ] T036 [S1] [US4] Test (Red) `backend/tests/integracion/repositorios/test_sql_vehiculos.py`: guardar con tipos de servicio; el error de unicidad de patente se traduce a `PatenteDuplicada`; listar por conductor con filtros
- [ ] T037 [S1] [US4] Impl (Green) `backend/app/infraestructura/repositorios/sql_vehiculos.py` hasta que pase T036
- [ ] T038 [S1] [US2] Test (Red) `backend/tests/integracion/repositorios/test_sql_habilitaciones.py`: los eventos son de solo escritura y el historial vuelve en orden; el estado y el evento se guardan en la misma transacción; la unidad de trabajo bloquea la fila (`SELECT ... FOR UPDATE`); licencias guardadas y consultadas
- [ ] T039 [S1] [US2] Impl (Green) `backend/app/infraestructura/repositorios/sql_documentos.py`, `sql_habilitaciones.py` y `sql_unidad_de_trabajo.py` hasta que pase T038
- [ ] T040 [S1] Refactor con la suite en verde: pasar `ruff`, aplicar la skill `clean-code` a `backend/app/dominio/` y `backend/app/aplicacion/`, y verificar con `uv run pytest backend/tests/unitarios --cov=app`

---

## Fase 2: Stack 2 — Servidor HTTP

**Meta**: exponer los 10 endpoints con FastAPI conforme al contrato, validando el JWT de Keycloak. Se trabaja con casos de uso simulados hasta que S1 y S3 integren.

### PR `feat/s2-base-api`

- [ ] T041 [S2] Agregar al grupo `api` de `backend/pyproject.toml` (solo ese grupo): fastapi, uvicorn, pydantic-settings y pyjwt con extra `crypto`, con las versiones de [research.md](./research.md); regenerar `backend/uv.lock`
- [ ] T042 [S2] Crear `backend/tests/api/conftest.py`: genera una clave RSA de prueba, expone su JWKS, ofrece `crear_token(roles, id_operador, exp, iss)` y un cliente de pruebas con los casos de uso reemplazados por simulados (según [contracts/token-jwt.md](./contracts/token-jwt.md))
- [ ] T043 [P] [S2] Test (Red) `backend/tests/api/test_configuracion.py`: la configuración lee `KEYCLOAK_URL`, `KEYCLOAK_REALM` y `DATABASE_URL` del entorno y falla con un mensaje claro si falta alguna
- [ ] T044 [S2] Impl (Green) `backend/app/api/__init__.py` y `backend/app/api/configuracion.py` con pydantic-settings hasta que pase T043
- [ ] T045 [S2] [US5] Test (Red) `backend/tests/api/test_seguridad.py`: `401` sin encabezado, token malformado, firma inválida, vencido o de otro emisor; `200` con rol `conductor` u `operador` en endpoints comunes; `403` en una acción de habilitación sin rol `operador`; `403` si el operador no trae `id_operador` numérico
- [ ] T046 [S2] [US5] Impl (Green) `backend/app/api/seguridad.py`: validación local con PyJWT y JWKS con caché, y dependencias `requerir_usuario` y `requerir_operador`, hasta que pase T045
- [ ] T047 [S2] Test (Red) `backend/tests/api/test_errores.py`: cada error de dominio responde el HTTP y el `{codigo, mensaje}` de [contracts/errores.md](./contracts/errores.md); validación de forma → `400` `SOLICITUD_INVALIDA`; excepción inesperada → `500` `ERROR_INTERNO` sin detalles internos
- [ ] T048 [S2] Impl (Green) `backend/app/api/errores.py` con los manejadores de excepciones hasta que pase T047
- [ ] T049 [P] [S2] Test (Red) `backend/tests/api/test_esquemas.py`: restricciones de entrada del OpenAPI, entre ellas DNI `^[0-9]{7,8}$`, email válido, `motivo` con `minLength: 1`, `tipos_serv` con `minItems: 1` y `uniqueItems`, fechas en formato `date` y `url_archivo` con formato `uri`
- [ ] T050 [S2] Impl (Green) `backend/app/api/esquemas/{conductor,vehiculo,documento,habilitacion,error}.py` con los nombres del OpenAPI hasta que pase T049
- [ ] T051 [S2] Test (Red) `backend/tests/api/test_main.py`: todas las rutas cuelgan de `/api/v1` y requieren autenticación
- [ ] T052 [S2] Impl (Green) `backend/app/api/main.py` con `crear_app()`, prefijo `/api/v1`, manejadores y seguridad, hasta que pase T051

### PR `feat/s2-endpoints-conductor`

- [ ] T053 [S2] [US1] Test (Red) `backend/tests/api/test_conductores_crear.py`: `POST /conductores` → `201` con encabezado `Location` y cuerpo `Conductor`; `400` por DNI inválido; `409` `DNI_DUPLICADO`; `401` sin token
- [ ] T054 [S2] [US1] Impl (Green) `backend/app/api/routers/conductores.py` (crear) hasta que pase T053
- [ ] T055 [S2] [US1] Test (Red) `backend/tests/api/test_conductores_listar.py`: `GET /conductores` con `habilitado`, `disponible` y `tipo_vehiculo`; `400` ante un valor inválido; los parámetros `latitud` y `longitud` se aceptan y se ignoran (no filtran ni ordenan, quedan para la Iteración 2)
- [ ] T056 [S2] [US1] Impl (Green) listar en `backend/app/api/routers/conductores.py` hasta que pase T055
- [ ] T057 [S2] [US1] Test (Red) `backend/tests/api/test_conductores_obtener.py`: `GET /conductores/{id_conductor}` → `200` y `404` `NO_ENCONTRADO`
- [ ] T058 [S2] [US1] Impl (Green) obtener en `backend/app/api/routers/conductores.py` hasta que pase T057
- [ ] T059 [S2] [US2] Test (Red) `backend/tests/api/test_habilitacion_consultar.py`: `GET /conductores/{id_conductor}/habilitacion` → `200` con `HabilitacionResumen` y `404`
- [ ] T060 [S2] [US2] Impl (Green) `backend/app/api/routers/habilitacion.py` (consultar) hasta que pase T059
- [ ] T061 [S2] [US2] Test (Red) `backend/tests/api/test_habilitacion_accionar.py`: `POST /conductores/{id_conductor}/habilitacion` → `200` con `HabilitacionEventos`; pasa al caso de uso el `id_operador` del token; `403` sin rol `operador`; `400` con `motivo` vacío; `404`; `409` `TRANSICION_INVALIDA`; `422` `LICENCIA_VIGENTE_REQUERIDA`
- [ ] T062 [S2] [US2] Impl (Green) accionar en `backend/app/api/routers/habilitacion.py` hasta que pase T061
- [ ] T063 [S2] [US3] Test (Red) `backend/tests/api/test_documentacion_licencia.py`: `POST /conductores/{id_conductor}/documentacion` → `201` con estado `VIGENTE` o `VENCIDO`; `400` por URL o fechas inválidas; `404`; `422` `DATOS_INVALIDOS`
- [ ] T064 [S2] [US3] Impl (Green) `backend/app/api/routers/documentacion.py` hasta que pase T063

### PR `feat/s2-endpoints-vehiculo`

- [ ] T065 [S2] [US4] Test (Red) `backend/tests/api/test_vehiculos_crear.py`: `POST /conductores/{id_conductor}/vehiculos` → `201`; `400` sin tipos de servicio; `404`; `409` `PATENTE_DUPLICADA`
- [ ] T066 [S2] [US4] Impl (Green) `backend/app/api/routers/vehiculos.py` (crear) hasta que pase T065
- [ ] T067 [S2] [US4] Test (Red) `backend/tests/api/test_vehiculos_listar.py`: `GET /conductores/{id_conductor}/vehiculos` con filtros `tipo` y `habilitacion`; `404`
- [ ] T068 [S2] [US4] Impl (Green) listar en `backend/app/api/routers/vehiculos.py` hasta que pase T067
- [ ] T069 [S2] [US4] Test (Red) `backend/tests/api/test_vehiculos_obtener.py`: `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}` → `200` y `404` (también si el vehículo es de otro conductor)
- [ ] T070 [S2] [US4] Impl (Green) obtener en `backend/app/api/routers/vehiculos.py` hasta que pase T069
- [ ] T071 [S2] [US4] Test (Red) `backend/tests/api/test_vehiculos_habilitacion.py`: `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion` → `200` con `HabilitacionVehiculoEventos`; `403` sin rol `operador`; `409`; `404`
- [ ] T072 [S2] [US4] Impl (Green) `backend/app/api/routers/vehiculos_habilitacion.py` hasta que pase T071
- [ ] T073 [S2] Test (Red) `backend/tests/api/test_paridad_rutas.py`: el `openapi.json` que genera FastAPI contiene exactamente los 10 pares ruta y método del alcance, con los mismos `operationId` de `docs/contract/openapi.yaml`
- [ ] T074 [S2] Impl (Green) `backend/app/api/dependencias.py`: cableado de los casos de uso con los repositorios SQL y la sesión. **Depende de** S1 (T035, T037, T039) y S3 (T081). Verificar con T073
- [ ] T075 [S2] Crear `backend/Dockerfile` con imagen base `python:3.12` de versión fija (nunca `latest`), `uv sync --frozen --no-dev --group api --group db` (las dependencias de ejecución viven en esos grupos), usuario sin privilegios y `uvicorn app.api.main:app --host 0.0.0.0 --port 8080`

---

## Fase 3: Stack 3 — Datos y seguridad

**Meta**: base de datos propia de M3, Keycloak con roles y usuarios de prueba, y un Compose que levanta todo con un comando. Sus tests viven en `backend/tests/infra/`.

### PR `feat/s3-esquema`

- [ ] T076 [S3] Agregar al grupo `db` de `backend/pyproject.toml` (solo ese grupo): sqlalchemy, alembic y psycopg con las versiones de [research.md](./research.md); regenerar `backend/uv.lock`
- [ ] T077 [P] [S3] Crear `infra/.env.example` con todas las variables (puertos, nombres de bases y usuarios, claves del realm, usuarios de prueba) sin valores reales
- [ ] T078 [S3] [US5] Test (Red) `backend/tests/infra/test_init_postgres.py` (con `conftest.py` propio y Testcontainers): existen las bases `m3` y `keycloak`, y el usuario de `m3` no puede conectarse a la base de `keycloak` (RNF-05)
- [ ] T079 [S3] [US5] Impl (Green) `infra/postgres/init/01-crear-bases.sh`: crea las dos bases con usuarios distintos, con contraseñas tomadas de variables de entorno, hasta que pase T078
- [ ] T080 [S3] [US1] Test (Red) `backend/tests/infra/test_esquema.py`: existen `conductor`, `vehiculo`, `vehiculo_tipo_servicio`, `documento_conductor`, `habilitacion_evento_conductor` y `habilitacion_evento_vehiculo`; `conductor.dni` único; `vehiculo.patente` única; restricciones `CHECK` en los estados de habilitación (`PENDIENTE`, `OBSERVADA`, `APROBADA`, `SUSPENDIDA`, `RECHAZADA`), `tipo` (`AUTO`/`MOTO`), tipos de servicio (`PASAJEROS`/`ENVIOS`) y `accion`; claves foráneas; `habilitacion` inicial `PENDIENTE`; `conectado` y `disponible` por defecto falsos
- [ ] T081 [S3] [US1] Impl (Green) `backend/app/infraestructura/db/__init__.py`, `modelos.py` y `sesion.py` (modelos SQLAlchemy según [data-model.md](./data-model.md); sesión por `DATABASE_URL`) hasta que pase T080
- [ ] T082 [S3] [US1] Test (Red) `backend/tests/infra/test_migraciones.py`: `alembic upgrade head` crea el esquema de T080 y `alembic downgrade base` lo elimina
- [ ] T083 [S3] [US1] Impl (Green) `infra/migraciones/alembic.ini`, `env.py` y `versions/0001_esquema_inicial.py` hasta que pase T082

### PR `feat/s3-seed-realm-compose`

- [ ] T084 [S3] [US5] Test (Red) `backend/tests/infra/test_seed.py`: el seed es idempotente (correrlo dos veces no duplica); carga conductores en distintos estados de habilitación, al menos uno con licencia `VIGENTE` y otro con licencia `VENCIDO`, al menos uno con `conectado` y `disponible` verdaderos (para probar el filtro `disponible`), al menos un vehículo, y un evento `ALTA` por cada entidad
- [ ] T085 [S3] [US5] Impl (Green) `infra/seed/cargar_datos.py` determinista hasta que pase T084
- [ ] T086 [S3] [US5] Test (Red) `backend/tests/infra/test_realm.py`: el JSON es válido; realm `m3`; roles `operador` y `conductor`; usuario operador con atributo numérico `id_operador` y mapeador que lo incluye como claim entero; cliente confidencial con concesión de contraseña habilitada; ningún secreto ni contraseña literal (solo `${VARIABLE}`)
- [ ] T087 [S3] [US5] Impl (Green) `infra/keycloak/realm-m3.json` con sustitución de variables de entorno hasta que pase T086
- [ ] T088 [S3] [US5] Impl `infra/docker-compose.yml`: `postgres` (versión fija de [research.md](./research.md)), `keycloak` (26.8.1, importa el realm), `migraciones` y `seed` (una sola vez) y `api` (usa `backend/Dockerfile` de S2); puertos 5432, 8081 y 8080; chequeos de salud y `depends_on` con condición; sin `latest`. Lo valida la prueba de humo T107
- [ ] T089 [S3] [US5] Agregar a `README.md` la sección "Arranque rápido" con los comandos de [quickstart.md](./quickstart.md), sin duplicar su contenido

---

## Fase 4: Stack 4 — Testing y CI

**Meta**: verificación automática en cada PR y los tests que ningún otro stack cubre: contrato, concurrencia y entorno completo. S4 es también dueño de `docs/contract/openapi.yaml` (pulido y ejemplos).

### PR `test/s4-base-ci`

- [ ] T090 [S4] Agregar al grupo `test` de `backend/pyproject.toml` (solo ese grupo): testcontainers, openapi-core, httpx y un validador de especificaciones OpenAPI, con las versiones de [research.md](./research.md); regenerar `backend/uv.lock`
- [ ] T091 [P] [S4] Crear `backend/ruff.toml` (lint y formato, Python 3.12)
- [ ] T092 [P] [S4] Crear `backend/.coveragerc` con `source = app`, ramas activadas y `fail_under = 65`
- [ ] T093 [P] [S4] [US6] Test (Red) `backend/tests/contrato/test_openapi_valido.py`: `docs/contract/openapi.yaml` es una especificación válida y define las 10 operaciones del alcance con sus respuestas `401`, `403` y de error

### PR `test/s4-contrato-openapi`

- [ ] T094 [S4] [US6] Test (Red) `backend/tests/contrato/test_openapi_ejemplos.py`: cada cuerpo de petición y cada respuesta `2xx` de las 10 operaciones del alcance tiene al menos un `example`; cada respuesta de error (`400`, `401`, `403`, `404`, `409`, `422`) declarada en esas operaciones tiene un ejemplo `{codigo, mensaje}` con un código del catálogo de [contracts/errores.md](./contracts/errores.md); rutas y nombres consistentes (plural, sin tildes ni espacios)
- [ ] T095 [S4] [US6] Impl (Green) `docs/contract/openapi.yaml`: agregar los ejemplos y corregir las inconsistencias que marque T094, solo en las 10 operaciones del alcance (no se tocan las de la Iteración 2 ni las de M6). Es un punto de sincronización: va en su propia PR y se avisa a S1, S2 y S5 antes de mergear

### PR `test/s4-ci`

- [ ] T096 [S4] [US6] Crear `.github/workflows/ci.yml` que corre en cada PR: `ruff check` y `ruff format --check`; pruebas unitarias y de API con `--cov-fail-under=65`; integración, contrato y concurrencia con Docker; validación de `openapi.yaml`; y, si existe `frontend/package.json`, lint y pruebas del frontend

### PR `test/s4-fixture-integracion`

> **Depende de** S3 (T083). Desbloquea a S1 (T034).

- [ ] T097 [S4] [US6] Impl `backend/tests/integracion/conftest.py` con Testcontainers: PostgreSQL con la misma imagen y versión que el Compose, migraciones de Alembic aplicadas y sesiones por prueba, más `test_conftest.py` de verificación. **Depende de** S3 (T083)

### PR `test/s4-contrato`

> **Depende de** S1, S2 y S3 integrados.

- [ ] T098 [S4] [US6] Impl `backend/tests/contrato/conftest.py`: la aplicación real con repositorios SQL sobre el contenedor, tokens de prueba firmados y un validador de openapi-core. **Depende de** T097, S1, S2 y S3
- [ ] T099 [S4] [US1] Test `backend/tests/contrato/test_contrato_conductores.py`: las respuestas de los tres endpoints de conductores cumplen el contrato
- [ ] T100 [S4] [US2] Test `backend/tests/contrato/test_contrato_habilitacion.py`: consulta y acción de habilitación del conductor
- [ ] T101 [S4] [US3] Test `backend/tests/contrato/test_contrato_licencia.py`: registro de licencia
- [ ] T102 [S4] [US4] Test `backend/tests/contrato/test_contrato_vehiculos.py`: alta, listado, detalle y habilitación del vehículo
- [ ] T103 [S4] [US6] Test `backend/tests/contrato/test_contrato_errores.py`: `401`, `403`, `404`, `409` y `422` tienen el formato `{codigo, mensaje}`

> Los tests T099–T103 pueden fallar hasta que S1, S2 y S3 integren; es lo esperado en su fase Red. No se marcan como `xfail`.

### PR `test/s4-concurrencia-humo`

- [ ] T104 [S4] [US1] Test `backend/tests/integracion/concurrencia/test_dni_concurrente.py`: 20 solicitudes simultáneas con el mismo DNI producen exactamente un `201` y 19 `409` (SC-005)
- [ ] T105 [S4] [US4] Test `backend/tests/integracion/concurrencia/test_patente_concurrente.py`: lo mismo con la patente
- [ ] T106 [S4] [US2] Test `backend/tests/integracion/concurrencia/test_habilitacion_concurrente.py`: dos acciones simultáneas sobre el mismo conductor; una se aplica, la otra recibe `409` y el historial queda con un solo evento nuevo
- [ ] T107 [S4] [US5] Crear `.github/scripts/humo.sh` y el job `entorno` en `.github/workflows/ci.yml`: levanta el Compose, pide un token de operador a Keycloak, verifica `GET /api/v1/conductores` → `200` con al menos un conductor y `401` sin token
- [ ] T108 [S4] **Acción manual del responsable del repositorio** (sin esto SC-004 no se garantiza; conviene hacerla apenas exista el workflow T096, antes de abrir las PRs de implementación): configurar la protección de las ramas `dev` y `main` exigiendo el chequeo `ci` en verde antes de mergear

---

## Fase 5: Stack 5 — Frontend

**Meta**: una pantalla que lista los conductores. Con TDD (Vitest), usando `fetch` simulado hasta que la API esté disponible.

### PR `feat/s5-pantalla`

- [ ] T109 [S5] [US7] Inicializar `frontend/` con `package.json` (Next.js 16.4, React y React DOM 19.3, TypeScript 5.9, versiones exactas), `.nvmrc` con Node 24, `tsconfig.json`, ESLint y `vitest.config.ts` con Testing Library, y los scripts `dev`, `build`, `lint` y `test`
- [ ] T110 [P] [S5] [US7] Crear `frontend/.env.example` con `API_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `TEST_USER` y `TEST_PASSWORD`, sin valores reales
- [ ] T111 [S5] [US7] Test (Red) `frontend/src/lib/token.test.ts`: pide el token a `/realms/m3/protocol/openid-connect/token` con concesión de contraseña, lo reutiliza hasta su vencimiento y lanza `ErrorAutenticacion` si Keycloak responde error
- [ ] T112 [S5] [US7] Impl (Green) `frontend/src/lib/token.ts` hasta que pase T111
- [ ] T113 [S5] [US7] Test (Red) `frontend/src/lib/api.test.ts`: `listarConductores` envía `Authorization: Bearer`, llama a `GET {API_URL}/conductores`, devuelve el listado y lanza `ErrorApi` ante `401` o `500`
- [ ] T114 [S5] [US7] Impl (Green) `frontend/src/lib/api.ts` y `frontend/src/lib/tipos.ts` (forma de `ConductorConUbicacion` según `docs/contract/openapi.yaml`) hasta que pase T113
- [ ] T115 [S5] [US7] Test (Red) `frontend/src/components/ListadoConductores.test.tsx`: muestra nombre, apellido, DNI y habilitación; estado vacío "No hay conductores"; estado de error con mensaje claro
- [ ] T116 [S5] [US7] Impl (Green) `frontend/src/components/ListadoConductores.tsx` hasta que pase T115
- [ ] T117 [S5] [US7] Test (Red) `frontend/src/app/page.test.tsx`: la pantalla obtiene los datos en el servidor y renderiza el listado; si la API falla, muestra el estado de error sin romper
- [ ] T118 [S5] [US7] Impl (Green) `frontend/src/app/page.tsx` como componente de servidor (las credenciales nunca llegan al navegador) hasta que pase T117
- [ ] T119 [S5] [US7] Agregar `frontend/README.md` breve (instalar, configurar `.env`, `npm run dev`) y verificar a mano contra la API real con el entorno levantado

---

## Fase 6: Cierre (integración y verificación)

**Meta**: integrar los cinco stacks en `dev`, completar la documentación y comprobar los criterios de éxito.

- [ ] T120 Redactar `docs/justificacion-stack.md` (RNF-01): por qué FastAPI, PostgreSQL, Keycloak y Next.js, resumiendo [research.md](./research.md), para aprobar el stack
- [ ] T121 Actualizar `README.md` con enlaces a la constitución, la spec y el plan, y verificar que "Arranque rápido" coincide con [quickstart.md](./quickstart.md)
- [ ] T122 Verificar la cobertura: `cd backend && uv run pytest --cov --cov-fail-under=65`; confirmar que está entre 65 y 70% o más sobre lo implementado (SC-003)
- [ ] T123 Recorrer [quickstart.md](./quickstart.md) en una máquina limpia y cronometrar que API, base e identidad levantan en menos de 10 minutos con un solo comando (SC-001)
- [ ] T124 Verificar SC-002, SC-005 y SC-007: los 10 endpoints cumplen el contrato, la prueba de DNI simultáneo da un solo éxito, y los accesos sin token o sin rol son rechazados
- [ ] T125 Resolver los conflictos de `backend/pyproject.toml` y `backend/uv.lock` al integrar, correr todo el CI en `dev` y abrir la PR de `dev` hacia `main`

---

## Dependencias y orden de ejecución

- **Fase 1 (S1)**: T001–T003 primero; T004–T013 después; los casos de uso (T014–T033) solo requieren T013. Los repositorios SQL (T034–T039) esperan a S3 y a T097.
- **Fase 2 (S2)**: T041 y T042 primero; el resto sigue el orden de las PRs. T074 espera a S1 y S3.
- **Fase 3 (S3)**: independiente al arranque. T083 desbloquea a S1 (T034) y S4 (T097).
- **Fase 4 (S4)**: T090–T096 sin dependencias (T094–T095 pulen el OpenAPI y se avisan al resto antes de mergear); T097 espera a T083; T098–T106 y T107 esperan a la integración de S1–S3.
- **Fase 5 (S5)**: independiente hasta T119, que necesita la API real.
- **Fase 6**: al final, con todo integrado en `dev`.

## Oportunidades de paralelismo

- Cinco personas o grupos pueden empezar el día uno: T001 (S1), T041 (S2), T076 (S3), T090 (S4) y T109 (S5). Los cuatro últimos tocan solo su grupo de dependencias en `pyproject.toml`.
- Dentro de S1: los tests de dominio T004, T006, T008 y T010 son independientes entre sí; también los pares de casos de uso de conductor y de vehículo.
- Dentro de S2: los routers de conductores, habilitación, documentación y vehículos son independientes una vez hechas T041–T052.

## Criterios de prueba independiente por historia

| Historia | Cómo se prueba sola |
|---|---|
| US1 Conductores | Registrar y consultar un conductor por id y en el listado; DNI duplicado da `409` |
| US2 Habilitación | Aplicar acciones y verificar estado e historial; transición inválida da `409`; aprobar sin licencia vigente da `422` |
| US3 Licencia | Cargar una licencia vigente y otra vencida y verificar el estado |
| US4 Vehículos | Registrar, listar, consultar y habilitar un vehículo; patente duplicada da `409` |
| US5 Entorno y seguridad | Levantar con un comando; sin token `401`; sin rol de operador `403` |
| US6 Verificación | Un PR con cobertura baja o contrato inválido falla el CI |
| US7 Pantalla | Con el entorno levantado, muestra el listado; con la API caída, muestra un error claro |

## Estrategia de implementación

1. **Primer hito (MVP)**: US1 de punta a punta: dominio y casos de uso (S1), `POST` y `GET` de conductores (S2), esquema y seed (S3), CI (S4). La pantalla (S5) ya puede mostrar datos.
2. **Segundo hito**: US2 y US3 (habilitación y licencia).
3. **Tercer hito**: US4 (vehículos) y pruebas de concurrencia.
4. **Cierre**: Fase 6 y PR de `dev` hacia `main`.

Cada hito deja la rama `dev` en verde.

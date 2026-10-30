# Tareas: Iteración 2 — Integración E2E y endpoints restantes de M3

**Entrada**: Documentos de diseño en `specs/iteracion2/`
**Requisitos previos**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Pruebas**: obligatorias (constitución, principio I). Cada tarea de implementación va precedida por su test que falla primero (Red → Green → Refactor). Los tests de Iteración 1 no se modifican.

**Convención de estado**:
- `[ ]` pendiente · `[x]` completo · `[~]` en curso

## Formato: `- [ ] ID [P] [Stack] [Historia] Descripción con ruta`

- **[P]**: se puede hacer en paralelo.
- **[S1]–[S5]**: stack dueño de la tarea.
- **[US8]–[US15]**: historia de [spec.md](./spec.md).

---

## Fase 1: Stack 3 — Datos (migración de esquema)

**Meta**: extender el esquema con las columnas de ubicación del conductor (ya definidas pero nulas) y la tabla `vehiculo_documento`. Desbloquea S1 y S2 para los repositorios SQL nuevos.

### PR `feat/s3-migracion-i2`

- [ ] T201 [S3] Crear migración Alembic `0002_ubicacion_conductor_vehiculo_documento.py`: confirmar que `latitud`, `longitud`, `fecha_act_ubic` ya existen en la tabla `conductor` (Iteración 1 las creó nulas); crear tabla `vehiculo_documento` análoga a `documento_conductor` con FK a `vehiculo`. Mantener `DOWN` funcional
- [ ] T202 [S3] Extender el seed con conductores que tengan `latitud`, `longitud` y distintos tipos de servicio en sus vehículos para poder probar los filtros nuevos de `GET /conductores`
- [ ] T203 [S3] Actualizar `infra/.env.example` si se agregan variables nuevas (no se esperan)

---

## Fase 2: Stack 1 — Lógica del backend

**Meta**: implementar los casos de uso de los 6 endpoints nuevos, el control de acceso por conductor y los filtros de ubicación/tipo de servicio.

### PR `feat/s1-logica-i2`

#### Control de acceso por conductor [US15]

- [ ] T204 [S1] [US15] Test (Red) `backend/tests/unitarios/test_acceso.py`: un conductor solo puede operar sobre su propio `id_conductor`; cualquier otro `id_conductor` lanza `AccesoProhibido`
- [ ] T205 [S1] [US15] Impl (Green) `backend/app/dominio/errores.py`: agregar `AccesoProhibido` hasta que pase T204
- [ ] T206 [S1] [US15] Test (Red) `backend/tests/unitarios/test_politica_acceso.py`: la función/política `verificar_acceso_conductor(id_del_token, id_del_recurso)` lanza `AccesoProhibido` cuando no coinciden, y no lanza nada si coinciden o si el token tiene rol `operador`
- [ ] T207 [S1] [US15] Impl (Green) `backend/app/aplicacion/politicas/acceso_conductor.py` hasta que pase T206

#### Filtros de ubicación y tipo de servicio en listar conductores [US14]

- [ ] T208 [S1] [US14] Test (Red) `backend/tests/unitarios/casos_de_uso/test_listar_conductores_filtros_i2.py`: filtrar por `latitud`/`longitud` devuelve solo los conductores con ubicación; filtrar por `tipo_servicio` devuelve solo los que tienen ese tipo habilitado; los filtros se combinan en AND con los ya existentes
- [ ] T209 [S1] [US14] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_conductores.py`: extender `FiltrosListarConductores` con `latitud?`, `longitud?` y `tipo_servicio?` hasta que pase T208
- [ ] T210 [S1] [US14] Impl (Green) `backend/app/aplicacion/puertos/repositorio_conductores.py`: extender la firma del repositorio para aceptar los nuevos filtros (implementación en memoria para tests)

#### Actualizar conexión / disponibilidad [US10]

- [ ] T211 [S1] [US10] Test (Red) `backend/tests/unitarios/casos_de_uso/test_actualizar_conductor.py`: actualizar `conectado` / `disponible` modifica la entidad; intentar modificar campos no permitidos se ignora o lanza `DatosInvalidos`
- [ ] T212 [S1] [US10] Impl (Green) `backend/app/aplicacion/casos_de_uso/actualizar_conductor.py` hasta que pase T211

#### Listar documentos del conductor [US11]

- [ ] T213 [S1] [US11] Test (Red) `backend/tests/unitarios/casos_de_uso/test_listar_documentos_conductor.py`: devuelve todos los documentos del conductor con estado calculado; lista vacía si no tiene; `NoEncontrado` si el conductor no existe
- [ ] T214 [S1] [US11] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_documentos_conductor.py` hasta que pase T213

#### Historial de habilitación del vehículo [US9]

- [ ] T215 [S1] [US9] Test (Red) `backend/tests/unitarios/casos_de_uso/test_historial_habilitacion_vehiculo.py`: devuelve eventos en orden cronológico; solo el evento `ALTA` si no hubo acciones; `NoEncontrado` si el vehículo no pertenece al conductor
- [ ] T216 [S1] [US9] Impl (Green) `backend/app/aplicacion/casos_de_uso/historial_habilitacion_vehiculo.py` hasta que pase T215

#### Documentación del vehículo [US12]

- [ ] T217 [S1] [US12] Test (Red) `backend/tests/unitarios/casos_de_uso/test_documentacion_vehiculo.py`: registrar documento guarda y devuelve con estado calculado; listar devuelve lista (vacía o con datos); `NoEncontrado` si el vehículo no pertenece al conductor
- [ ] T218 [S1] [US12] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_documento_vehiculo.py` y `listar_documentos_vehiculo.py` hasta que pasen T217
- [ ] T219 [S1] [US12] Impl (Green) puerto `RepositorioDocumentosVehiculo` en `backend/app/aplicacion/puertos/` con implementación en memoria para tests

#### Tipos de servicio del vehículo [US13]

- [ ] T220 [S1] [US13] Test (Red) `backend/tests/unitarios/casos_de_uso/test_actualizar_tipos_servicio.py`: actualizar tipos de servicio modifica las filas de `vehiculo_tipo_servicio`; valor inválido lanza `DatosInvalidos`; vehículo ajeno lanza `NoEncontrado`
- [ ] T221 [S1] [US13] Impl (Green) `backend/app/aplicacion/casos_de_uso/actualizar_tipos_servicio_vehiculo.py` hasta que pase T220

#### Repositorios SQL (depende de T201) [S1]

- [ ] T222 [S1] Impl (Green) `backend/app/infraestructura/repositorios/repositorio_conductores.py`: extender con los filtros nuevos (ubicación, tipo de servicio) y la actualización de `conectado`/`disponible`
- [ ] T223 [S1] Impl (Green) `backend/app/infraestructura/repositorios/repositorio_documentos_vehiculo.py`: nuevo repositorio SQL sobre la tabla `vehiculo_documento`

---

## Fase 3: Stack 2 — Servidor HTTP

**Meta**: exponer los 6 endpoints nuevos y aplicar la política de acceso por conductor en cada router.

### PR `feat/s2-endpoints-i2`

- [ ] T224 [S2] [US15] Test (Red) `backend/tests/api/test_acceso_conductor.py`: una petición de conductor con `id_conductor` distinto al del token devuelve `403`; la misma petición con `id_conductor` propio devuelve `200`
- [ ] T225 [S2] [US15] Impl (Green) `backend/app/api/seguridad.py`: agregar función/dependencia `exigir_acceso_propio_o_operador(id_conductor_ruta, usuario_actual)` que llama a `verificar_acceso_conductor` del dominio hasta que pase T224
- [ ] T226 [S2] [US9] Test (Red) `backend/tests/api/test_historial_habilitacion_vehiculo.py`: `GET /conductores/{id}/vehiculos/{id_vehiculo}/habilitacion` devuelve la lista de eventos; `404` si el vehículo no existe; `401` sin token
- [ ] T227 [S2] [US9] Impl (Green) router en `backend/app/api/routers/vehiculos.py` (nuevo endpoint) hasta que pase T226
- [ ] T228 [S2] [US10] Test (Red) `backend/tests/api/test_actualizar_conductor.py`: `PATCH /conductores/{id}` actualiza `conectado`/`disponible`; `403` si el conductor intenta modificar a otro; `404` si el conductor no existe
- [ ] T229 [S2] [US10] Impl (Green) router en `backend/app/api/routers/conductores.py` hasta que pase T228
- [ ] T230 [S2] [US11] Test (Red) `backend/tests/api/test_listar_documentos_conductor.py`: `GET /conductores/{id}/documentacion` devuelve lista; `404` si no existe
- [ ] T231 [S2] [US11] Impl (Green) router en `backend/app/api/routers/documentacion.py` hasta que pase T230
- [ ] T232 [S2] [US12] Test (Red) `backend/tests/api/test_documentacion_vehiculo.py`: `POST` y `GET` de `/vehiculos/{id_vehiculo}/documentacion`; `404` si el vehículo no existe o no es del conductor
- [ ] T233 [S2] [US12] Impl (Green) router en `backend/app/api/routers/vehiculos.py` hasta que pase T232
- [ ] T234 [S2] [US13] Test (Red) `backend/tests/api/test_tipos_servicio.py`: `PATCH /conductores/{id}/vehiculos/{id_vehiculo}` actualiza tipos de servicio; `400` con valor inválido; `404` si el vehículo no es del conductor
- [ ] T235 [S2] [US13] Impl (Green) router en `backend/app/api/routers/vehiculos.py` hasta que pase T234
- [ ] T236 [S2] [US14] Test (Red) `backend/tests/api/test_filtros_listado.py`: `GET /conductores?latitud=...&longitud=...&tipo_servicio=...` aplica los filtros nuevos
- [ ] T237 [S2] [US14] Impl (Green) actualizar el router de conductores con los parámetros nuevos hasta que pase T236
- [ ] T238 [S2] Actualizar `backend/app/api/esquemas.py` con los nuevos schemas de entrada/salida de Pydantic para los 6 endpoints

---

## Fase 4: Stack 4 — Testing y CI

**Meta**: pruebas de contrato para los 6 nuevos endpoints y verificar que el umbral de cobertura sube a 70 %.

### PR `test/s4-contrato-i2`

- [ ] T239 [S4] Test `backend/tests/contrato/test_contrato_i2.py`: agregar los 6 nuevos endpoints al suite de contrato con openapi-core; cada respuesta se valida contra `docs/contract/openapi.yaml`
- [ ] T240 [S4] Actualizar `backend/.coveragerc` y el workflow de CI para usar `--cov-fail-under=70`
- [ ] T241 [S4] Test de integración `backend/tests/integracion/test_acceso_conductor.py`: usando Testcontainers, verificar que un conductor no puede acceder a recursos de otro (`403` real, no solo unitario)

---

## Fase 5: Stack 5 — Frontend y Cierre

**Meta**: integración E2E del frontend con la API real, badges de color por estado y todas las tareas de cierre diferidas de Iteración 1.

### PR `feat/s5-frontend-e2e` [US8]

- [ ] T242 [S5] [US8] Crear `frontend/.env.local` (gitignored) con valores reales de `infra/.env`: `API_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `TEST_USER`, `TEST_PASSWORD`. Verificar que `npm run dev` arranca sin errores de variables
- [ ] T243 [S5] [US8] Levantar `infra/` con Docker Compose y verificar `http://localhost:8080/salud` responde OK y `http://localhost:8081` atiende Keycloak
- [ ] T244 [S5] [US8] Verificar obtención de token: `POST` al endpoint de Keycloak con las credenciales del `.env.local`; confirmar que el token contiene los roles y claims esperados
- [ ] T245 [S5] [US8] Verificar `GET /api/v1/conductores` con `Authorization: Bearer <token>`: la respuesta coincide con `ConductorConUbicacion[]` del contrato y los tipos de `src/lib/tipos.ts`
- [ ] T246 [S5] [US8] [P] Test (Red) `frontend/src/components/ListadoConductores.test.tsx`: agregar test que verifica que cada estado de habilitación (`PENDIENTE`, `APROBADA`, `OBSERVADA`, `SUSPENDIDA`, `RECHAZADA`) tiene un elemento con el atributo `data-estado` o clase CSS correspondiente
- [ ] T247 [S5] [US8] Impl (Green) `frontend/src/components/ListadoConductores.tsx`: reemplazar el texto plano del estado por un badge con color diferenciado por estado — sin añadir dependencias externas; usar clases CSS en línea o un `Map<EstadoHabilitacion, string>` de colores hasta que pase T246
- [ ] T248 [S5] [US8] Ejecutar `npm run test`, `npm run lint` y `npm run build` con los valores de `.env.local`: todos deben terminar sin errores
- [ ] T249 [S5] [US8] Verificar manualmente la pantalla con el stack levantado: la lista muestra conductores del seed con badges de color; con la API apagada muestra el mensaje de error claro

### PR `feat/s5-cierre`

- [ ] T250 [S5] Redactar `docs/justificacion-stack.md` (RNF-01): por qué FastAPI, PostgreSQL, Keycloak y Next.js, resumiendo [research.md de Iteración 1](../iteracion1/research.md). Máximo 1 página
- [ ] T251 [S5] Actualizar `README.md` raíz con enlaces a la constitución (`docs/constitucion.md`), la spec de Iteración 2 y el plan, y verificar que "Arranque rápido" coincide con [quickstart.md](./quickstart.md)
- [ ] T252 [S5] Verificar cobertura: `cd backend && uv run pytest --cov --cov-fail-under=70`; si no alcanza, identificar los módulos nuevos sin cobertura suficiente y agregar los tests faltantes (solo unitarios o de integración, sin bajar calidad)
- [ ] T253 [S5] Recorrer [quickstart.md](./quickstart.md) en una máquina limpia y cronometrar que API, base e identidad levantan en menos de 10 minutos con un solo comando (revalidación de SC-001 / SC-013)
- [ ] T254 [S5] Verificar SC-009, SC-010 y la combinación de filtros nuevos: los 6 endpoints cumplen el contrato, un conductor no accede a datos ajenos, los filtros `latitud`/`longitud`/`tipo_servicio` funcionan correctamente
- [ ] T255 [S5] Resolver conflictos de `backend/pyproject.toml` y `backend/uv.lock` si los hay, correr todo el CI en `dev` y abrir la PR de `dev` hacia `main`

---

## Dependencias y orden de ejecución

- **Fase 1 (S3)**: T201–T203 primero; T201 desbloquea T222–T223 (S1) y los tests de integración de S4.
- **Fase 2 (S1)**: T204–T211 arrancan en paralelo el día uno (usan repositorios en memoria); T222–T223 esperan T201.
- **Fase 3 (S2)**: T224–T238 esperan los casos de uso de S1 correspondientes.
- **Fase 4 (S4)**: T239–T241 esperan que S1, S2 y S3 estén integrados en `dev`.
- **Fase 5 (S5)**: T242–T249 pueden arrancar en paralelo con S1/S2/S3; T250–T255 van al final.

## Oportunidades de paralelismo

- S1 y S3 pueden arrancar el mismo día; S2 puede avanzar con casos de uso simulados (igual que en Iteración 1).
- Dentro de S1: los casos de uso T211, T213, T215, T217, T220 son independientes entre sí.
- S5 frontend (T242–T249) es completamente independiente de S1/S2/S3 hasta T249 (verificación manual).

## Criterios de prueba independiente por historia

| Historia | Cómo se prueba sola |
|---|---|
| US8 E2E frontend | `.env.local` completo + Compose levantado + `npm run dev`; badges visibles por estado |
| US9 Historial vehículo | Aplicar acciones de habilitación al vehículo y verificar el `GET` de historial |
| US10 PATCH conductor | Cambiar `conectado`/`disponible` y verificar con `GET`; intentar con otro `id_conductor` da `403` |
| US11 Docs conductor | Cargar una licencia y verificar que aparece en `GET /documentacion` con estado calculado |
| US12 Docs vehículo | Cargar un documento de vehículo y verificar `GET`; vehículo de otro conductor da `404` |
| US13 Tipos servicio | `PATCH` con tipos válidos e inválidos; verificar cambio en `GET` del vehículo |
| US14 Filtros completos | `GET /conductores?latitud=...&longitud=...&tipo_servicio=...` devuelve subset correcto |
| US15 Acceso por conductor | Petición con token de conductor A al `id_conductor` de B devuelve `403` |

## Alcance integrado esperado al cierre

S1–S5 integrados hasta T255. `dev` mergeado a `main` con CI verde, cobertura ≥ 70 %, contrato 100 % cubierto para los 16 endpoints y criterios SC-008 a SC-013 verificados.

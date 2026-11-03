# Tareas: Iteración 2 — Backend de M3 (Conductores y Vehículos)

**Entrada**: Documentos de diseño en `specs/iteracion2-backend/`
**Requisitos previos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Pruebas**: obligatorias en todo el proyecto (constitución, principio I). Cada tarea de implementación va precedida por su tarea de **test que falla primero** (Red → Green → Refactor) y nombra el test que cumple. Los tests no se modifican para hacerlos pasar. Las únicas excepciones son los cambios de requisito del spec (acceso propio del conductor y listado solo para operador y servicio), que se aclaran en las tareas T378 y T379 con el motivo.

**Numeración**: las tareas arrancan en T301 para no chocar con T001–T125 de la [Iteración 1](../iteracion1/tasks.md).

**Organización**: las tareas se agrupan por **stack** y, dentro de cada stack, por **PR**. Cada PR tiene una sola responsabilidad y cada tarea lleva su historia de usuario cuando corresponde.

## Formato: `- [ ] ID [P] [Stack] [Historia] Descripción con ruta`

- **[P]**: se puede hacer en paralelo con la tarea anterior (archivos distintos, sin depender de tareas incompletas).
- **[S1]** lógica y **[S2]** servidor: stack dueño de la tarea (ver el [plan](./plan.md)). Las de cierre no llevan stack.
- **[US1]…[US8]**: historia de [spec.md](./spec.md): US1 acceso por rol y servicio, US2 estado y ubicación, US3 disponibilidad desde M4, US4 viaje finalizado y puntaje, US5 solicitudes, US6 vehículo, US7 listado y campos nuevos, US8 acceso propio del conductor.
- Las tareas de **test** dicen "Test (Red)"; las de **implementación**, "Impl (Green)" y nombran el test que cumplen.

## PRs (todas contra `dev`)

Una PR por fila. Las estimaciones son de líneas de diff con tests; una PR que llegue a 1500–2000 líneas sigue siendo aceptable y no hace falta partirla.

| PR | Rama | Tareas | Depende de | Líneas (est.) |
|---|---|---|---|---|
| L1 | `feat/s1-dominio-conductor-estado` | T301–T308 | — | 450 |
| L2 | `feat/s1-dominio-solicitud-viaje-documento` | T309–T314 | — | 450 |
| L3 | `feat/s1-politica-acceso` | T315–T318 | — | 250 |
| L4 | `feat/s1-puertos-fakes-i2` | T319–T323 | L1, L2 | 450 |
| L5 | `feat/s1-casos-estado-ubicacion` | T324–T330 | L4 | 500 |
| L6 | `feat/s1-caso-disponibilidad-m4` | T331–T332 | L5 | 300 |
| L7 | `feat/s1-caso-viaje-finalizado` | T333–T335 | L4 | 450 |
| L8 | `feat/s1-casos-solicitudes` | T336–T340 | L5 | 500 |
| L9 | `feat/s1-casos-vehiculo-i2` | T341–T348 | L4 | 550 |
| L10 | `feat/s1-casos-conductor-i2` | T349–T352 | L4 | 350 |
| L11 | `feat/s1-sql-conductor-i2` | T353–T356 | L4 y la migración y los modelos de Datos y seguridad | 500 |
| L12 | `feat/s1-sql-solicitud-viaje` | T357–T362 | L11 | 550 |
| L13 | `feat/s1-sql-documentos-vehiculo` | T363–T366 | L11 | 400 |
| V1 | `feat/s2-seguridad-rol-servicio` | T367–T374 | L3 | 500 |
| V2 | `feat/s2-acceso-endpoints-existentes` | T375–T380 | V1 | 550 |
| V3 | `feat/s2-estado-ubicacion` | T381–T388 | V1 y L5 | 550 |
| V4 | `feat/s2-integracion-m4` | T389–T392 | V1 y L6 | 300 |
| V5 | `feat/s2-integracion-m6` | T393–T395 | V1 y L7 | 350 |
| V6 | `feat/s2-solicitudes` | T396–T400 | V1 y L8 | 450 |
| V7 | `feat/s2-vehiculo-i2` | T401–T404 | V1 y L9 | 450 |
| V8 | `feat/s2-conductor-campos-nuevos` | T405–T412 | V1 y L10 | 400 |
| C1 | `docs/backend-cierre-i2` | T413–T416 | todas las anteriores | 150 |

## Olas de integración

Las PRs de una misma ola no dependen entre sí y se pueden abrir en paralelo.

```text
Ola 1:  L1  L2  L3
Ola 2:  L4  V1
Ola 3:  L5  L7  L9  L10  V2
Ola 4:  L6  L8  V3  V5  V7  V8
Ola 5:  V4  V6
Ola 6:  L11 → L12, L13        (esperan la migración y los modelos de Datos y seguridad)
Cierre: C1
```

- Las olas 1 a 5 trabajan con repositorios en memoria y no esperan a nadie. L4 deja la unidad de trabajo SQL con los repositorios nuevos marcados como pendientes (T323) para que `dev` siga en verde hasta la ola 6.
- Hasta que L11 a L13 estén integradas, los endpoints nuevos solo funcionan con los repositorios en memoria. Si la migración de Datos y seguridad ya está en `dev` antes de la ola 4, conviene adelantar L11 a L13.
- Cada PR se abre desde `dev` ya actualizada.

## Dependencias con otros grupos

| Grupo | Qué necesita Backend | Hasta que llegue |
|---|---|---|
| Datos y seguridad | Migración y modelos con las columnas y tablas del [data-model.md](./data-model.md) (issue #36) | L11, L12 y L13 |
| Datos y seguridad | Rol `servicio`, cuentas técnicas de M4 y M6 y claim `id_conductor` del conductor | La verificación contra el entorno real (C1) |
| Testing | Ampliar las pruebas de contrato a las 19 operaciones, el umbral de cobertura y los casos de concurrencia de punta a punta | Después de la ola 6 |

**Puntos de sincronización**: `docs/contract/openapi.yaml` · [data-model.md](./data-model.md) · [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) · [contracts/token-jwt.md](./contracts/token-jwt.md) · [contracts/errores.md](./contracts/errores.md).

**Dueños de archivos**: ver la tabla de [plan.md](./plan.md). Cada tarea toca solo archivos de su stack, salvo las que lo aclaran.

---

## Fase 1: Stack 1 — Lógica del backend

**Meta**: dominio, política de acceso, puertos, casos de uso y repositorios SQL de los 9 endpoints nuevos y de las adaptaciones, con TDD y sin depender de FastAPI. Las PRs L1 a L10 trabajan con repositorios en memoria y no esperan a nadie; L11 a L13 esperan la migración y los modelos de Datos y seguridad.

### PR `feat/s1-dominio-conductor-estado` (L1, T301–T308): Dominio del conductor: puntaje y estado

- [ ] T301 [S1] [US4] Test (Red) `backend/tests/unitarios/dominio/test_conductor.py`: un conductor nuevo queda con `id_vehiculo_activo` nulo, `fecha_ultimo_cambio_estado` nula, `suma_puntajes` 0 y `cantidad_calificaciones` 0; `puntaje_promedio` es nulo con cantidad 0; con calificaciones es `suma / cantidad` en 2 decimales, mitad hacia arriba (14/3 → 4.67; 9/2 → 4.5); `registrar_puntaje(p)` suma `p` y cuenta 1; un puntaje fuera de 1 a 5 lanza `DatosInvalidos`
- [ ] T302 [S1] [US4] Impl (Green) `backend/app/dominio/conductor.py`: campos nuevos con esos valores por defecto, propiedad `puntaje_promedio` calculada con `Decimal` y `registrar_puntaje`, hasta que pase T301
- [ ] T303 [S1] [US2] Test (Red) `backend/tests/unitarios/dominio/test_conductor.py`: `fijar_ubicacion(latitud, longitud, ahora)` guarda las coordenadas y `fecha_act_ubic = ahora`; rechaza una latitud fuera de -90 a 90 o una longitud fuera de -180 a 180 con `DatosInvalidos`; `tiene_ubicacion` es falso con los tres campos nulos
- [ ] T304 [S1] [US2] Impl (Green) `backend/app/dominio/conductor.py`: `fijar_ubicacion` y `tiene_ubicacion` hasta que pase T303
- [ ] T305 [S1] [US2] Test (Red) `backend/tests/unitarios/dominio/test_disponibilidad.py`: `puede_estar_disponible(conductor, vehiculo_activo)` es verdadero solo con conductor conectado y `APROBADA` y vehículo activo existente y `APROBADA`; pedir `disponible = true` sin cumplirlo lanza `ConductorNoHabilitado`; pedir `conectado = false` deja `disponible = false` aunque se pida otra cosa; quitar el vehículo activo (`None`) deja `disponible = false`; pasar a un vehículo activo no `APROBADA` estando disponible deja `disponible = false`; un pedido que no cambia ningún valor no toca `fecha_ultimo_cambio_estado`; si algún valor cambia, `fecha_ultimo_cambio_estado = ahora`; cambiar solo la ubicación no la toca
- [ ] T306 [S1] [US2] Impl (Green) `backend/app/dominio/errores.py` (`ConductorNoHabilitado`) y `backend/app/dominio/disponibilidad.py` (`puede_estar_disponible` y `aplicar_cambio_estado(conductor, vehiculo_activo, *, conectado, disponible, id_vehiculo_activo, ahora)`, que devuelve si hubo cambio), hasta que pase T305
- [ ] T307 [S1] [US3] Test (Red) `backend/tests/unitarios/dominio/test_disponibilidad.py`: `aplicar_disponibilidad_de_m4(conductor, vehiculo_activo, *, disponible, actualizado)` ignora el pedido si `actualizado` es estrictamente anterior a `fecha_ultimo_cambio_estado`; con `actualizado` igual o posterior aplica solo `disponible` y guarda `fecha_ultimo_cambio_estado = actualizado`; `disponible = false` se acepta siempre; `disponible = true` sin cumplir la regla lanza `ConductorNoHabilitado`; no modifica `conectado`, `id_vehiculo_activo`, ubicación ni habilitación
- [ ] T308 [S1] [US3] Impl (Green) `backend/app/dominio/disponibilidad.py`: `aplicar_disponibilidad_de_m4`, hasta que pase T307

### PR `feat/s1-dominio-solicitud-viaje-documento` (L2, T309–T314): Dominio de solicitud, viaje finalizado y documento de vehículo

- [ ] T309 [P] [S1] [US5] Test (Red) `backend/tests/unitarios/dominio/test_solicitud.py`: estados `PENDIENTE`, `ACEPTADO`, `RECHAZADO` y `VENCIDA`; `estado_efectivo(ahora)` devuelve `PENDIENTE` si `ahora <= vence_en` (la igualdad es válida) y `VENCIDA` si `ahora > vence_en`; los demás estados no cambian; `responder(respuesta, hora_rta, ahora)` sobre una `PENDIENTE` vigente deja el estado igual a la respuesta y guarda `respuesta` y `hora_rta` tal como llegan; vencida lanza `SolicitudVencida`; ya respondida lanza `SolicitudYaRespondida`; guardada como `VENCIDA` lanza `SolicitudVencida`; la hora que decide es `ahora`, no `hora_rta`
- [ ] T310 [S1] [US5] Impl (Green) `backend/app/dominio/errores.py` (`SolicitudVencida`, `SolicitudYaRespondida`) y `backend/app/dominio/solicitud.py` (entidad, enum `EstadoSolicitud`, `estado_efectivo`, `responder`), hasta que pase T309
- [ ] T311 [P] [S1] [US4] Test (Red) `backend/tests/unitarios/dominio/test_viaje_finalizado.py`: `ViajeFinalizado.crear(...)` exige `id_viaje`, `id_conductor`, `fecha_finalizacion` y destino con latitud de -90 a 90 y longitud de -180 a 180; `puntaje_conductor` entero entre 1 y 5 o nulo; `coincide_con(otro)` compara `id_conductor`, `fecha_finalizacion`, destino y puntaje y es falso si alguno difiere
- [ ] T312 [S1] [US4] Impl (Green) `backend/app/dominio/errores.py` (`ViajeEnConflicto`) y `backend/app/dominio/viaje_finalizado.py` (entidad con `ubicacion_aplicada` y `coincide_con`), hasta que pase T311
- [ ] T313 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/dominio/test_documento_vehiculo.py`: tipos `SEGURO`, `CEDULA_VERDE` y `VTV`; `numero` obligatorio; `entidad_emisora` opcional; `fecha_vencimiento` posterior a `fecha_emision` (si no, `DatosInvalidos`); `url_archivo` con esquema y host; estado `VIGENTE` o `VENCIDO` calculado con la fecha de hoy
- [ ] T314 [S1] [US6] Impl (Green) `backend/app/dominio/documento_vehiculo.py` (entidad, enum `TipoDocumentoVehiculo` y estado calculado, reutilizando `EstadoDocumento`), hasta que pase T313

### PR `feat/s1-politica-acceso` (L3, T315–T318): Política pura de acceso

- [ ] T315 [S1] [US8] Test (Red) `backend/tests/unitarios/aplicacion/test_politica_acceso.py`: `verificar_acceso(identidad, id_conductor_recurso, admite)` con la matriz de [contracts/token-jwt.md](./contracts/token-jwt.md): el operador pasa sin `id_conductor`; el conductor pasa solo con su propio id; con el id de otro lanza `AccesoProhibido`; un conductor sin `id_conductor` (nulo, booleano o no entero) lanza `AccesoProhibido`; el servicio pasa solo si la operación lo admite y si no lanza `RolNoAutorizado`; un rol no admitido lanza `RolNoAutorizado`; con varios roles vale el que más permite (operador y conductor juntos no quedan limitados por el id)
- [ ] T316 [S1] [US8] Impl (Green) `backend/app/dominio/errores.py` (`AccesoProhibido`, `RolNoAutorizado`), `backend/app/aplicacion/politicas/__init__.py` y `backend/app/aplicacion/politicas/acceso.py` (`Identidad` con roles, `id_conductor` e `id_operador`, y `verificar_acceso`), hasta que pase T315
- [ ] T317 [S1] [US1] Test (Red) `backend/tests/unitarios/aplicacion/test_politica_acceso.py`: `verificar_rol(identidad, admite)` para operaciones sin id de conductor (listado, alta, integraciones): `GET /conductores` admite operador y servicio; las integraciones admiten solo servicio; un conductor recibe `RolNoAutorizado`
- [ ] T318 [S1] [US1] Impl (Green) `backend/app/aplicacion/politicas/acceso.py`: `verificar_rol` y las constantes de roles admitidos por patrón de operación, hasta que pase T317

### PR `feat/s1-puertos-fakes-i2` (L4, T319–T323): Puertos nuevos y repositorios en memoria

- [ ] T319 [S1] Test (Red) `backend/tests/unitarios/fakes/test_fakes.py`: `RepositorioConductoresEnMemoria` persiste los campos nuevos del conductor y `listar` filtra por `tipo_servicio` (conductores con al menos un vehículo con ese tipo habilitado); `RepositorioSolicitudesEnMemoria` asigna id al guardar, obtiene y lista por conductor; `RepositorioViajesFinalizadosEnMemoria.registrar_si_no_existe` devuelve verdadero la primera vez y falso la segunda, y `obtener` devuelve el primero; `RepositorioDocumentosVehiculoEnMemoria` asigna id, lista por vehículo y por lote con una clave por cada id pedido; `UnidadDeTrabajoEnMemoria.bloquear_solicitud` devuelve la solicitud y `rollback` descarta los cambios nuevos
- [ ] T320 [P] [S1] Impl (Green) puertos nuevos en `backend/app/aplicacion/puertos/repositorio_solicitudes.py`, `repositorio_viajes_finalizados.py` y `repositorio_documentos_vehiculo.py`, según [contracts/casos-de-uso.md](./contracts/casos-de-uso.md)
- [ ] T321 [S1] Impl (Green) `backend/app/aplicacion/puertos/repositorio_conductores.py` (`listar` suma `tipo_servicio`) y `backend/app/aplicacion/puertos/unidad_de_trabajo.py` (atributos `solicitudes`, `viajes_finalizados` y `documentos_vehiculo`, y `bloquear_solicitud(id_solicitud)`)
- [ ] T322 [S1] Impl (Green) `backend/tests/unitarios/fakes/repositorios_en_memoria.py`: los tres repositorios en memoria nuevos, `tipo_servicio` en el listado de conductores y `bloquear_solicitud`, hasta que pase T319
- [ ] T323 [S1] Impl (Green) `backend/app/infraestructura/repositorios/sql_unidad_de_trabajo.py` y `sql_conductores.py`: la unidad de trabajo SQL declara los repositorios nuevos como pendientes (lanzan `NotImplementedError` al usarse) y `listar` acepta `tipo_servicio` pero lanza `NotImplementedError` si no es `None`, para que la aplicación siga arrancando y la suite siga en verde hasta L11 a L13

### PR `feat/s1-casos-estado-ubicacion` (L5, T324–T330): Casos de uso de estado y ubicación

- [ ] T324 [P] [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_estado_conductor.py`: devuelve `conectado`, `disponible`, `id_vehiculo_activo` (nulo si no tiene) y `actualizado` (= `fecha_ultimo_cambio_estado`, la fecha de alta si nunca cambió), sin ubicación; `NoEncontrado` si el conductor no existe
- [ ] T325 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_estado_conductor.py` y el resultado `EstadoDelConductor` en `backend/app/aplicacion/casos_de_uso/resultados.py`, hasta que pase T324
- [ ] T326 [P] [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_ubicacion_conductor.py`: devuelve `latitud`, `longitud` y `fecha_act_ubic`; sin ubicación devuelve los tres en `None` y nunca `0.0`; `NoEncontrado` si el conductor no existe
- [ ] T327 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_ubicacion_conductor.py` y el resultado `UbicacionDelConductor`, hasta que pase T326
- [ ] T328 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_actualizar_estado_conductor.py`: queda disponible con conductor y vehículo activo `APROBADA` y `actualizado` toma la hora del `Reloj`; sin cumplir la regla lanza `ConductorNoHabilitado` y no cambia nada; desconectarse deja no disponible; `latitud` y `longitud` guardan la ubicación con `fecha_act_ubic` del `Reloj`; una sola de las dos lanza `DatosInvalidos`; sin ubicación y con ubicación previa no la cambia; un cuerpo sin ningún campo lanza `DatosInvalidos`; un vehículo activo ajeno o inexistente lanza `NoEncontrado`; `null` quita el vehículo activo y deja no disponible; bloquea al conductor con `bloquear_conductor`
- [ ] T329 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_actualizar_estado_conductor.py`: ubicación simulada (decisión 6): al pasar de desconectado a conectado sin ubicación previa y sin coordenadas en el pedido, asigna la coordenada inyectada con `fecha_act_ubic` igual a la hora del `Reloj`; si ya tiene ubicación no la cambia; si el pedido trae coordenadas usa esas; la coordenada simulada nunca es `0, 0`
- [ ] T330 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/actualizar_estado_conductor.py` (recibe `UnidadDeTrabajo`, `Reloj` y la ubicación simulada) hasta que pasen T328 y T329

### PR `feat/s1-caso-disponibilidad-m4` (L6, T331–T332): Caso de uso de disponibilidad desde M4

- [ ] T331 [S1] [US3] Test (Red) `backend/tests/unitarios/aplicacion/test_actualizar_disponibilidad_desde_m4.py`: `disponible = false` queda no disponible y devuelve el estado; `disponible = true` con la regla cumplida queda disponible; sin cumplirla lanza `ConductorNoHabilitado`; un `actualizado` anterior al último cambio devuelve el estado vigente sin cambios; con `actualizado` igual aplica; el mismo pedido repetido deja el mismo estado; no toca conexión, vehículo activo ni ubicación; `NoEncontrado` si el conductor no existe; bloquea al conductor
- [ ] T332 [S1] [US3] Impl (Green) `backend/app/aplicacion/casos_de_uso/actualizar_disponibilidad_desde_m4.py`, hasta que pase T331

### PR `feat/s1-caso-viaje-finalizado` (L7, T333–T335): Caso de uso de viaje finalizado

- [ ] T333 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_viaje_finalizado.py`: con puntaje, guarda el destino como ubicación (si no es anterior a la actual), suma el puntaje, cuenta 1 y devuelve `procesado`, `ubicacion_actualizada` y `puntaje_registrado` en verdadero; sin puntaje actualiza la ubicación y no toca los contadores (`puntaje_registrado` falso); con `fecha_finalizacion` anterior a la ubicación actual no la cambia (`ubicacion_actualizada` falso); `NoEncontrado` si el conductor no existe
- [ ] T334 [S1] [US4] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_viaje_finalizado.py`: idempotencia: el mismo viaje con los mismos datos devuelve la misma respuesta de la primera vez y no vuelve a sumar; el mismo `id_viaje` con otro `id_conductor`, destino, fecha o puntaje lanza `ViajeEnConflicto`; un puntaje fuera de 1 a 5 lanza `DatosInvalidos`
- [ ] T335 [S1] [US4] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_viaje_finalizado.py` y el resultado `ViajeFinalizadoResultado`: bloquea al conductor, registra con `registrar_si_no_existe` y aplica ubicación y puntaje solo si insertó, hasta que pasen T333 y T334

### PR `feat/s1-casos-solicitudes` (L8, T336–T340): Casos de uso de solicitudes

- [ ] T336 [P] [S1] [US5] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_solicitudes_conductor.py`: devuelve solo las solicitudes del conductor; el estado es el efectivo (una `PENDIENTE` vencida figura `VENCIDA`); el filtro `estado` se aplica sobre el estado efectivo, así `PENDIENTE` excluye a las vencidas y `VENCIDA` las incluye; sin solicitudes devuelve lista vacía; `NoEncontrado` si el conductor no existe
- [ ] T337 [S1] [US5] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_solicitudes_conductor.py`, hasta que pase T336
- [ ] T338 [S1] [US5] Test (Red) `backend/tests/unitarios/aplicacion/test_responder_solicitud.py`: aceptar una vigente la deja `ACEPTADO` con `respuesta` y la `hora_rta` del cliente, y deja al conductor no disponible con `actualizado` del `Reloj`; rechazar la deja `RECHAZADO` sin cambiar la disponibilidad; vencida lanza `SolicitudVencida` (aunque la `hora_rta` sea anterior) y no cambia nada; ya respondida lanza `SolicitudYaRespondida`; aceptar sin poder estar disponible lanza `ConductorNoHabilitado`; solicitud inexistente lanza `NoEncontrado`
- [ ] T339 [S1] [US8] Test (Red) `backend/tests/unitarios/aplicacion/test_responder_solicitud.py`: acceso: un conductor que no es el dueño lanza `AccesoProhibido` y no cambia nada; el operador puede responder la de cualquier conductor; bloquea primero al conductor y después a la solicitud (orden de bloqueos)
- [ ] T340 [S1] [US5] Impl (Green) `backend/app/aplicacion/casos_de_uso/responder_solicitud.py`: lee la solicitud, aplica `verificar_acceso`, bloquea al conductor y luego a la solicitud, revalida y aplica la respuesta, hasta que pasen T338 y T339

### PR `feat/s1-casos-vehiculo-i2` (L9, T341–T348): Casos de uso del vehículo: tipos de servicio y documentación

- [ ] T341 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_tipos_servicio_vehiculo.py`: devuelve cada tipo de servicio del vehículo con su `habilitado`; `NoEncontrado` si el vehículo no existe o es de otro conductor
- [ ] T342 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_tipos_servicio_vehiculo.py`, hasta que pase T341
- [ ] T343 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_documento_vehiculo.py`: guarda el documento y devuelve el estado `VIGENTE` o `VENCIDO` calculado con `reloj.hoy()`; vencimiento no posterior a la emisión lanza `DatosInvalidos`; `NoEncontrado` si el vehículo es de otro conductor
- [ ] T344 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_documento_vehiculo.py`, hasta que pase T343
- [ ] T345 [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_vehiculo.py`: el detalle incluye los documentos del vehículo con su estado calculado y una lista vacía si no tiene
- [ ] T346 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_vehiculo.py` y el resultado `VehiculoDetalle` en `resultados.py`, hasta que pase T345
- [ ] T347 [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_accionar_habilitacion_vehiculo.py`: aprobar un vehículo habilita todos sus tipos de servicio; suspender o rechazar los deshabilita; observar no los toca; el cambio queda en la misma transacción que el evento (decisión 9)
- [ ] T348 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/accionar_habilitacion_vehiculo.py`: sincronizar `habilitado` de los tipos de servicio con la acción, hasta que pase T347

### PR `feat/s1-casos-conductor-i2` (L10, T349–T352): Casos de uso del conductor: listado y campos nuevos

- [ ] T349 [S1] [US7] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_conductores.py`: el filtro `tipo_servicio` devuelve los conductores con al menos un vehículo con ese tipo habilitado; se combina con `habilitado`, `disponible` y `tipo_vehiculo` en conjunción; sin coincidencias devuelve lista vacía; el caso de uso no recibe `latitud` ni `longitud`
- [ ] T350 [S1] [US7] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_conductores.py`: parámetro `tipo_servicio`, hasta que pase T349
- [ ] T351 [S1] [US7] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_conductor.py` y `test_listar_conductores.py`: el conductor devuelto trae `id_vehiculo_activo`, `suma_puntajes`, `cantidad_calificaciones` y `puntaje_promedio` con los valores guardados
- [ ] T352 [S1] [US7] Impl (Green) `backend/app/aplicacion/casos_de_uso/resultados.py` y los casos de uso `obtener_conductor` y `listar_conductores` si hace falta, hasta que pase T351

### PR `feat/s1-sql-conductor-i2` (L11, T353–T356): Repositorio SQL del conductor con los campos nuevos

- [ ] T353 [S1] [US7] Test (Red) `backend/tests/integracion/repositorios/test_sql_conductores_i2.py` (PostgreSQL real): guardar y obtener persisten `id_vehiculo_activo` (FK a `vehiculo`, nulo), `fecha_ultimo_cambio_estado` (timestamptz, nulo), `suma_puntajes` y `cantidad_calificaciones` (enteros no negativos, por defecto 0); la unidad de trabajo bloquea al conductor y devuelve los campos nuevos
- [ ] T354 [S1] [US7] Test (Red) `backend/tests/integracion/repositorios/test_sql_listar_conductores.py`: el filtro `tipo_servicio` devuelve conductores con al menos un vehículo con ese tipo `habilitado`; se combina con los filtros existentes; carga vehículos y tipos de servicio en consultas agrupadas, sin una consulta por fila
- [ ] T355 [S1] [US7] Impl (Green) `backend/app/infraestructura/repositorios/sql_conductores.py`: mapeo de los campos nuevos entre el modelo ORM de Datos y seguridad y el dominio, y filtro `tipo_servicio`, hasta que pasen T353 y T354
- [ ] T356 [S1] [US7] Impl (Green) `backend/app/infraestructura/repositorios/sql_unidad_de_trabajo.py`: `bloquear_conductor` devuelve el conductor con los campos nuevos

### PR `feat/s1-sql-solicitud-viaje` (L12, T357–T362): Repositorios SQL de solicitudes y viajes finalizados

- [ ] T357 [S1] [US5] Test (Red) `backend/tests/integracion/repositorios/test_sql_solicitudes.py`: guardar y obtener una solicitud con `estado` (`PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`), `vence_en`, `respuesta` y `hora_rta`; listar por conductor; `bloquear_solicitud` devuelve la fila bloqueada; una respuesta con `respuesta` y `hora_rta` desparejados o con un `estado` que no coincide es rechazada por la base (`CHECK`)
- [ ] T358 [S1] [US5] Impl (Green) `backend/app/infraestructura/repositorios/sql_solicitudes.py` y `bloquear_solicitud` en `sql_unidad_de_trabajo.py`, hasta que pase T357
- [ ] T359 [S1] [US4] Test (Red) `backend/tests/integracion/repositorios/test_sql_viajes_finalizados.py`: `registrar_si_no_existe` inserta con `INSERT ... ON CONFLICT DO NOTHING` y devuelve verdadero la primera vez y falso con el mismo `id_viaje`; `obtener` devuelve el primero; `puntaje_conductor` fuera de 1 a 5 es rechazado por el `CHECK`; `id_conductor` inexistente es rechazado por la FK
- [ ] T360 [S1] [US4] Impl (Green) `backend/app/infraestructura/repositorios/sql_viajes_finalizados.py` y su cableado en `sql_unidad_de_trabajo.py`, hasta que pase T359
- [ ] T361 [S1] [US4] Test (Red) `backend/tests/integracion/test_casos_de_uso_sql.py`: con la unidad de trabajo SQL, `registrar_viaje_finalizado` repetido (mismos datos) suma el puntaje una sola vez y devuelve la misma respuesta; `responder_solicitud` acepta una vigente, deja al conductor no disponible y rechaza una segunda respuesta con `SolicitudYaRespondida`
- [ ] T362 [S1] [US4] Impl (Green) ajustes mínimos en `sql_unidad_de_trabajo.py` y en los repositorios nuevos hasta que pase T361

### PR `feat/s1-sql-documentos-vehiculo` (L13, T363–T366): Repositorio SQL de documentos del vehículo y tipos de servicio

- [ ] T363 [S1] [US6] Test (Red) `backend/tests/integracion/repositorios/test_sql_documentos_vehiculo.py`: guardar un documento (`tipo` `SEGURO`, `CEDULA_VERDE` o `VTV`; `numero` obligatorio; `entidad_emisora` opcional; `fecha_vencimiento` posterior a `fecha_emision`; `url_archivo` obligatoria) y listar por vehículo y por lote; un `tipo` inválido o un vencimiento anterior a la emisión es rechazado por el `CHECK`; la FK a `vehiculo` es `ON DELETE RESTRICT`
- [ ] T364 [S1] [US6] Impl (Green) `backend/app/infraestructura/repositorios/sql_documentos_vehiculo.py` y su cableado en `sql_unidad_de_trabajo.py`, hasta que pase T363
- [ ] T365 [S1] [US6] Test (Red) `backend/tests/integracion/repositorios/test_sql_vehiculos.py`: guardar un vehículo persiste el cambio de `habilitado` de sus tipos de servicio, y `obtener` y `listar_por_conductores` los devuelven actualizados
- [ ] T366 [S1] [US6] Impl (Green) `backend/app/infraestructura/repositorios/sql_vehiculos.py`: persistir `habilitado` de los tipos de servicio, hasta que pase T365

---

## Fase 2: Stack 2 — Servidor HTTP

**Meta**: seguridad por rol, acceso propio del conductor, los 9 endpoints nuevos y los esquemas ampliados, contra casos de uso simulados (`CasoDeUsoFalso`) y tokens firmados en el test. Cada PR de esta fase agrega a `ESPERADOS` de `backend/tests/api/test_paridad_rutas.py` los pares (ruta, método) que incorpora, con el test que falla primero.

### PR `feat/s2-seguridad-rol-servicio` (V1, T367–T374): Rol servicio, claim del conductor y dependencias de acceso

- [ ] T367 [S2] [US1] Test (Red) `backend/tests/api/conftest.py`: `crear_token` acepta varios roles e `id_conductor`; fixtures `headers_servicio` (solo rol `servicio`) y `headers_conductor_de(id)` (rol `conductor` con ese `id_conductor`); `test_fixtures_de_acceso` verifica el contenido de cada token
- [ ] T368 [S2] [US1] Impl (Green) `backend/tests/api/conftest.py`: los ayudantes anteriores, sin cambiar las fixtures existentes, hasta que pase T367
- [ ] T369 [S2] [US1] Test (Red) `backend/tests/api/test_seguridad_servicio.py`: un token con solo el rol `servicio` es aceptado; un token sin ningún rol reconocido responde `403`; se lee el claim `id_conductor` entero; un `id_conductor` booleano o no numérico se trata como ausente
- [ ] T370 [S2] [US1] Impl (Green) `backend/app/api/seguridad.py`: agregar `servicio` a `ROLES_VALIDOS` y construir la `Identidad` desde el payload, hasta que pase T369
- [ ] T371 [S2] [US1] Test (Red) `backend/tests/api/test_dependencias_acceso.py` (aplicación mínima de prueba): `requerir_servicio` responde `403` con el mensaje "Se requiere el rol servicio" a conductor y operador; `requerir_operador_o_servicio`; `requerir_conductor_propio_u_operador(id)`; `requerir_conductor_propio_operador_o_servicio(id)`; el chequeo por id responde `403` `ACCESO_PROHIBIDO` antes de buscar el recurso; `requerir_operador` existente no cambia
- [ ] T372 [S2] [US1] Impl (Green) `backend/app/api/seguridad.py`: las dependencias de acceso, una por patrón de la matriz y apoyadas en `aplicacion/politicas/acceso.py`, hasta que pase T371
- [ ] T373 [S2] [US1] Test (Red) `backend/tests/api/test_errores.py`: `AccesoProhibido` → `403` `ACCESO_PROHIBIDO`; `RolNoAutorizado` → `403` `SIN_PERMISOS`; `SolicitudYaRespondida` → `409` `SOLICITUD_YA_RESPONDIDA`; `ViajeEnConflicto` → `409` `VIAJE_EN_CONFLICTO`; `SolicitudVencida` → `410` `SOLICITUD_VENCIDA`; `ConductorNoHabilitado` → `422` `CONDUCTOR_NO_HABILITADO`
- [ ] T374 [S2] [US1] Impl (Green) `backend/app/api/errores.py`: agregar los seis errores a `MAPEO_ERRORES_DOMINIO`, hasta que pase T373

### PR `feat/s2-acceso-endpoints-existentes` (V2, T375–T380): Acceso por rol y propio en los 10 endpoints de la Iteración 1

- [ ] T375 [S2] [US8] Test (Red) `backend/tests/api/test_acceso_propio.py`: para las operaciones 3, 4, 6, 7, 8 y 9 de la matriz de [contracts/token-jwt.md](./contracts/token-jwt.md): el conductor con su propio id obtiene la respuesta normal; con el id de otro responde `403` `ACCESO_PROHIBIDO` sin llamar al caso de uso, aunque el otro conductor no exista; un token de conductor sin `id_conductor` responde `403`; el operador accede a cualquiera; el servicio lee las operaciones 3, 4, 8 y 9 y recibe `403` en las escrituras 6 y 7
- [ ] T376 [S2] [US1] Test (Red) `backend/tests/api/test_acceso_propio.py`: `POST /conductores` responde `403` al rol `servicio` y funciona para operador y conductor; las acciones de habilitación (operaciones 5 y 10) siguen siendo solo del operador y responden `403` al conductor y al servicio
- [ ] T377 [S2] [US7] Test (Red) `backend/tests/api/test_acceso_propio.py`: `GET /conductores` responde `403` `SIN_PERMISOS` a un conductor y `200` a operador y a servicio
- [ ] T378 [S2] [US8] Impl (Green) `backend/tests/api/conftest.py`: la fixture `headers_conductor` pasa a incluir `id_conductor=1`, el id de `conductor_de_prueba()`, porque el requisito de acceso propio (FR-040) lo exige; no cambia ninguna aserción de los tests existentes
- [ ] T379 [S2] [US7] Impl (Green) `backend/tests/api/test_conductores_listar.py`: los tests del listado pasan a usar `headers_operador` en lugar de `headers_conductor`, porque `GET /conductores` ya no es del conductor (FR-041, decisión de la clarificación); las aserciones no cambian
- [ ] T380 [S2] [US8] Impl (Green) `backend/app/api/routers/conductores.py`, `habilitacion.py`, `documentacion.py`, `vehiculos.py` y `vehiculos_habilitacion.py`: aplicar la dependencia de acceso que corresponde a cada operación según la matriz, hasta que pasen T375 a T377

### PR `feat/s2-estado-ubicacion` (V3, T381–T388): Endpoints de estado y ubicación del conductor

- [ ] T381 [S2] [US2] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar a `ESPERADOS` los pares `GET /api/v1/conductores/{id_conductor}/estado` (`obtenerEstadoConductor`), `PATCH` en la misma ruta (`actualizarEstadoConductor`) y `GET /api/v1/conductores/{id_conductor}/ubicacion` (`obtenerUbicacionConductor`)
- [ ] T382 [S2] [US2] Test (Red) `backend/tests/api/test_configuracion.py`: `UBICACION_SIMULADA_LATITUD` y `UBICACION_SIMULADA_LONGITUD` valen por defecto `-27.4511` y `-58.9867`, se pueden cambiar por variable de entorno y fuera de rango (latitud -90 a 90, longitud -180 a 180) producen un error de validación
- [ ] T383 [S2] [US2] Impl (Green) `backend/app/api/configuracion.py`: las dos variables opcionales con esos valores por defecto, hasta que pasen T381 y T382
- [ ] T384 [S2] [US2] Test (Red) `backend/tests/api/test_esquemas.py`: `EstadoConductor` con `id_conductor`, `conectado`, `disponible`, `id_vehiculo_activo` (nulo) y `actualizado`, y sin campos de ubicación; `UbicacionConductor` con los tres campos que admiten nulo; `EstadoConductorRequest` exige al menos un campo y `latitud` y `longitud` van juntas y en rango
- [ ] T385 [S2] [US2] Impl (Green) `backend/app/api/esquemas/estado.py` con esos esquemas, hasta que pase T384
- [ ] T386 [S2] [US2] Test (Red) `backend/tests/api/test_estado_ubicacion.py`: las tres operaciones según la matriz de roles; el `PATCH` responde `400` con cuerpo vacío o una sola coordenada, `422` `CONDUCTOR_NO_HABILITADO` y `404`; con el rol `servicio` el `PATCH` responde `403`; los casos de uso reciben los argumentos esperados
- [ ] T387 [S2] [US2] Impl (Green) `backend/app/api/dependencias.py` (proveedores de `obtener_estado_conductor`, `obtener_ubicacion_conductor` y `actualizar_estado_conductor`, con la ubicación simulada de la configuración) y `backend/app/api/routers/estado.py`, hasta que pasen T381 y T386
- [ ] T388 [S2] [US2] Impl (Green) `backend/app/api/main.py`: registrar `estado.router` en `ROUTERS`

### PR `feat/s2-integracion-m4` (V4, T389–T392): Endpoint de disponibilidad desde M4

- [ ] T389 [S2] [US3] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `PATCH /api/v1/integraciones/m4/conductores/{id_conductor}/disponibilidad` (`actualizarDisponibilidadDesdeM4`)
- [ ] T390 [S2] [US3] Test (Red) `backend/tests/api/test_integracion_m4.py`: solo el rol `servicio` (conductor y operador reciben `403` con "Se requiere el rol servicio"); `disponible` y `actualizado` obligatorios y `motivo` solo `RESERVADO`, `OCUPADO` o `LIBERADO` (si no, `400`); `200` con el estado; `422` `CONDUCTOR_NO_HABILITADO`; `404`; sin token `401`
- [ ] T391 [S2] [US3] Impl (Green) `backend/app/api/esquemas/integracion.py` (`DisponibilidadM4Request`), el proveedor de `actualizar_disponibilidad_desde_m4` en `dependencias.py` y el router `backend/app/api/routers/integraciones.py`, hasta que pasen T389 y T390
- [ ] T392 [S2] [US3] Impl (Green) `backend/app/api/main.py`: registrar `integraciones.router` en `ROUTERS`

### PR `feat/s2-integracion-m6` (V5, T393–T395): Endpoint de viaje finalizado desde M6

- [ ] T393 [S2] [US4] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `POST /api/v1/integraciones/m6/viajes/{id_viaje}/finalizacion` (`recibirViajeFinalizadoM6`)
- [ ] T394 [S2] [US4] Test (Red) `backend/tests/api/test_integracion_m6.py`: solo el rol `servicio`; `id_conductor`, `estado` (solo `FINALIZADO`), `destino` y `fecha_finalizacion` obligatorios; `puntaje_conductor` de 1 a 5 o nulo (fuera de rango o `estado` distinto responden `400`); `200` con `procesado`, `ubicacion_actualizada` y `puntaje_registrado`; `404` y `409` `VIAJE_EN_CONFLICTO`; el `id_viaje` de la ruta llega al caso de uso
- [ ] T395 [S2] [US4] Impl (Green) `backend/app/api/esquemas/integracion.py` (`ViajeFinalizadoM6Request` y `ViajeFinalizadoM3Response`), el proveedor de `registrar_viaje_finalizado` y la ruta en `routers/integraciones.py`, hasta que pasen T393 y T394

### PR `feat/s2-solicitudes` (V6, T396–T400): Endpoints de solicitudes

- [ ] T396 [S2] [US5] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `GET /api/v1/conductores/{id_conductor}/solicitudes` (`listarSolicitudesConductor`) y `POST /api/v1/solicitudes/{id_solicitud}` (`responderSolicitud`)
- [ ] T397 [S2] [US5] Test (Red) `backend/tests/api/test_esquemas.py`: `Solicitud` con `id`, `id_conductor`, `id_viaje` (nulo), `estado`, `vence_en`, `respuesta` (nulo) y `hora_rta` (nulo); `RespuestaSolicitudRequest` con `respuesta` (`ACEPTADO` o `RECHAZADO`) y `hora_rta` obligatorias
- [ ] T398 [S2] [US5] Test (Red) `backend/tests/api/test_solicitudes.py`: el listado admite el filtro `estado` y un valor inválido responde `400`; el conductor lista solo las suyas; responder devuelve la solicitud y mapea `404`, `403` `ACCESO_PROHIBIDO`, `409` `SOLICITUD_YA_RESPONDIDA`, `410` `SOLICITUD_VENCIDA` y `422` `CONDUCTOR_NO_HABILITADO`; el rol `servicio` recibe `403`; el caso de uso recibe la identidad de quien responde
- [ ] T399 [S2] [US5] Impl (Green) `backend/app/api/esquemas/solicitud.py`, los proveedores de `listar_solicitudes_conductor` y `responder_solicitud` en `dependencias.py` y el router `backend/app/api/routers/solicitudes.py`, hasta que pasen T396 a T398
- [ ] T400 [S2] [US5] Impl (Green) `backend/app/api/main.py`: registrar `solicitudes.router` en `ROUTERS`

### PR `feat/s2-vehiculo-i2` (V7, T401–T404): Endpoints de tipos de servicio y documentación del vehículo

- [ ] T401 [S2] [US6] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `GET /api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` (`listarTiposServicioVehiculo`) y `POST` en `.../vehiculos/{id_vehiculo}/documentacion` (`crearDocumentacionVehiculo`)
- [ ] T402 [S2] [US6] Test (Red) `backend/tests/api/test_esquemas.py`: `TipoServicioHabilitado` (`tipo` y `habilitado`); `DocumentoVehiculoCreate` con `tipo` (`SEGURO`, `CEDULA_VERDE` o `VTV`), `numero`, `entidad_emisora` opcional, fechas y `url_archivo` con formato de URL; `DocumentoVehiculo` con `id_vehiculo` y `estado`; `Vehiculo.documentos` incluye los documentos con su estado
- [ ] T403 [S2] [US6] Test (Red) `backend/tests/api/test_vehiculos_i2.py`: tipos de servicio según la matriz de roles y `404`; el documento responde `201` con el estado calculado; `400` con tipo inválido o URL inválida; `422` con vencimiento anterior a la emisión; `404` si el vehículo es de otro conductor; `servicio` recibe `403` al crear el documento
- [ ] T404 [S2] [US6] Impl (Green) `backend/app/api/esquemas/vehiculo.py` y `documento.py`, los proveedores de `listar_tipos_servicio_vehiculo` y `registrar_documento_vehiculo` en `dependencias.py` y las dos rutas en `backend/app/api/routers/vehiculos.py`, hasta que pasen T401 a T403

### PR `feat/s2-conductor-campos-nuevos` (V8, T405–T412): Campos nuevos del conductor, filtro de tipo de servicio y versión 1.1.0

- [ ] T405 [S2] [US7] Test (Red) `backend/tests/api/test_esquemas.py`: `Conductor` incluye `puntaje_promedio` (número de 1 a 5 o nulo) y `cantidad_calificaciones` (entero no negativo, por defecto 0); `ConductorConUbicacion` incluye `id_vehiculo_activo` (nulo); el alta (`POST /conductores`) sigue devolviendo `Conductor` sin ubicación
- [ ] T406 [S2] [US7] Impl (Green) `backend/app/api/esquemas/conductor.py`: los campos nuevos y su mapeo desde el detalle, hasta que pase T405
- [ ] T407 [S2] [US7] Test (Red) `backend/tests/api/test_conductores_listar.py`: `tipo_servicio` llega al caso de uso; `latitud` y `longitud` siguen aceptándose (solo juntas y en rango) pero no llegan al caso de uso ni cambian el resultado; una sola de las dos responde `400`; los campos nuevos aparecen en la respuesta
- [ ] T408 [S2] [US7] Impl (Green) `backend/app/api/routers/conductores.py`: pasar `tipo_servicio` al caso de uso y descartar `latitud` y `longitud`, hasta que pase T407
- [ ] T409 [S2] [US7] Test (Red) `backend/tests/api/test_main.py`: la aplicación declara la versión `1.1.0`
- [ ] T410 [S2] [US7] Impl (Green) `backend/app/api/main.py`: `version="1.1.0"`, hasta que pase T409
- [ ] T411 [S2] [US7] Test (Red) `backend/tests/api/test_paridad_rutas.py`: cambiar el nombre de las pruebas de "10" a "19" y exigir que la aplicación genere exactamente las 19 operaciones del contrato, con sus `operationId` y los pares que sumaron V3 a V7
- [ ] T412 [S2] [US7] Impl (Green) completar lo que falte para que pase T411 y ejecutar la suite completa con `--cov-fail-under=65`

---

## Fase 3: Cierre

**Meta**: dejar documentado y verificado lo que termina la parte de Backend.

### PR `docs/backend-cierre-i2` (C1, T413–T416): Documentación y verificación final de Backend

- [ ] T413 Actualizar `README.md`: la tabla de endpoints marca como implementados los 19 y la sección de la API refleja el rol `servicio`, el acceso propio del conductor y el listado solo para operador y servicio
- [ ] T414 Recorrer [quickstart.md](./quickstart.md) contra el entorno real una vez que L11 a L13 y la migración de Datos y seguridad están en `dev`, y anotar cualquier diferencia
- [ ] T415 Informar a Testing el valor propuesto para el umbral de cobertura (70 %) y los resultados de `pytest --cov` sobre lo implementado
- [ ] T416 PR de contrato aparte (`docs/contrato-roles-bearer`): ajustar en `docs/contract/openapi.yaml` la descripción de roles de `bearerAuth`, que hoy dice que el conductor consulta conductores y vehículos, para que el listado figure como de operador y servicio

---

## Dependencias entre PRs

- **L1, L2 y L3** no dependen de nadie y se pueden hacer en paralelo.
- **L4** necesita las entidades de L1 y L2. **V1** necesita la política de L3 y los errores de L2 y L3.
- **L5, L7, L9 y L10** necesitan los puertos y los fakes de L4. **V2** necesita V1.
- **L6 y L8** necesitan L5 (reutilizan el cambio de estado). **V3, V5, V7 y V8** necesitan V1 y el caso de uso de su grupo (L5, L7, L9 y L10).
- **V4 y V6** necesitan V1 y L6 y L8.
- **L11** necesita L4 y la migración de Datos y seguridad; **L12 y L13** necesitan L11.
- En cada PR, la tarea de test va siempre antes de su implementación.

## Verificación por historia

| Historia | Cómo se comprueba que está cumplida |
|---|---|
| US1 Acceso por rol y servicio | Un token `servicio` lee conductores y no hace acciones de operador; las integraciones responden `403` a otros roles; sin token `401` |
| US2 Estado y ubicación | Se actualiza el estado de un conductor aprobado y se consulta; sin ubicación, `200` con los tres campos nulos; el conductor sin ubicación que se conecta recibe la simulada |
| US3 Disponibilidad desde M4 | Un pedido viejo no cambia nada; uno repetido da el mismo resultado; `disponible = true` sin cumplir la regla da `422` |
| US4 Viaje finalizado | El puntaje suma una sola vez ante reintentos; sin puntaje solo cambia la ubicación; el mismo viaje con otros datos da `409` |
| US5 Solicitudes | Vigente se responde; vencida da `410`; ya respondida da `409`; aceptar deja al conductor no disponible |
| US6 Vehículo | Tipos de servicio con su `habilitado`; documento con estado calculado; `422` con vencimiento anterior a la emisión |
| US7 Listado y campos nuevos | `tipo_servicio` filtra; `latitud` y `longitud` no cambian el resultado; `puntaje_promedio` e `id_vehiculo_activo` salen en la respuesta; versión 1.1.0 |
| US8 Acceso propio | Un conductor recibe `403` sobre datos de otro, con el mismo resultado exista o no ese conductor; el operador accede a todo |

## Estrategia de implementación

1. **Primer hito (MVP)**: US1 y US2 de punta a punta con fakes: L1, L3, L4, L5, V1 y V3. M4 ya puede leer estado y ubicación y el conductor actualizarlos.
2. **Segundo hito**: US3 y US4 (integraciones de M4 y M6): L6, L7, V4 y V5.
3. **Tercer hito**: US5, US6, US7 y US8: solicitudes, vehículo, listado y acceso propio en los endpoints existentes (L8 a L10, V2, V6 a V8).
4. **Cierre**: repositorios SQL (L11 a L13) cuando llegue la migración, y C1.

Cada hito deja la rama `dev` en verde.

## Notas

- **Total**: 116 tareas en 22 PRs (13 de lógica, 8 de servidor y 1 de cierre).
- **Paridad de rutas**: cada PR de servidor agrega sus pares a `ESPERADOS` de `backend/tests/api/test_paridad_rutas.py` con su test en rojo primero. La lista llega a las 19 operaciones en V8.
- **No incluido** (otros grupos): migración, seed, Keycloak, pruebas de contrato y de concurrencia de punta a punta.

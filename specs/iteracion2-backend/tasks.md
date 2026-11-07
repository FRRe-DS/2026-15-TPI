# Tareas: Iteración 2 — Backend de M3 (Conductores y Vehículos)

**Entrada**: Documentos de diseño en `specs/iteracion2-backend/`
**Requisitos previos**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Pruebas**: obligatorias en todo el proyecto (constitución, principio I). Cada tarea de implementación va precedida por su tarea de **test que falla primero** (Red → Green → Refactor) y nombra el test que cumple. Los tests no se modifican para hacerlos pasar. Las únicas excepciones son los cambios de requisito del spec (acceso propio del conductor y listado solo para operador y servicio), que se aclaran en las tareas T370 y T371 con el motivo.

**Numeración**: las tareas arrancan en T301 para no chocar con T001–T125 de la [Iteración 1](../iteracion1/tasks.md).

**Organización**: las tareas se agrupan por **stack** y, dentro de cada stack, por **PR**. Cada PR tiene una sola responsabilidad y cada tarea lleva su historia de usuario cuando corresponde.

**Cambio de contrato 1.2.0**: se sacaron las operaciones de integración con M4 y M6 y se unificaron `conectado` y `disponible` en `estado`. Las historias US3 y US4 quedaron retiradas y esta lista ya no las incluye; el spec conserva sus números.

## Formato: `- [ ] ID [P] [Stack] [Historia] Descripción con ruta`

- **[P]**: se puede hacer en paralelo con la tarea anterior (archivos distintos, sin depender de tareas incompletas).
- **[S1]** lógica y **[S2]** servidor: stack dueño de la tarea (ver el [plan](./plan.md)). Las de cierre no llevan stack.
- **[US1]…[US8]**: historia de [spec.md](./spec.md): US1 acceso por rol y servicio de solo lectura, US2 estado y ubicación, US5 solicitudes, US6 vehículo, US7 listado y campos nuevos, US8 acceso propio del conductor (US3 y US4 están retiradas).
- Las tareas de **test** dicen "Test (Red)"; las de **implementación**, "Impl (Green)" y nombran el test que cumplen.

## PRs (todas contra `dev`)

Una PR por fila. Las estimaciones son de líneas de diff con tests; una PR que llegue a 1500–2000 líneas sigue siendo aceptable y no hace falta partirla.

| PR | Rama | Tareas | Depende de | Líneas (est.) |
|---|---|---|---|---|
| L1 | `feat/s1-dominio-conductor-estado` | T301–T309 | — | 450 |
| L2 | `feat/s1-dominio-solicitud-documento` | T310–T313 | — | 400 |
| L3 | `feat/s1-politica-acceso` | T314–T317 | — | 250 |
| L4 | `feat/s1-puertos-fakes-i2` | T318–T322 | L1, L2 | 400 |
| L5 | `feat/s1-casos-estado-ubicacion` | T323–T329 | L4 | 500 |
| L6 | `feat/s1-casos-solicitudes` | T330–T334 | L5 | 500 |
| L7 | `feat/s1-casos-vehiculo-i2` | T335–T342 | L4 | 550 |
| L8 | `feat/s1-casos-conductor-i2` | T343–T346 | L4 | 350 |
| L9 | `feat/s1-sql-conductor-i2` | T347–T350 | L4 y la migración y los modelos de Datos y seguridad | 500 |
| L10 | `feat/s1-sql-solicitud-documentos` | T351–T358 | L9 | 550 |
| V1 | `feat/s2-seguridad-rol-servicio` | T359–T366 | L3 | 500 |
| V2 | `feat/s2-acceso-endpoints-existentes` | T367–T372 | V1 | 550 |
| V3 | `feat/s2-estado-ubicacion` | T373–T380 | V1 y L5 | 550 |
| V4 | `feat/s2-solicitudes` | T381–T385 | V1 y L6 | 450 |
| V5 | `feat/s2-vehiculo-i2` | T386–T389 | V1 y L7 | 450 |
| V6 | `feat/s2-conductor-campos-nuevos` | T390–T397 | V1 y L8 | 450 |
| C1 | `docs/backend-cierre-i2` | T398–T401 | todas las anteriores | 150 |

## Olas de integración

Las PRs de una misma ola no dependen entre sí y se pueden abrir en paralelo.

```text
Ola 1:  L1  L2  L3
Ola 2:  L4  V1
Ola 3:  L5  L7  L8  V2
Ola 4:  L6  V3  V5  V6
Ola 5:  V4
Ola 6:  L9 → L10              (esperan la migración y los modelos de Datos y seguridad)
Cierre: C1
```

- Las olas 1 a 5 trabajan con repositorios en memoria y no esperan a nadie. L1 deja la traducción de `estado` al esquema vigente en `sql_conductores.py` (T309: mapeo directo si la migración ya está integrada, adaptación transitoria si no) y L4 deja la unidad de trabajo SQL con los repositorios nuevos marcados como pendientes (T322), para que `dev` siga en verde hasta la ola 6.
- Hasta que L9 y L10 estén integradas, los endpoints nuevos solo funcionan con los repositorios en memoria y `OCUPADO` no se distingue de `CONECTADO` en la base. Si la migración de Datos y seguridad ya está en `dev` antes de la ola 4, conviene adelantar L9 y L10.
- Ventana V5 / L10: V5 (ola 4) expone `Vehiculo.documentos` y el seed de Datos y seguridad (T511) siembra documentos del vehículo, pero hasta L10 la unidad de trabajo SQL devuelve la lista vacía al listar documentos por vehículo (marcador de T322). Si V5 y T511 se integran antes que L10, el `GET` del vehículo responde `documentos: []` aunque la base tenga datos, y el `POST` de documentos responde 500. V5 debe integrarse después de L10 o esa ventana debe aceptarse de forma explícita; quien haga V5 o recorra el quickstart antes de L10 no debe tomarlo por un bug de V5, y T399 lo confirma contra el entorno real.
- Cada PR se abre desde `dev` ya actualizada.

## Dependencias con otros grupos

| Grupo | Qué necesita Backend | Hasta que llegue |
|---|---|---|
| Datos y seguridad | Migración y modelos con las columnas y tablas del [data-model.md](./data-model.md), incluido el paso de `conectado` y `disponible` a `estado` (issue #36) | L9 y L10 |
| Datos y seguridad | Rol `servicio`, cuenta técnica de M4 y claim `id_conductor` del conductor | La verificación contra el entorno real (C1) |
| Testing | Ampliar las pruebas de contrato a las 17 operaciones, el umbral de cobertura y los casos de concurrencia de punta a punta (tareas T601+ en [su plan](../iteracion2-testing/plan.md)) | Después de la ola 6 |
| Testing | Reutiliza los helpers `headers_servicio` y `headers_conductor_de` de V1 en `backend/tests/api/conftest.py`; Testing no crea otros | Después de V1 |
| Datos y seguridad | Rate limiting con Redis (T515–T523, T529): su T517 se conecta en `seguridad.py` **después de V1 (T364)**; Backend no agrega nada de limitación | Después de V1 |
| Frontend | Pasar de `conectado` y `disponible` a `estado` en tipos y pantallas | Después de V6 |

**Puntos de sincronización**: `docs/contract/openapi.yaml` · [data-model.md](./data-model.md) · [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) · [contracts/token-jwt.md](./contracts/token-jwt.md) · [contracts/errores.md](./contracts/errores.md).

**Dueños de archivos**: ver la tabla de [plan.md](./plan.md). Cada tarea toca solo archivos de su stack, salvo las que lo aclaran.

---

## Fase 1: Stack 1 — Lógica del backend

**Meta**: dominio, política de acceso, puertos, casos de uso y repositorios SQL de los 7 endpoints nuevos y de las adaptaciones, con TDD y sin depender de FastAPI. Las PRs L1 a L8 trabajan con repositorios en memoria y no esperan a nadie; L9 y L10 esperan la migración y los modelos de Datos y seguridad.

### PR `feat/s1-dominio-conductor-estado` (L1, T301–T309): Dominio del conductor: estado unificado y puntaje

- [X] T301 [S1] [US7] Test (Red) `backend/tests/unitarios/dominio/test_conductor.py`: un conductor nuevo queda con `estado` `DESCONECTADO`, `id_vehiculo_activo` nulo, `fecha_ultimo_cambio_estado` nula, `suma_puntajes` 0 y `cantidad_calificaciones` 0; `puntaje_promedio` es nulo con cantidad 0; con calificaciones es `suma / cantidad` en 2 decimales, mitad hacia arriba (14/3 → 4.67; 9/2 → 4.5); los totales negativos o una cantidad 0 con suma distinta de 0 lanzan `DatosInvalidos`
- [X] T302 [S1] [US7] Impl (Green) `backend/app/dominio/conductor.py`: enum `EstadoConductor` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) y campo `estado` en lugar de `conectado` y `disponible`, campos nuevos con esos valores por defecto y propiedad `puntaje_promedio` calculada con `Decimal`; propiedades de compatibilidad `conectado` y `disponible` derivadas de `estado` para no romper el código existente, hasta que pase T301
- [X] T303 [S1] [US2] Test (Red) `backend/tests/unitarios/dominio/test_conductor.py`: `fijar_ubicacion(latitud, longitud, ahora)` guarda las coordenadas y `fecha_act_ubic = ahora`; rechaza una latitud fuera de -90 a 90 o una longitud fuera de -180 a 180 con `DatosInvalidos`; `tiene_ubicacion` es falso con los tres campos nulos
- [X] T304 [S1] [US2] Impl (Green) `backend/app/dominio/conductor.py`: `fijar_ubicacion` y `tiene_ubicacion` hasta que pase T303
- [X] T305 [S1] [US2] Test (Red) `backend/tests/unitarios/dominio/test_disponibilidad.py`: `puede_quedar_disponible(conductor, vehiculo_activo)` es verdadero solo con conductor `APROBADA` y vehículo activo existente y `APROBADA`; pedir `DISPONIBLE` sin cumplirlo lanza `ConductorNoHabilitado`; pedir `DISPONIBLE` estando `DESCONECTADO`, `CONECTADO` u `OCUPADO` y cumpliendo la regla deja `DISPONIBLE`; pedir `DESCONECTADO` o `CONECTADO` se acepta siempre y desde cualquier estado; quitar el vehículo activo (`None`) o pasar a uno no `APROBADA` estando `DISPONIBLE` deja `CONECTADO`; esos mismos cambios estando `CONECTADO` u `OCUPADO` no cambian el estado; un pedido que no cambia nada no toca `fecha_ultimo_cambio_estado`; si cambia el estado o el vehículo activo, `fecha_ultimo_cambio_estado = ahora`; cambiar solo la ubicación no la toca
- [X] T306 [S1] [US2] Impl (Green) `backend/app/dominio/errores.py` (`ConductorNoHabilitado`) y `backend/app/dominio/disponibilidad.py` (`puede_quedar_disponible` y `aplicar_cambio_estado(conductor, vehiculo_activo, *, estado, id_vehiculo_activo, ahora)`, que distingue "no informado" de `None` y devuelve si hubo cambio), hasta que pase T305
- [X] T307 [S1] [US5] Test (Red) `backend/tests/unitarios/dominio/test_disponibilidad.py`: `marcar_ocupado(conductor, vehiculo_activo, ahora)` deja `OCUPADO` y `fecha_ultimo_cambio_estado = ahora` si el conductor está `CONECTADO` o `DISPONIBLE`, `APROBADA` y con vehículo activo `APROBADA`; si está `DESCONECTADO` u `OCUPADO`, o no cumple la regla, lanza `ConductorNoHabilitado` y no cambia nada
- [X] T308 [S1] [US5] Impl (Green) `backend/app/dominio/disponibilidad.py`: `marcar_ocupado`, hasta que pase T307
- [X] T309 [S1] Impl (Green) `backend/app/infraestructura/repositorios/sql_conductores.py` y los demás lugares que construyen o leen `Conductor` con `conectado` y `disponible`: adaptación transitoria entre `estado` y las columnas actuales (`DESCONECTADO` ↔ `conectado` falso; `CONECTADO` y `OCUPADO` ↔ `conectado` verdadero y `disponible` falso; `DISPONIBLE` ↔ ambos verdaderos), para que la suite siga en verde hasta L9; `OCUPADO` no se distingue de `CONECTADO` en la base hasta que llegue la migración. **Orden acordado con Datos y seguridad**: la migración `0002` entra primero en `dev` (ver [su plan](../iteracion2-seguridad/plan.md)); en ese caso Datos y seguridad ya dejó en `sql_conductores.py` una traducción entre los booleanos del dominio anterior y la columna `estado`, y esta tarea la reemplaza por el mapeo directo de `estado` del dominio, sin adaptación transitoria. La adaptación entre `estado` y las columnas viejas solo se escribe si L1 se integra antes que la migración

### PR `feat/s1-dominio-solicitud-documento` (L2, T310–T313): Dominio de solicitud y documento de vehículo

- [X] T310 [P] [S1] [US5] Test (Red) `backend/tests/unitarios/dominio/test_solicitud.py`: estados `PENDIENTE`, `ACEPTADO`, `RECHAZADO` y `VENCIDA`; `estado_efectivo(ahora)` devuelve `PENDIENTE` si `ahora <= vence_en` (la igualdad es válida) y `VENCIDA` si `ahora > vence_en`; los demás estados no cambian; `responder(respuesta, hora_rta, ahora)` sobre una `PENDIENTE` vigente deja el estado igual a la respuesta y guarda `respuesta` y `hora_rta` tal como llegan; vencida lanza `SolicitudVencida`; ya respondida lanza `SolicitudYaRespondida`; guardada como `VENCIDA` lanza `SolicitudVencida`; la hora que decide es `ahora`, no `hora_rta`
- [X] T311 [S1] [US5] Impl (Green) `backend/app/dominio/errores.py` (`SolicitudVencida`, `SolicitudYaRespondida`) y `backend/app/dominio/solicitud.py` (entidad, enum `EstadoSolicitud`, `estado_efectivo`, `responder`), hasta que pase T310
- [X] T312 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/dominio/test_documento_vehiculo.py`: tipos `SEGURO`, `CEDULA_VERDE` y `VTV`; `numero` obligatorio; `entidad_emisora` opcional; `fecha_vencimiento` posterior a `fecha_emision` (si no, `DatosInvalidos`); `url_archivo` con esquema y host; estado `VIGENTE` o `VENCIDO` calculado con la fecha de hoy
- [X] T313 [S1] [US6] Impl (Green) `backend/app/dominio/documento_vehiculo.py` (entidad, enum `TipoDocumentoVehiculo` y estado calculado, reutilizando `EstadoDocumento`), hasta que pase T312

### PR `feat/s1-politica-acceso` (L3, T314–T317): Política pura de acceso

- [X] T314 [S1] [US8] Test (Red) `backend/tests/unitarios/aplicacion/test_politica_acceso.py`: `verificar_acceso(identidad, id_conductor_recurso, admite)` con la matriz de [contracts/token-jwt.md](./contracts/token-jwt.md): el operador pasa sin `id_conductor`; el conductor pasa solo con su propio id; con el id de otro lanza `AccesoProhibido`; un conductor sin `id_conductor` (nulo, booleano o no entero) lanza `AccesoProhibido`; el servicio pasa solo si la operación lo admite y si no lanza `RolNoAutorizado`; un rol no admitido lanza `RolNoAutorizado`; con varios roles vale el que más permite (operador y conductor juntos no quedan limitados por el id)
- [X] T315 [S1] [US8] Impl (Green) `backend/app/dominio/errores.py` (`AccesoProhibido`, `RolNoAutorizado`), `backend/app/aplicacion/politicas/__init__.py` y `backend/app/aplicacion/politicas/acceso.py` (`Identidad` con roles, `id_conductor` e `id_operador`, y `verificar_acceso`), hasta que pase T314
- [X] T316 [S1] [US1] Test (Red) `backend/tests/unitarios/aplicacion/test_politica_acceso.py`: `verificar_rol(identidad, admite)` para operaciones sin id de conductor (listado y alta): `GET /conductores` admite operador y servicio; el alta admite operador y conductor y no al servicio; un conductor recibe `RolNoAutorizado` en el listado
- [X] T317 [S1] [US1] Impl (Green) `backend/app/aplicacion/politicas/acceso.py`: `verificar_rol` y las constantes de roles admitidos por patrón de operación, hasta que pase T316

### PR `feat/s1-puertos-fakes-i2` (L4, T318–T322): Puertos nuevos y repositorios en memoria

- [X] T318 [S1] Test (Red) `backend/tests/unitarios/fakes/test_fakes.py`: `RepositorioSolicitudesEnMemoria` asigna id al guardar, obtiene y lista por conductor; `RepositorioDocumentosVehiculoEnMemoria` asigna id, lista por vehículo y por lote con una clave por cada id pedido; `UnidadDeTrabajoEnMemoria.bloquear_solicitud` devuelve la solicitud y `rollback` descarta los cambios nuevos
- [X] T319 [P] [S1] Impl (Green) puertos nuevos en `backend/app/aplicacion/puertos/repositorio_solicitudes.py` y `repositorio_documentos_vehiculo.py`, según [contracts/casos-de-uso.md](./contracts/casos-de-uso.md)
- [X] T320 [S1] Impl (Green) `backend/app/aplicacion/puertos/unidad_de_trabajo.py`: atributos `solicitudes` y `documentos_vehiculo`, y `bloquear_solicitud(id_solicitud)`
- [X] T321 [S1] Impl (Green) `backend/tests/unitarios/fakes/repositorios_en_memoria.py`: los dos repositorios en memoria nuevos y `bloquear_solicitud`, hasta que pase T318
- [X] T322 [S1] Impl (Green) `backend/app/infraestructura/repositorios/sql_unidad_de_trabajo.py`: la unidad de trabajo SQL declara los repositorios nuevos como pendientes (lanzan `NotImplementedError` al usarse), para que la aplicación siga arrancando y la suite siga en verde hasta L9 y L10. El marcador de documentos del vehículo devuelve lista vacía al listar por vehículo (para que `GET` del vehículo no responda 500) y lanza `NotImplementedError` al guardar y al listar por lote, hasta L10

### PR `feat/s1-casos-estado-ubicacion` (L5, T323–T329): Casos de uso de estado y ubicación

- [X] T323 [P] [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_estado_conductor.py`: devuelve `estado`, `id_vehiculo_activo` (nulo si no tiene) y `actualizado` (= `fecha_ultimo_cambio_estado`, la fecha de alta si nunca cambió), sin ubicación; `NoEncontrado` si el conductor no existe
- [X] T324 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_estado_conductor.py` y el resultado `EstadoDelConductor` en `backend/app/aplicacion/casos_de_uso/resultados.py`, hasta que pase T323
- [X] T325 [P] [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_ubicacion_conductor.py`: devuelve `latitud`, `longitud` y `fecha_act_ubic`; sin ubicación devuelve los tres en `None` y nunca `0.0`; `NoEncontrado` si el conductor no existe
- [X] T326 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_ubicacion_conductor.py` y el resultado `UbicacionDelConductor`, hasta que pase T325
- [X] T327 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_actualizar_estado_conductor.py`: pedir `DISPONIBLE` con conductor y vehículo activo `APROBADA` lo deja `DISPONIBLE` (también si estaba `DESCONECTADO` u `OCUPADO`) y `actualizado` toma la hora del `Reloj`; sin cumplir la regla lanza `ConductorNoHabilitado` y no cambia nada; `DESCONECTADO` y `CONECTADO` se aceptan siempre; `latitud` y `longitud` guardan la ubicación con `fecha_act_ubic` del `Reloj`; una sola de las dos lanza `DatosInvalidos`; sin ubicación y con ubicación previa no la cambia; un cuerpo sin ningún campo lanza `DatosInvalidos`; un vehículo activo ajeno o inexistente lanza `NoEncontrado`; `null` quita el vehículo activo y baja a `CONECTADO` a un conductor `DISPONIBLE`; bloquea al conductor con `bloquear_conductor`
- [X] T328 [S1] [US2] Test (Red) `backend/tests/unitarios/aplicacion/test_actualizar_estado_conductor.py`: ubicación simulada (decisión 6): al pasar de `DESCONECTADO` a otro estado sin ubicación previa y sin coordenadas en el pedido, asigna la coordenada inyectada con `fecha_act_ubic` igual a la hora del `Reloj`; si ya tiene ubicación no la cambia; si el pedido trae coordenadas usa esas; la coordenada simulada nunca es `0, 0`
- [X] T329 [S1] [US2] Impl (Green) `backend/app/aplicacion/casos_de_uso/actualizar_estado_conductor.py` (recibe `UnidadDeTrabajo`, `Reloj` y la ubicación simulada) hasta que pasen T327 y T328

### PR `feat/s1-casos-solicitudes` (L6, T330–T334): Casos de uso de solicitudes

- [X] T330 [P] [S1] [US5] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_solicitudes_conductor.py`: devuelve solo las solicitudes del conductor; el estado es el efectivo (una `PENDIENTE` vencida figura `VENCIDA`); el filtro `estado` se aplica sobre el estado efectivo, así `PENDIENTE` excluye a las vencidas y `VENCIDA` las incluye; sin solicitudes devuelve lista vacía; `NoEncontrado` si el conductor no existe
- [X] T331 [S1] [US5] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_solicitudes_conductor.py`, hasta que pase T330
- [X] T332 [S1] [US5] Test (Red) `backend/tests/unitarios/aplicacion/test_responder_solicitud.py`: aceptar una vigente la deja `ACEPTADO` con `respuesta` y la `hora_rta` del cliente, y deja al conductor `OCUPADO` con `actualizado` del `Reloj`; rechazar la deja `RECHAZADO` sin cambiar el estado del conductor; vencida lanza `SolicitudVencida` (aunque la `hora_rta` sea anterior) y no cambia nada; ya respondida lanza `SolicitudYaRespondida`; aceptar con el conductor `DESCONECTADO`, `OCUPADO` o sin cumplir la regla lanza `ConductorNoHabilitado` y no cambia nada; solicitud inexistente lanza `NoEncontrado`
- [X] T333 [S1] [US8] Test (Red) `backend/tests/unitarios/aplicacion/test_responder_solicitud.py`: acceso: un conductor que no es el dueño lanza `AccesoProhibido` y no cambia nada; el operador puede responder la de cualquier conductor; bloquea primero al conductor y después a la solicitud (orden de bloqueos)
- [X] T334 [S1] [US5] Impl (Green) `backend/app/aplicacion/casos_de_uso/responder_solicitud.py`: lee la solicitud, aplica `verificar_acceso`, bloquea al conductor y luego a la solicitud, revalida, aplica la respuesta y, si acepta, usa `marcar_ocupado`, hasta que pasen T332 y T333

### PR `feat/s1-casos-vehiculo-i2` (L7, T335–T342): Casos de uso del vehículo: tipos de servicio y documentación

- [X] T335 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_tipos_servicio_vehiculo.py`: devuelve cada tipo de servicio del vehículo con su `habilitado`; `NoEncontrado` si el vehículo no existe o es de otro conductor
- [X] T336 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_tipos_servicio_vehiculo.py`, hasta que pase T335
- [X] T337 [P] [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_registrar_documento_vehiculo.py`: guarda el documento y devuelve el estado `VIGENTE` o `VENCIDO` calculado con `reloj.hoy()`; vencimiento no posterior a la emisión lanza `DatosInvalidos`; `NoEncontrado` si el vehículo es de otro conductor
- [X] T338 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/registrar_documento_vehiculo.py`, hasta que pase T337
- [X] T339 [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_vehiculo.py`: el detalle incluye los documentos del vehículo con su estado calculado y una lista vacía si no tiene
- [X] T340 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/obtener_vehiculo.py` y el resultado `VehiculoDetalle` en `resultados.py`, hasta que pase T339
- [X] T341 [S1] [US6] Test (Red) `backend/tests/unitarios/aplicacion/test_accionar_habilitacion_vehiculo.py`: aprobar un vehículo habilita todos sus tipos de servicio; suspender o rechazar los deshabilita; observar no los toca; el cambio queda en la misma transacción que el evento (decisión 9)
- [X] T342 [S1] [US6] Impl (Green) `backend/app/aplicacion/casos_de_uso/accionar_habilitacion_vehiculo.py`: sincronizar `habilitado` de los tipos de servicio con la acción, hasta que pase T341

### PR `feat/s1-casos-conductor-i2` (L8, T343–T346): Casos de uso del conductor: listado y campos nuevos

- [X] T343 [S1] [US7] Test (Red) `backend/tests/unitarios/aplicacion/test_listar_conductores.py`: el filtro `estado` devuelve solo los conductores en ese estado; el filtro `tipo_servicio` devuelve los conductores con al menos un vehículo con ese tipo habilitado; se combinan con `habilitado` y `tipo_vehiculo` en conjunción; sin coincidencias devuelve lista vacía; el caso de uso no recibe `latitud` ni `longitud`
- [X] T344 [S1] [US7] Impl (Green) `backend/app/aplicacion/casos_de_uso/listar_conductores.py` y `backend/app/aplicacion/puertos/repositorio_conductores.py`: `listar` recibe `estado` (en lugar de `disponible`) y `tipo_servicio`; el fake en memoria los aplica y el repositorio SQL traduce `estado` a las columnas actuales y aplica `tipo_servicio` con el esquema actual (al menos un vehículo con ese tipo de servicio `habilitado`, vía `vehiculo_tipo_servicio`, que existe desde la migración 0001), hasta que pase T343
- [X] T345 [S1] [US7] Test (Red) `backend/tests/unitarios/aplicacion/test_obtener_conductor.py` y `test_listar_conductores.py`: el conductor devuelto trae `estado`, `id_vehiculo_activo`, `suma_puntajes`, `cantidad_calificaciones` y `puntaje_promedio` con los valores guardados
- [X] T346 [S1] [US7] Impl (Green) `backend/app/aplicacion/casos_de_uso/resultados.py` y los casos de uso `obtener_conductor` y `listar_conductores` si hace falta, hasta que pase T345

### PR `feat/s1-sql-conductor-i2` (L9, T347–T350): Repositorio SQL del conductor con estado y campos nuevos

- [ ] T347 [S1] [US7] Test (Red) `backend/tests/integracion/repositorios/test_sql_conductores_i2.py` (PostgreSQL real): guardar y obtener persisten `estado` (los cuatro valores, con `CHECK`), `id_vehiculo_activo` (FK a `vehiculo`, nulo), `fecha_ultimo_cambio_estado` (timestamptz, nulo), `suma_puntajes` y `cantidad_calificaciones` (enteros no negativos, por defecto 0); la unidad de trabajo bloquea al conductor y devuelve los campos nuevos
- [ ] T348 [S1] [US7] Test (Red) `backend/tests/integracion/repositorios/test_sql_listar_conductores.py`: el filtro `estado` devuelve solo los conductores en ese estado; el filtro `tipo_servicio` devuelve conductores con al menos un vehículo con ese tipo `habilitado`; se combinan con los filtros existentes; carga vehículos y tipos de servicio en consultas agrupadas, sin una consulta por fila
- [ ] T349 [S1] [US7] Impl (Green) `backend/app/infraestructura/repositorios/sql_conductores.py`: mapeo directo de `estado` y de los campos nuevos entre el modelo ORM de Datos y seguridad y el dominio (L1 ya dejó el mapeo directo de `estado`; aquí se suman los campos nuevos), filtro `estado` y filtro `tipo_servicio`, hasta que pasen T347 y T348
- [ ] T350 [S1] [US7] Impl (Green) `backend/app/infraestructura/repositorios/sql_unidad_de_trabajo.py`: `bloquear_conductor` devuelve el conductor con los campos nuevos

### PR `feat/s1-sql-solicitud-documentos` (L10, T351–T358): Repositorios SQL de solicitudes, documentos del vehículo y tipos de servicio

- [ ] T351 [S1] [US5] Test (Red) `backend/tests/integracion/repositorios/test_sql_solicitudes.py`: guardar y obtener una solicitud con `estado` (`PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`), `vence_en`, `respuesta` y `hora_rta`; listar por conductor; `bloquear_solicitud` devuelve la fila bloqueada, y con la fila ORM de la solicitud cargada y retenida en la sesión de la transacción (por ejemplo `fila = sesion.get(SolicitudOrm, id_solicitud)`, manteniendo la referencia viva: SQLAlchemy solo guarda referencias débiles a las filas no modificadas, y sin retenerla el test puede pasar sin `populate_existing`), modificada y confirmada por otra transacción, devuelve la versión confirmada (no la copia vieja de la sesión); el test debe fallar si se quita `populate_existing` de la consulta; una respuesta con `respuesta` y `hora_rta` desparejados o con un `estado` que no coincide es rechazada por la base (`CHECK`)
- [ ] T352 [S1] [US5] Impl (Green) `backend/app/infraestructura/repositorios/sql_solicitudes.py` y `bloquear_solicitud` en `sql_unidad_de_trabajo.py`, hasta que pase T351. La consulta de bloqueo usa `.with_for_update().execution_options(populate_existing=True)` para devolver el valor vigente de la fila aunque la sesión ya la tenga cargada; agregar `populate_existing` también a `bloquear_conductor` y `bloquear_vehiculo` del adaptador SQL, con su test (fila retenida y modificada por otra transacción), para que cumplan el contrato del puerto aunque hoy ningún caso de uso lea la entidad antes de bloquearla
- [ ] T353 [S1] [US6] Test (Red) `backend/tests/integracion/repositorios/test_sql_documentos_vehiculo.py`: guardar un documento (`tipo` `SEGURO`, `CEDULA_VERDE` o `VTV`; `numero` obligatorio; `entidad_emisora` opcional; `fecha_vencimiento` posterior a `fecha_emision`; `url_archivo` obligatoria) y listar por vehículo y por lote; un `tipo` inválido o un vencimiento anterior a la emisión es rechazado por el `CHECK`; la FK a `vehiculo` es `ON DELETE RESTRICT`; los documentos del vehículo se listan ordenados por `id` ascendente, tanto por vehículo como por lote
- [ ] T354 [S1] [US6] Impl (Green) `backend/app/infraestructura/repositorios/sql_documentos_vehiculo.py` y su cableado en `sql_unidad_de_trabajo.py`, hasta que pase T353. Reemplaza la clase marcador de documentos del vehículo (T322) y el test que fija su contrato en `tests/integracion/repositorios/test_sql_unidad_de_trabajo.py`
- [ ] T355 [S1] [US6] Test (Red) `backend/tests/integracion/repositorios/test_sql_vehiculos.py`: guardar un vehículo persiste el cambio de `habilitado` de sus tipos de servicio, y `obtener` y `listar_por_conductores` los devuelven actualizados
- [ ] T356 [S1] [US6] Impl (Green) `backend/app/infraestructura/repositorios/sql_vehiculos.py`: persistir `habilitado` de los tipos de servicio, hasta que pase T355
- [ ] T357 [S1] [US5] Test (Red) `backend/tests/integracion/test_casos_de_uso_sql.py`: con la unidad de trabajo SQL, `responder_solicitud` acepta una vigente, deja al conductor `OCUPADO` y rechaza una segunda respuesta con `SolicitudYaRespondida`; una aceptación y un cambio de estado del mismo conductor lanzados a la vez se aplican uno tras otro sin perder ninguno
- [ ] T358 [S1] [US5] Impl (Green) ajustes mínimos en `sql_unidad_de_trabajo.py` y en los repositorios nuevos hasta que pase T357

---

## Fase 2: Stack 2 — Servidor HTTP

**Meta**: seguridad por rol, acceso propio del conductor, los 7 endpoints nuevos y los esquemas ampliados, contra casos de uso simulados (`CasoDeUsoFalso`) y tokens firmados en el test. Cada PR de esta fase agrega a `ESPERADOS` de `backend/tests/api/test_paridad_rutas.py` los pares (ruta, método) que incorpora, con el test que falla primero.

### PR `feat/s2-seguridad-rol-servicio` (V1, T359–T366): Rol servicio, claim del conductor y dependencias de acceso

- [ ] T359 [S2] [US1] Test (Red) `backend/tests/api/conftest.py`: `crear_token` acepta varios roles e `id_conductor` e incluye por defecto un `sub` de texto no vacío (junto al `iss` existente), porque el rate limiting de Datos y seguridad (T517) clasifica por `(iss, sub)`; fixtures `headers_servicio` (solo rol `servicio`) y `headers_conductor_de(id)` (rol `conductor` con ese `id_conductor`); `test_fixtures_de_acceso` verifica el contenido de cada token
- [ ] T360 [S2] [US1] Impl (Green) `backend/tests/api/conftest.py`: los ayudantes anteriores, sin cambiar las fixtures existentes, hasta que pase T359
- [ ] T361 [S2] [US1] Test (Red) `backend/tests/api/test_seguridad_servicio.py`: un token con solo el rol `servicio` es aceptado; un token sin ningún rol reconocido responde `403`; se lee el claim `id_conductor` entero; un `id_conductor` booleano o no numérico se trata como ausente
- [ ] T362 [S2] [US1] Impl (Green) `backend/app/api/seguridad.py`: agregar `servicio` a `ROLES_VALIDOS` y construir la `Identidad` desde el payload, hasta que pase T361
- [ ] T363 [S2] [US1] Test (Red) `backend/tests/api/test_dependencias_acceso.py` (aplicación mínima de prueba): `requerir_operador_o_servicio`; `requerir_conductor_propio_u_operador(id)`; `requerir_conductor_propio_operador_o_servicio(id)`; el chequeo por id responde `403` `ACCESO_PROHIBIDO` antes de buscar el recurso; el rol `servicio` recibe `403` en las dependencias que no lo admiten; `requerir_operador` existente no cambia
- [ ] T364 [S2] [US1] Impl (Green) `backend/app/api/seguridad.py`: las dependencias de acceso, una por patrón de la matriz y apoyadas en `aplicacion/politicas/acceso.py`, hasta que pase T363
- [ ] T365 [S2] [US1] Test (Red) `backend/tests/api/test_errores.py`: `AccesoProhibido` → `403` `ACCESO_PROHIBIDO`; `RolNoAutorizado` → `403` `SIN_PERMISOS`; `SolicitudYaRespondida` → `409` `SOLICITUD_YA_RESPONDIDA`; `SolicitudVencida` → `410` `SOLICITUD_VENCIDA`; `ConductorNoHabilitado` → `422` `CONDUCTOR_NO_HABILITADO`
- [ ] T366 [S2] [US1] Impl (Green) `backend/app/api/errores.py`: agregar los cinco errores a `MAPEO_ERRORES_DOMINIO`, hasta que pase T365

### PR `feat/s2-acceso-endpoints-existentes` (V2, T367–T372): Acceso por rol y propio en los 10 endpoints de la Iteración 1

- [ ] T367 [S2] [US8] Test (Red) `backend/tests/api/test_acceso_propio.py`: para las operaciones 3, 4, 6, 7, 8 y 9 de la matriz de [contracts/token-jwt.md](./contracts/token-jwt.md): el conductor con su propio id obtiene la respuesta normal; con el id de otro responde `403` `ACCESO_PROHIBIDO` sin llamar al caso de uso, aunque el otro conductor no exista; un token de conductor sin `id_conductor` responde `403`; el operador accede a cualquiera; el servicio lee las operaciones 3, 4, 8 y 9 y recibe `403` en las escrituras 6 y 7
- [ ] T368 [S2] [US1] Test (Red) `backend/tests/api/test_acceso_propio.py`: `POST /conductores` responde `403` al rol `servicio` y funciona para operador y conductor; las acciones de habilitación (operaciones 5 y 10) siguen siendo solo del operador y responden `403` al conductor y al servicio
- [ ] T369 [S2] [US7] Test (Red) `backend/tests/api/test_acceso_propio.py`: `GET /conductores` responde `403` `SIN_PERMISOS` a un conductor y `200` a operador y a servicio
- [ ] T370 [S2] [US8] Impl (Green) `backend/tests/api/conftest.py`: la fixture `headers_conductor` pasa a incluir `id_conductor=1`, el id de `conductor_de_prueba()`, porque el requisito de acceso propio (FR-040) lo exige; no cambia ninguna aserción de los tests existentes
- [ ] T371 [S2] [US7] Impl (Green) `backend/tests/api/test_conductores_listar.py`: los tests del listado pasan a usar `headers_operador` en lugar de `headers_conductor`, porque `GET /conductores` ya no es del conductor (FR-041, decisión de la clarificación); las aserciones no cambian
- [ ] T372 [S2] [US8] Impl (Green) `backend/app/api/routers/conductores.py`, `habilitacion.py`, `documentacion.py`, `vehiculos.py` y `vehiculos_habilitacion.py`: aplicar la dependencia de acceso que corresponde a cada operación según la matriz, hasta que pasen T367 a T369

### PR `feat/s2-estado-ubicacion` (V3, T373–T380): Endpoints de estado y ubicación del conductor

- [ ] T373 [S2] [US2] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar a `ESPERADOS` los pares `GET /api/v1/conductores/{id_conductor}/estado` (`obtenerEstadoConductor`), `PATCH` en la misma ruta (`actualizarEstadoConductor`) y `GET /api/v1/conductores/{id_conductor}/ubicacion` (`obtenerUbicacionConductor`)
- [ ] T374 [S2] [US2] Test (Red) `backend/tests/api/test_configuracion.py`: `UBICACION_SIMULADA_LATITUD` y `UBICACION_SIMULADA_LONGITUD` valen por defecto `-27.4511` y `-58.9867`, se pueden cambiar por variable de entorno y fuera de rango (latitud -90 a 90, longitud -180 a 180) producen un error de validación
- [ ] T375 [S2] [US2] Impl (Green) `backend/app/api/configuracion.py`: las dos variables opcionales con esos valores por defecto, hasta que pasen T373 y T374
- [ ] T376 [S2] [US2] Test (Red) `backend/tests/api/test_esquemas.py`: `EstadoOperativo` con `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`; `EstadoConductor` con `id_conductor`, `estado`, `id_vehiculo_activo` (nulo) y `actualizado`, y sin campos de ubicación; `UbicacionConductor` con los tres campos que admiten nulo; `EstadoConductorRequest` exige al menos un campo, su `estado` admite solo `DESCONECTADO`, `CONECTADO` o `DISPONIBLE` (`OCUPADO` responde `400`) y `latitud` y `longitud` van juntas y en rango
- [ ] T377 [S2] [US2] Impl (Green) `backend/app/api/esquemas/estado.py` con esos esquemas, hasta que pase T376
- [ ] T378 [S2] [US2] Test (Red) `backend/tests/api/test_estado_ubicacion.py`: las tres operaciones según la matriz de roles; el `PATCH` responde `400` con cuerpo vacío, una sola coordenada o `estado: OCUPADO`, `422` `CONDUCTOR_NO_HABILITADO` y `404`; con el rol `servicio` el `PATCH` responde `403`; los casos de uso reciben los argumentos esperados
- [ ] T379 [S2] [US2] Impl (Green) `backend/app/api/dependencias.py` (proveedores de `obtener_estado_conductor`, `obtener_ubicacion_conductor` y `actualizar_estado_conductor`, con la ubicación simulada de la configuración) y `backend/app/api/routers/estado.py`, hasta que pasen T373 y T378
- [ ] T380 [S2] [US2] Impl (Green) `backend/app/api/main.py`: registrar `estado.router` en `ROUTERS`

### PR `feat/s2-solicitudes` (V4, T381–T385): Endpoints de solicitudes

- [ ] T381 [S2] [US5] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `GET /api/v1/conductores/{id_conductor}/solicitudes` (`listarSolicitudesConductor`) y `POST /api/v1/solicitudes/{id_solicitud}` (`responderSolicitud`)
- [ ] T382 [S2] [US5] Test (Red) `backend/tests/api/test_esquemas.py`: `Solicitud` con `id`, `id_conductor`, `id_viaje` (nulo), `estado`, `vence_en`, `respuesta` (nulo) y `hora_rta` (nulo); `RespuestaSolicitudRequest` con `respuesta` (`ACEPTADO` o `RECHAZADO`) y `hora_rta` obligatorias
- [ ] T383 [S2] [US5] Test (Red) `backend/tests/api/test_solicitudes.py`: el listado admite el filtro `estado` y un valor inválido responde `400`; el conductor lista solo las suyas; responder devuelve la solicitud y mapea `404`, `403` `ACCESO_PROHIBIDO`, `409` `SOLICITUD_YA_RESPONDIDA`, `410` `SOLICITUD_VENCIDA` y `422` `CONDUCTOR_NO_HABILITADO`; el rol `servicio` recibe `403`; el caso de uso recibe la identidad de quien responde
- [ ] T384 [S2] [US5] Impl (Green) `backend/app/api/esquemas/solicitud.py`, los proveedores de `listar_solicitudes_conductor` y `responder_solicitud` en `dependencias.py` y el router `backend/app/api/routers/solicitudes.py`, hasta que pasen T381 a T383
- [ ] T385 [S2] [US5] Impl (Green) `backend/app/api/main.py`: registrar `solicitudes.router` en `ROUTERS`

### PR `feat/s2-vehiculo-i2` (V5, T386–T389): Endpoints de tipos de servicio y documentación del vehículo

- [ ] T386 [S2] [US6] Test (Red) `backend/tests/api/test_paridad_rutas.py`: agregar `GET /api/v1/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` (`listarTiposServicioVehiculo`) y `POST` en `.../vehiculos/{id_vehiculo}/documentacion` (`crearDocumentacionVehiculo`)
- [ ] T387 [S2] [US6] Test (Red) `backend/tests/api/test_esquemas.py`: `TipoServicioHabilitado` (`tipo` y `habilitado`); `DocumentoVehiculoCreate` con `tipo` (`SEGURO`, `CEDULA_VERDE` o `VTV`), `numero`, `entidad_emisora` opcional, fechas y `url_archivo` con formato de URL; `DocumentoVehiculo` con `id_vehiculo` y `estado`; `Vehiculo.documentos` incluye los documentos con su estado
- [ ] T388 [S2] [US6] Test (Red) `backend/tests/api/test_vehiculos_i2.py`: tipos de servicio según la matriz de roles y `404`; el documento responde `201` con el estado calculado; `400` con tipo inválido o URL inválida; `422` con vencimiento anterior a la emisión; `404` si el vehículo es de otro conductor; `servicio` recibe `403` al crear el documento
- [ ] T389 [S2] [US6] Impl (Green) `backend/app/api/esquemas/vehiculo.py` y `documento.py`, los proveedores de `listar_tipos_servicio_vehiculo` y `registrar_documento_vehiculo` en `dependencias.py` y las dos rutas en `backend/app/api/routers/vehiculos.py`, hasta que pasen T386 a T388

### PR `feat/s2-conductor-campos-nuevos` (V6, T390–T397): Estado, campos nuevos y filtros del conductor, y versión 1.2.0

- [ ] T390 [S2] [US7] Test (Red) `backend/tests/api/test_esquemas.py`: `Conductor` incluye `estado` (uno de los cuatro valores) en lugar de `conectado` y `disponible`, `puntaje_promedio` (número de 1 a 5 o nulo) y `cantidad_calificaciones` (entero no negativo, por defecto 0); `ConductorConUbicacion` incluye `id_vehiculo_activo` (nulo); el alta (`POST /conductores`) sigue devolviendo `Conductor` sin ubicación y con `estado` `DESCONECTADO`
- [ ] T391 [S2] [US7] Impl (Green) `backend/app/api/esquemas/conductor.py` y `backend/tests/api/conftest.py` (`conductor_de_prueba`): `estado` en lugar de `conectado` y `disponible`, los campos nuevos y su mapeo desde el detalle, hasta que pase T390
- [ ] T392 [S2] [US7] Test (Red) `backend/tests/api/test_conductores_listar.py`: el filtro `estado` (en lugar de `disponible`) llega al caso de uso y un valor inválido responde `400`; `tipo_servicio` llega al caso de uso; `latitud` y `longitud` siguen aceptándose (solo juntas y en rango) pero no llegan al caso de uso ni cambian el resultado; una sola de las dos responde `400`; los campos nuevos aparecen en la respuesta
- [ ] T393 [S2] [US7] Impl (Green) `backend/app/api/routers/conductores.py`: reemplazar el parámetro `disponible` por `estado`, pasar `tipo_servicio` al caso de uso y descartar `latitud` y `longitud`, hasta que pase T392
- [ ] T394 [S2] [US7] Test (Red) `backend/tests/api/test_main.py`: la aplicación declara la versión `1.2.0`
- [ ] T395 [S2] [US7] Impl (Green) `backend/app/api/main.py`: `version="1.2.0"`, hasta que pase T394
- [ ] T396 [S2] [US7] Test (Red) `backend/tests/api/test_paridad_rutas.py`: cambiar el nombre de las pruebas de "10" a "17" y exigir que la aplicación genere exactamente las 17 operaciones del contrato, con sus `operationId` y los pares que sumaron V3 a V5
- [ ] T397 [S2] [US7] Impl (Green) completar lo que falte para que pase T396 y ejecutar la suite completa con `--cov-fail-under=65`

---

## Fase 3: Cierre

**Meta**: dejar documentado y verificado lo que termina la parte de Backend.

### PR `docs/backend-cierre-i2` (C1, T398–T401): Documentación y verificación final de Backend

- [ ] T398 Actualizar `README.md`: la tabla de endpoints marca como implementados los 17, la sección de la API refleja el rol `servicio` de solo lectura, el acceso propio del conductor, el listado solo para operador y servicio y el campo `estado` en lugar de `conectado` y `disponible`, y se quita la nota sobre la diferencia con la Iteración 1
- [ ] T399 Recorrer [quickstart.md](./quickstart.md) contra el entorno real una vez que L9 y L10 y la migración de Datos y seguridad están en `dev`, y anotar cualquier diferencia
- [ ] T400 Informar a Testing el valor propuesto para el umbral de cobertura (70 %) y los resultados de `pytest --cov` sobre lo implementado
- [ ] T401 PR de contrato aparte (`docs/contrato-roles-bearer`): ajustar en `docs/contract/openapi.yaml` la descripción de roles de `bearerAuth`, que hoy dice que el conductor consulta conductores y vehículos, para que el listado figure como de operador y servicio

---

---

## Dependencias entre PRs

- **L1, L2 y L3** no dependen de nadie y se pueden hacer en paralelo.
- **L4** necesita las entidades de L1 y L2. **V1** necesita la política de L3 y los errores de L2 y L3.
- **L5, L7 y L8** necesitan los puertos y los fakes de L4. **V2** necesita V1.
- **L6** necesita L5 (reutiliza el cambio de estado). **V3, V5 y V6** necesitan V1 y el caso de uso de su grupo (L5, L7 y L8).
- **V4** necesita V1 y L6.
- **L9** necesita L4 y la migración de Datos y seguridad; **L10** necesita L9.
- En cada PR, la tarea de test va siempre antes de su implementación.

## Verificación por historia

| Historia | Cómo se comprueba que está cumplida |
|---|---|
| US1 Acceso por rol y servicio | Un token `servicio` lee conductores y no hace acciones de operador ni actualiza estados o solicitudes; sin token `401` |
| US2 Estado y ubicación | Se actualiza el estado de un conductor aprobado y se consulta; pedir `OCUPADO` da `400`; sin ubicación, `200` con los tres campos nulos; el conductor sin ubicación que se conecta recibe la simulada |
| US3 y US4 | Retiradas con el contrato 1.2.0 |
| US5 Solicitudes | Vigente se responde; vencida da `410`; ya respondida da `409`; aceptar deja al conductor `OCUPADO` y un conductor `OCUPADO` no puede aceptar otra |
| US6 Vehículo | Tipos de servicio con su `habilitado`; documento con estado calculado; `422` con vencimiento anterior a la emisión |
| US7 Listado y campos nuevos | `estado` y `tipo_servicio` filtran; `latitud` y `longitud` no cambian el resultado; `estado`, `puntaje_promedio` e `id_vehiculo_activo` salen en la respuesta; versión 1.2.0 |
| US8 Acceso propio | Un conductor recibe `403` sobre datos de otro, con el mismo resultado exista o no ese conductor; el operador accede a todo |

## Estrategia de implementación

1. **Primer hito (MVP)**: US1 y US2 de punta a punta con fakes: L1, L3, L4, L5, V1 y V3. M4 ya puede leer estado y ubicación y el conductor actualizarlos.
2. **Segundo hito**: US5, US6, US7 y US8: solicitudes, vehículo, listado y acceso propio en los endpoints existentes (L6 a L8, V2, V4 a V6).
3. **Cierre**: repositorios SQL (L9 y L10) cuando llegue la migración, y C1.

Cada hito deja la rama `dev` en verde.

## Notas

- **Total**: 101 tareas en 17 PRs (10 de lógica, 6 de servidor y 1 de cierre).
- **Paridad de rutas**: cada PR de servidor agrega sus pares a `ESPERADOS` de `backend/tests/api/test_paridad_rutas.py` con su test en rojo primero. La lista llega a las 17 operaciones en V6.
- **No incluido** (otros grupos): migración, seed, Keycloak, pruebas de contrato y de concurrencia de punta a punta.
- **Pendiente con M4 y M6**: el contrato ya no tiene operaciones de entrada para ellos. Quién marca `OCUPADO` más allá de aceptar una solicitud, y de dónde salen los puntajes, se acuerda con ellos.

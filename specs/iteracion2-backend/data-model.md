# Modelo de Datos: Iteración 2 — Backend

Interfaz entre **Backend** y **Datos y seguridad**: lo que el backend necesita de la base `m3` (PostgreSQL) para los endpoints de la Iteración 2. Extiende el [modelo de la Iteración 1](../iteracion1/data-model.md). **Backend no escribe la migración ni el seed**: los hace Datos y seguridad (issue #36) y este documento es lo que acordamos.

Los nombres son una **propuesta**. Cualquier cambio se avisa y se actualiza acá antes de implementarlo. Todas las fechas y horas en UTC. Los modelos SQLAlchemy (`backend/app/infraestructura/db/modelos.py`) los mantiene Datos y seguridad.

## Cambios en tablas existentes

### conductor (columna reemplazada y columnas nuevas)

| Campo | Tipo | Reglas |
|---|---|---|
| `estado` | texto | **Reemplaza a `conectado` y `disponible`.** `DESCONECTADO` (por defecto), `CONECTADO`, `DISPONIBLE` u `OCUPADO`, con `CHECK`. Obligatorio |
| `id_vehiculo_activo` | bigint, FK → `vehiculo.id_vehiculo`, nulo | Vehículo con el que trabaja. Debe ser de ese conductor (lo valida el backend). `ON DELETE SET NULL` |
| `fecha_ultimo_cambio_estado` | timestamptz, nulo | Es el campo `actualizado` del contrato. Cambia con el estado o el vehículo activo. **No** cambia por la ubicación. Nulo hasta el primer cambio |
| `suma_puntajes` | entero | Por defecto 0. No negativo |
| `cantidad_calificaciones` | entero | Por defecto 0. No negativo |

- **Migración de `conectado` y `disponible` a `estado`**: `conectado = false` → `DESCONECTADO`; `conectado = true` y `disponible = true` → `DISPONIBLE`; `conectado = true` y `disponible = false` → `CONECTADO`. Después se eliminan las dos columnas y el índice `ix_conductor_disponible`, y se crea un índice por `estado`. El valor `OCUPADO` no sale de datos existentes: lo asigna el backend al aceptar una solicitud.
- `puntaje_promedio` **no se guarda**: se calcula como `suma_puntajes / cantidad_calificaciones` (nulo si la cantidad es 0). **Ningún endpoint escribe estos totales en esta iteración**: el seed los carga y de dónde vendrán en producción se define con M6 y M2.
- `latitud`, `longitud` y `fecha_act_ubic` ya existen desde la Iteración 1 y se empiezan a usar.
- `CHECK`: `cantidad_calificaciones >= 0` y `suma_puntajes >= 0`; si la cantidad es 0, la suma es 0.
- Índice sugerido por `id_vehiculo_activo`.

### vehiculo_tipo_servicio

Sin cambios de esquema. `habilitado` pasa a mantenerse sincronizado con la habilitación del vehículo (aprobar → verdadero; suspender o rechazar → falso). Lo hace el backend, en la misma transacción que la acción de habilitación.

## Tablas nuevas

### solicitud

| Campo | Tipo | Reglas |
|---|---|---|
| `id_solicitud` | bigint, PK | Autogenerado |
| `id_conductor` | bigint, FK → `conductor` | Obligatorio. `ON DELETE RESTRICT` |
| `id_viaje` | bigint, nulo | Viaje al que corresponde la oferta |
| `estado` | texto | `PENDIENTE` (inicial), `ACEPTADO`, `RECHAZADO` o `VENCIDA`, con `CHECK` |
| `vence_en` | timestamptz | Obligatorio. Límite para responder |
| `respuesta` | texto, nulo | `ACEPTADO` o `RECHAZADO`, con `CHECK`. Nulo mientras no se responda |
| `hora_rta` | timestamptz, nulo | La hora que envió el cliente, guardada tal cual. Nulo mientras no se responda |
| `fecha_alta` | timestamptz | Autogenerada por la base |

- `CHECK`: `respuesta` y `hora_rta` son ambos nulos o ambos con valor, y si tienen valor `estado` coincide con `respuesta`.
- Índice por `(id_conductor, estado)`.
- **El backend no crea solicitudes**: el origen (cómo las crea M5) queda fuera de esta iteración. El seed y los tests de integración las insertan directamente.
- El estado `VENCIDA` es válido en la base, pero el backend no lo escribe: calcula "vencida" al leer (`PENDIENTE` con `vence_en` ya pasado), ver [research.md](./research.md), decisión 7.

### vehiculo_documento

| Campo | Tipo | Reglas |
|---|---|---|
| `id_documento` | bigint, PK | Autogenerado |
| `id_vehiculo` | bigint, FK → `vehiculo` | Obligatorio. `ON DELETE RESTRICT` |
| `tipo` | texto | `SEGURO`, `CEDULA_VERDE` o `VTV`, con `CHECK` |
| `numero` | texto | Obligatorio |
| `entidad_emisora` | texto, nulo | Opcional |
| `fecha_emision` | fecha | Obligatoria |
| `fecha_vencimiento` | fecha | Obligatoria. `CHECK` posterior a `fecha_emision` |
| `url_archivo` | texto | Obligatorio, URI válida |
| `fecha_registro` | timestamptz | Autogenerada por la base |

El estado `VIGENTE` o `VENCIDO` **no se guarda**: se calcula al leer con la fecha actual, igual que en el documento del conductor. Los documentos son de solo escritura: nunca se actualizan ni se borran.

### viaje_finalizado *(retirada)*

Se retiró con el contrato 1.2.0, que sacó `POST /integraciones/m6/.../finalizacion`. **Datos y seguridad no crea esta tabla.**

## Relaciones

- Un conductor tiene cero o un vehículo activo y cero o más solicitudes.
- Un vehículo tiene cero o más documentos.
- Una solicitud pertenece a un conductor y puede tener un viaje asociado.

## Transiciones

### Solicitud

| Estado guardado | Acción | Resultado |
|---|---|---|
| `PENDIENTE` y `ahora <= vence_en` | aceptar o rechazar | `ACEPTADO` o `RECHAZADO` |
| `PENDIENTE` y `ahora > vence_en` | aceptar o rechazar | no cambia; `410` |
| `ACEPTADO`, `RECHAZADO` o `VENCIDA` | cualquiera | no cambia; `409` (`410` si es `VENCIDA`) |

`ahora` es la hora del servidor, no la `hora_rta` del cliente.

### Estado del conductor

Las reglas y sus resultados están en [research.md](./research.md), decisión 5. En resumen: para quedar `DISPONIBLE` el conductor debe estar `APROBADA` y tener un vehículo activo `APROBADA`; si pierde el vehículo activo estando `DISPONIBLE`, pasa a `CONECTADO`. `OCUPADO` lo asigna el backend al aceptar una solicitud y el conductor lo deja pidiendo otro estado.

| Estado actual | Pide | Resultado |
|---|---|---|
| cualquiera | `DESCONECTADO` o `CONECTADO` | ese estado |
| `DESCONECTADO`, `CONECTADO` u `OCUPADO` | `DISPONIBLE` (cumple la regla) | `DISPONIBLE` |
| cualquiera | `DISPONIBLE` (no cumple la regla) | no cambia; `422` |
| cualquiera | `OCUPADO` | no cambia; `400` |
| `CONECTADO` o `DISPONIBLE` | aceptar una solicitud (cumple la regla) | `OCUPADO` |

## Bloqueos que usa el backend

| Operación | Bloquea |
|---|---|
| Estado del conductor | Fila del `conductor` (`SELECT ... FOR UPDATE`) |
| Responder solicitud | Fila del `conductor` y después la de la `solicitud` |
| Acción de habilitación del vehículo (ya existente) | Fila del `vehiculo` |

Datos y seguridad no tiene que crear nada para esto; se pide solo que las FK estén definidas.

## Datos de prueba mínimos (seed, a cargo de Datos y seguridad)

- Conductores con ubicación distinta y uno **sin ubicación** (los tres campos en nulo).
- Conductores en cada uno de los cuatro `estado` y uno con `id_vehiculo_activo` en nulo.
- Un conductor con calificaciones (promedio no nulo) y otro sin ninguna; los totales se cargan directamente porque ningún endpoint los escribe.
- Vehículos con tipos de servicio habilitados.
- Solicitudes en los cuatro estados, incluida una `PENDIENTE` vigente y otra `PENDIENTE` ya vencida, y un conductor `CONECTADO` con vehículo activo `APROBADA` que pueda aceptarlas.
- Documentos de vehículo, uno `VIGENTE` y uno `VENCIDO`.
- Un usuario conductor cuyo `id_conductor` del token coincida con un conductor del seed.

## Notas para la implementación

- El listado de conductores y el detalle deben traer las columnas nuevas sin consultas adicionales por fila (el listado carga vehículos, documentos y tipos de servicio en consultas agrupadas, como en la Iteración 1).
- `GET /conductores/{id}/vehiculos/{id_vehiculo}` ahora devuelve `documentos` del vehículo en lugar de la lista vacía.
- El filtro `tipo_servicio` del listado usa `vehiculo_tipo_servicio` (conductores con al menos un vehículo con ese tipo habilitado).

# Modelo de Datos: Iteración 1

Base de datos `m3` (PostgreSQL). Nombres en español, sin tildes. Todas las fechas y horas en UTC.

## Entidades

### conductor
| Campo | Tipo | Reglas |
|---|---|---|
| id_conductor | bigint, PK | Autogenerado |
| dni | texto | Único; 7 u 8 dígitos |
| nombre, apellido, telefono | texto | Obligatorios |
| email | texto | Obligatorio, formato de correo |
| estado_habilitacion | texto | `PENDIENTE` (inicial), `OBSERVADA`, `APROBADA`, `SUSPENDIDA`, `RECHAZADA` |
| conectado | booleano | Por defecto falso |
| disponible | booleano | Por defecto falso |
| latitud, longitud | doble | Nulos en la Iteración 1; se usan en la Iteración 2 |
| fecha_act_ubic | timestamptz | Nulo en la Iteración 1; se usa en la Iteración 2 |
| fecha_alta, fecha_actualizacion | timestamptz | Autogeneradas por la base |

### vehiculo
| Campo | Tipo | Reglas |
|---|---|---|
| id_vehiculo | bigint, PK | Autogenerado |
| id_conductor | bigint, FK → conductor | Obligatorio |
| tipo | texto | `AUTO` o `MOTO` |
| patente | texto | Única |
| marca, modelo | texto | Obligatorios |
| anio | entero | Obligatorio; entre 1900 y 2100 (también validado por el contrato) |
| estado_habilitacion | texto | Mismos estados que el conductor; inicial `PENDIENTE` |
| fecha_alta, fecha_actualizacion | timestamptz | Autogeneradas por la base |

### vehiculo_tipo_servicio
| Campo | Tipo | Reglas |
|---|---|---|
| id_vehiculo_tipo_servicio | bigint, PK | Autogenerado |
| id_vehiculo | bigint, FK → vehiculo | Obligatorio |
| tipo_servicio | texto | `PASAJEROS` o `ENVIOS`; único por vehículo |
| habilitado | booleano | Por defecto falso |

Al menos una fila por vehículo y sin tipos de servicio repetidos.

### documento_conductor
| Campo | Tipo | Reglas |
|---|---|---|
| id_documento | bigint, PK | Autogenerado |
| id_conductor | bigint, FK → conductor | Obligatorio |
| tipo | texto | Solo `LICENCIA` |
| numero | texto | Obligatorio |
| categoria | texto | Opcional |
| fecha_emision, fecha_vencimiento | fecha | Obligatorias; vencimiento posterior a emisión |
| url_archivo | texto | Obligatorio, URI válida |
| fecha_registro | timestamptz | Autogenerada por la base |

El estado `VIGENTE` o `VENCIDO` **no se guarda**: se calcula al leer con la fecha actual (ver [research.md](./research.md)).

### habilitacion_evento_conductor y habilitacion_evento_vehiculo
Dos tablas con la misma forma, una por entidad, para mantener las claves foráneas.

| Campo | Tipo | Reglas |
|---|---|---|
| id_evento | bigint, PK | Autogenerado |
| id_conductor / id_vehiculo | bigint, FK | Obligatorio; `ON DELETE RESTRICT` |
| accion | texto | `ALTA`, `APROBAR`, `OBSERVAR`, `SUSPENDER`, `RECHAZAR` |
| estado_anterior | texto | Nulo en `ALTA` |
| estado_nuevo | texto | Obligatorio |
| motivo | texto | Obligatorio y no vacío, también en `ALTA` |
| id_operador | bigint | Nulo si lo genera el sistema (`ALTA`) |
| fecha | timestamptz | Autogenerada por la base |

Los eventos son de solo escritura: nunca se actualizan ni se borran.

## Relaciones

- Un conductor tiene muchos vehículos, muchos documentos y muchos eventos de habilitación.
- Un vehículo tiene uno o más tipos de servicio y muchos eventos de habilitación.
- El estado actual de habilitación vive en la entidad y se actualiza junto con el evento, en la misma transacción.

## Restricciones de integridad

- `conductor.dni` único y `vehiculo.patente` única (base de las respuestas `409`, RNF-08).
- Los estados de habilitación y los enumerados se restringen con `CHECK`.
- `vehiculo.anio` se restringe a 1900–2100 con `CHECK` y la misma regla está en el contrato OpenAPI.
- Los largos máximos de las columnas (`String(n)`) son límites técnicos de la base; el contrato de entrada los replica con `maxLength` para evitar errores de integridad.
- Las claves foráneas de los eventos usan `ON DELETE RESTRICT` para preservar la trazabilidad.
- `ALTA` se registra al crear el conductor y el vehículo, con `estado_anterior` nulo, `PENDIENTE` como estado nuevo y un motivo no vacío.

## Transiciones de habilitación

Aplican a conductor y vehículo. Cualquier otra combinación devuelve `409`.

| Estado actual | Acciones permitidas | Estado nuevo |
|---|---|---|
| `PENDIENTE` | `APROBAR`, `OBSERVAR`, `RECHAZAR` | `APROBADA`, `OBSERVADA`, `RECHAZADA` |
| `OBSERVADA` | `APROBAR`, `RECHAZAR` | `APROBADA`, `RECHAZADA` |
| `APROBADA` | `SUSPENDER` | `SUSPENDIDA` |
| `SUSPENDIDA` | `APROBAR`, `RECHAZAR` | `APROBADA`, `RECHAZADA` |
| `RECHAZADA` | ninguna | final |

**Regla adicional (solo conductor)**: `APROBAR` exige al menos una licencia `VIGENTE`; si no, responde `422`.

## Notas para la implementación

- `documentos` de un vehículo devuelve siempre una lista vacía en esta iteración (la documentación del vehículo queda para la Iteración 2).
- Los tipos de servicio inician con `habilitado = falso`; su habilitación llega en la Iteración 2.
- El listado de conductores carga vehículos y documentos en consultas agrupadas para evitar una consulta por fila.

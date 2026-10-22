# Modelo de Datos: Iteración 1

Base de datos `m3` (PostgreSQL). Nombres en español, sin tildes. Todas las fechas y horas en UTC.

## Entidades

### conductor
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint, PK | Autogenerado |
| dni | texto | Único; 7 u 8 dígitos |
| nombre, apellido, telefono | texto | Obligatorios |
| email | texto | Obligatorio, formato de correo |
| habilitacion | texto | `PENDIENTE` (inicial), `OBSERVADA`, `APROBADA`, `SUSPENDIDA`, `RECHAZADA` |
| conectado | booleano | Por defecto falso |
| disponible | booleano | Por defecto falso |
| latitud, longitud | doble | Nulos hasta la Iteración 2 |
| fecha_act_ubic | timestamptz | Nulo hasta la Iteración 2 |

### vehiculo
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint, PK | Autogenerado |
| id_conductor | bigint, FK → conductor | Obligatorio |
| tipo | texto | `AUTO` o `MOTO` |
| patente | texto | Única |
| marca, modelo | texto | Obligatorios |
| anio | entero | Obligatorio |
| habilitacion | texto | Mismos estados que el conductor; inicial `PENDIENTE` |

### vehiculo_tipo_servicio
| Campo | Tipo | Reglas |
|---|---|---|
| id_vehiculo | bigint, FK → vehiculo | PK compuesta |
| tipo | texto | `PASAJEROS` o `ENVIOS`; PK compuesta |
| habilitado | booleano | Por defecto falso |

Al menos una fila por vehículo.

### documento_conductor
| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint, PK | Autogenerado |
| id_conductor | bigint, FK → conductor | Obligatorio |
| tipo | texto | `LICENCIA` |
| numero | texto | Obligatorio |
| categoria | texto | Opcional |
| fecha_emision, fecha_vencimiento | fecha | Obligatorias; vencimiento posterior a emisión |
| url_archivo | texto | Obligatorio, URI válida |

El estado `VIGENTE` o `VENCIDO` **no se guarda**: se calcula al leer con la fecha actual (ver [research.md](./research.md)).

### habilitacion_evento_conductor y habilitacion_evento_vehiculo
Dos tablas con la misma forma, una por entidad, para mantener las claves foráneas.

| Campo | Tipo | Reglas |
|---|---|---|
| id | bigint, PK | Autogenerado |
| id_conductor / id_vehiculo | bigint, FK | Obligatorio |
| accion | texto | `ALTA`, `APROBAR`, `OBSERVAR`, `SUSPENDER`, `RECHAZAR` |
| estado_anterior | texto | Nulo en `ALTA` |
| estado_nuevo | texto | Obligatorio |
| motivo | texto | Obligatorio y no vacío |
| id_operador | bigint | Nulo si lo genera el sistema (`ALTA`) |
| fecha | timestamptz | Obligatoria |

Los eventos son de solo escritura: nunca se actualizan ni se borran.

## Relaciones

- Un conductor tiene muchos vehículos, muchos documentos y muchos eventos de habilitación.
- Un vehículo tiene uno o más tipos de servicio y muchos eventos de habilitación.
- El estado actual de habilitación vive en la entidad y se actualiza junto con el evento, en la misma transacción.

## Restricciones de integridad

- `conductor.dni` único y `vehiculo.patente` única (base de las respuestas `409`, RNF-08).
- Los dos estados de habilitación y los enumerados se restringen con `CHECK`.
- `ALTA` se registra al crear el conductor y el vehículo, con `estado_anterior` nulo y `PENDIENTE` como estado nuevo.

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

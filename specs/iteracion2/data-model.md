# Modelo de Datos: Iteración 2

Base de datos `m3` (PostgreSQL). Extiende el modelo de [Iteración 1](../iteracion1/data-model.md) con migraciones Alembic. Sin cambios en las tablas existentes salvo lo indicado.

## Cambios de esquema respecto a Iteración 1

### conductor (existente — sin cambios de estructura)

Las columnas `latitud`, `longitud` y `fecha_act_ubic` ya existen en la tabla desde la Iteración 1 (creadas como nulas). En esta iteración se activan: el `PATCH /conductores/{id}` puede actualizarlas y el `GET /conductores` las usa para filtrar.

> **Migración**: solo verificación de que las columnas existen; no se crea nada nuevo en esta tabla.

### vehiculo_documento (nueva)

Análoga a `documento_conductor`, pero con FK a `vehiculo`.

| Campo | Tipo | Reglas |
|---|---|---|
| id_vehiculo_documento | bigint, PK | Autogenerado |
| id_vehiculo | bigint, FK → vehiculo | Obligatorio; `ON DELETE RESTRICT` |
| tipo | texto | Solo `REVISION_TECNICA` u otros tipos definidos en el contrato |
| numero | texto | Obligatorio |
| categoria | texto | Opcional |
| fecha_emision | fecha | Obligatoria |
| fecha_vencimiento | fecha | Obligatoria; posterior a `fecha_emision` |
| url_archivo | texto | Obligatorio, URI válida |
| fecha_registro | timestamptz | Autogenerada por la base |

El estado `VIGENTE` o `VENCIDO` **no se guarda**: se calcula al leer comparando `fecha_vencimiento` con la fecha actual (mismo mecanismo que `documento_conductor`).

### vehiculo_tipo_servicio (existente — cambio de comportamiento)

No cambia el esquema. La columna `habilitado` (por defecto `falso` en Iteración 1) ahora es actualizable mediante `PATCH /conductores/{id}/vehiculos/{id_vehiculo}`. El repositorio de vehículos gestiona la actualización en la misma transacción.

## Migración Alembic

```
0002_vehiculo_documento.py
  UP:
    - Verificar que latitud, longitud, fecha_act_ubic existen en conductor (no-op si ya están)
    - CREATE TABLE vehiculo_documento (...)
    - CHECK en tipo de documento
    - FK con ON DELETE RESTRICT
  DOWN:
    - DROP TABLE vehiculo_documento
```

## Relaciones nuevas

- Un vehículo tiene cero o más documentos de vehículo.
- Los documentos de vehículo son de solo escritura: nunca se actualizan ni se borran.

## Restricciones de integridad nuevas

- `vehiculo_documento.fecha_vencimiento` posterior a `fecha_emision` (CHECK).
- La clave foránea `id_vehiculo` usa `ON DELETE RESTRICT` para preservar trazabilidad.

## Notas para la implementación

- Los filtros de ubicación en `GET /conductores` usan `latitud` y `longitud` del conductor. La lógica de proximidad (si aplica) la define el contrato OpenAPI.
- `PATCH /conductores/{id}` solo acepta `conectado` y `disponible`; los demás campos son ignorados o devuelven `400`.
- El seed de Iteración 2 debe incluir conductores con latitud/longitud distintos y vehículos con `habilitado=true` en al menos un tipo de servicio, para poder probar los filtros.

# Contrato interno: catálogo de errores

Todos los errores usan el formato del contrato: `{"codigo": "...", "mensaje": "..."}`. El `codigo` es estable y en mayúsculas; el `mensaje` es legible y no expone datos sensibles.

| HTTP | `codigo` | Cuándo ocurre |
|---|---|---|
| 400 | `SOLICITUD_INVALIDA` | Cuerpo mal formado o parámetro inválido |
| 401 | `NO_AUTENTICADO` | Token ausente, inválido, vencido o de otro emisor |
| 403 | `SIN_PERMISOS` | Falta el rol `operador` o el `id_operador` del token |
| 404 | `NO_ENCONTRADO` | Conductor o vehículo inexistente (o vehículo de otro conductor) |
| 409 | `DNI_DUPLICADO` | Ya existe un conductor con ese DNI |
| 409 | `PATENTE_DUPLICADA` | Ya existe un vehículo con esa patente |
| 409 | `TRANSICION_INVALIDA` | La acción no está permitida desde el estado actual |
| 422 | `DATOS_INVALIDOS` | Incumple una regla de negocio de los datos (por ejemplo, vencimiento anterior a la emisión) |
| 422 | `LICENCIA_VIGENTE_REQUERIDA` | Aprobar un conductor sin licencia vigente |
| 500 | `ERROR_INTERNO` | Falla no prevista; sin detalles internos en el mensaje |

Mapeo desde los errores de dominio: ver [casos-de-uso.md](./casos-de-uso.md). La validación de forma (DNI de 7 u 8 dígitos, email, motivo no vacío, al menos un tipo de servicio) la hace el servidor y responde `400` con `SOLICITUD_INVALIDA`.

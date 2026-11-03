# Contrato interno: catálogo de errores (ampliación)

Amplía el [catálogo de la Iteración 1](../../iteracion1/contracts/errores.md); sus códigos siguen vigentes. Formato de todos los errores: `{"codigo": "...", "mensaje": "..."}`. El `codigo` es estable y en mayúsculas; el `mensaje` es legible y no expone datos sensibles.

## Códigos nuevos

| HTTP | `codigo` | Error de dominio | Cuándo ocurre |
|---|---|---|---|
| 403 | `ACCESO_PROHIBIDO` | `AccesoProhibido` | Un conductor intenta operar sobre otro conductor o sobre una solicitud ajena, o su token no trae un `id_conductor` numérico |
| 409 | `SOLICITUD_YA_RESPONDIDA` | `SolicitudYaRespondida` | La solicitud ya fue aceptada o rechazada |
| 409 | `VIAJE_EN_CONFLICTO` | `ViajeEnConflicto` | M6 informa un `id_viaje` ya procesado con datos distintos (otro conductor, destino, fecha o puntaje) |
| 410 | `SOLICITUD_VENCIDA` | `SolicitudVencida` | La oferta superó su `vence_en` (hora del servidor) o ya figura como `VENCIDA` |
| 422 | `CONDUCTOR_NO_HABILITADO` | `ConductorNoHabilitado` | No puede quedar disponible ni aceptar una solicitud: no está conectado, no está `APROBADA`, o no tiene un vehículo activo `APROBADA` |

`SOLICITUD_INVALIDA`, `NO_AUTENTICADO`, `SIN_PERMISOS`, `NO_ENCONTRADO`, `DATOS_INVALIDOS` y `ERROR_INTERNO` se reutilizan sin cambios.

## Uso de los códigos existentes en endpoints nuevos

| HTTP | `codigo` | Cuándo ocurre en la Iteración 2 |
|---|---|---|
| 400 | `SOLICITUD_INVALIDA` | Cuerpo vacío o mal formado, solo `latitud` o solo `longitud`, valores fuera de rango, `estado` de solicitud inválido, puntaje fuera de 1 a 5, `estado` distinto de `FINALIZADO` |
| 401 | `NO_AUTENTICADO` | Sin token o inválido, en cualquier endpoint |
| 403 | `SIN_PERMISOS` | El rol no alcanza (por ejemplo `servicio` en una acción de operador, o un conductor llamando a `/integraciones/...`: "Se requiere el rol servicio") |
| 404 | `NO_ENCONTRADO` | Conductor, vehículo o solicitud inexistente; vehículo activo inexistente o de otro conductor |
| 422 | `DATOS_INVALIDOS` | Documento de vehículo con vencimiento anterior a la emisión |

## Mapeo desde los errores de dominio

| Error de dominio | HTTP | `codigo` |
|---|---|---|
| `NoEncontrado` | 404 | `NO_ENCONTRADO` |
| `AccesoProhibido` | 403 | `ACCESO_PROHIBIDO` |
| `SolicitudYaRespondida` | 409 | `SOLICITUD_YA_RESPONDIDA` |
| `ViajeEnConflicto` | 409 | `VIAJE_EN_CONFLICTO` |
| `SolicitudVencida` | 410 | `SOLICITUD_VENCIDA` |
| `ConductorNoHabilitado` | 422 | `CONDUCTOR_NO_HABILITADO` |
| `DatosInvalidos` | 422 | `DATOS_INVALIDOS` |

Los cinco primeros de la tabla nueva se agregan a `MAPEO_ERRORES_DOMINIO` en `backend/app/api/errores.py`.

## Qué respuestas documenta el contrato

El contrato OpenAPI ya define `Gone` (`410`), `Conflict` (`409`) y `UnprocessableEntity` (`422`) como respuestas, y el ejemplo del `422` de M4 usa el código `CONDUCTOR_NO_HABILITADO`. Los códigos de esta tabla deben coincidir con los ejemplos del YAML; si algún ejemplo usa otro código, se corrige el ejemplo en una PR de contrato, no el catálogo.

## Para Testing

`CODIGOS_POR_ESTADO` de `backend/tests/contrato/test_openapi_ejemplos.py` debe incluir el `410` y estos códigos nuevos. Ese archivo es del grupo de Testing.

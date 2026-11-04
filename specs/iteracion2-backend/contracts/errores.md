# Contrato interno: catálogo de errores (ampliación)

Amplía el [catálogo de la Iteración 1](../../iteracion1/contracts/errores.md); sus códigos siguen vigentes. Formato de todos los errores: `{"codigo": "...", "mensaje": "..."}`. El `codigo` es estable y en mayúsculas; el `mensaje` es legible y no expone datos sensibles.

## Códigos nuevos

| HTTP | `codigo` | Error de dominio | Cuándo ocurre |
|---|---|---|---|
| 403 | `ACCESO_PROHIBIDO` | `AccesoProhibido` | Un conductor intenta operar sobre otro conductor o sobre una solicitud ajena, o su token no trae un `id_conductor` numérico |
| 409 | `SOLICITUD_YA_RESPONDIDA` | `SolicitudYaRespondida` | La solicitud ya fue aceptada o rechazada |
| 410 | `SOLICITUD_VENCIDA` | `SolicitudVencida` | La oferta superó su `vence_en` (hora del servidor) o ya figura como `VENCIDA` |
| 422 | `CONDUCTOR_NO_HABILITADO` | `ConductorNoHabilitado` | No puede quedar `DISPONIBLE` (no está `APROBADA` o no tiene un vehículo activo `APROBADA`) ni aceptar una solicitud (además, está `DESCONECTADO` u `OCUPADO`) |

`SOLICITUD_INVALIDA`, `NO_AUTENTICADO`, `SIN_PERMISOS`, `NO_ENCONTRADO`, `DATOS_INVALIDOS` y `ERROR_INTERNO` se reutilizan sin cambios.

## Uso de los códigos existentes en endpoints nuevos

| HTTP | `codigo` | Cuándo ocurre en la Iteración 2 |
|---|---|---|
| 400 | `SOLICITUD_INVALIDA` | Cuerpo vacío o mal formado, solo `latitud` o solo `longitud`, valores fuera de rango, `estado` de solicitud o de conductor inválido, o `estado: OCUPADO` en el `PATCH` de estado (lo asigna M3) |
| 401 | `NO_AUTENTICADO` | Sin token o inválido, en cualquier endpoint |
| 403 | `SIN_PERMISOS` | El rol no alcanza (por ejemplo `servicio` en una acción de operador o en el `PATCH` de estado) |
| 404 | `NO_ENCONTRADO` | Conductor, vehículo o solicitud inexistente; vehículo activo inexistente o de otro conductor |
| 422 | `DATOS_INVALIDOS` | Documento de vehículo con vencimiento anterior a la emisión |

## Mapeo desde los errores de dominio

| Error de dominio | HTTP | `codigo` |
|---|---|---|
| `NoEncontrado` | 404 | `NO_ENCONTRADO` |
| `AccesoProhibido` | 403 | `ACCESO_PROHIBIDO` |
| `RolNoAutorizado` | 403 | `SIN_PERMISOS` |
| `SolicitudYaRespondida` | 409 | `SOLICITUD_YA_RESPONDIDA` |
| `SolicitudVencida` | 410 | `SOLICITUD_VENCIDA` |
| `ConductorNoHabilitado` | 422 | `CONDUCTOR_NO_HABILITADO` |
| `DatosInvalidos` | 422 | `DATOS_INVALIDOS` |

Los errores de la tabla nueva y `RolNoAutorizado` se agregan a `MAPEO_ERRORES_DOMINIO` en `backend/app/api/errores.py`. `RolNoAutorizado` lo lanza la política de acceso cuando el rol no alcanza y mantiene el código `SIN_PERMISOS` de la Iteración 1.

## Qué respuestas documenta el contrato

El contrato OpenAPI ya define `Gone` (`410`), `Conflict` (`409`) y `UnprocessableEntity` (`422`) como respuestas, y el `422` del `PATCH /conductores/{id}/estado` usa en su ejemplo el código `CONDUCTOR_NO_HABILITADO`. Los códigos de esta tabla deben coincidir con los ejemplos del YAML; si algún ejemplo usa otro código, se corrige el ejemplo en una PR de contrato, no el catálogo.

## Para Testing

`CODIGOS_POR_ESTADO` de `backend/tests/contrato/test_openapi_ejemplos.py` debe incluir el `410` y estos códigos nuevos. Ese archivo es del grupo de Testing.

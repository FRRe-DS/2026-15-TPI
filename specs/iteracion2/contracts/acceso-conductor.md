# Contrato interno: acceso de conductor a sus propios datos

Punto de sincronización entre el **Stack 1** (política de acceso) y el **Stack 2** (dependencia FastAPI). Complementa [token-jwt.md de Iteración 1](../iteracion1/contracts/token-jwt.md).

## Regla

Un usuario con rol `conductor` solo puede operar sobre los recursos cuyo `id_conductor` coincida con el `id_conductor` que viene en su token. Un usuario con rol `operador` puede operar sobre cualquier `id_conductor`.

## Claim del token

El token de un conductor incluye el claim `id_conductor` (entero) además de `realm_access.roles`. El Stack 3 lo configura en el realm de Keycloak igual que `id_operador` para el operador.

| Claim | Tipo | Usuario |
|---|---|---|
| `realm_access.roles` | lista | todos |
| `id_operador` | entero | solo operadores |
| `id_conductor` | entero | solo conductores |

## Endpoints afectados

Todos los endpoints con `{id_conductor}` en la ruta que no sean exclusivos de operador:

| Endpoint | Acceso conductor | Acceso operador |
|---|---|---|
| `GET /conductores/{id_conductor}` | Solo el propio | Cualquiera |
| `PATCH /conductores/{id_conductor}` | Solo el propio | Cualquiera |
| `GET /conductores/{id_conductor}/vehiculos` | Solo los propios | Cualquiera |
| `GET /conductores/{id_conductor}/vehiculos/{id}` | Solo los propios | Cualquiera |
| `GET /conductores/{id_conductor}/documentacion` | Solo la propia | Cualquiera |
| `GET /conductores/{id_conductor}/vehiculos/{id}/documentacion` | Solo los propios | Cualquiera |
| `GET /conductores/{id_conductor}/vehiculos/{id}/habilitacion` | Solo los propios | Cualquiera |
| `POST /conductores/{id_conductor}/habilitacion` | **Solo operador** (`403` para conductor) | Cualquiera |
| `POST /conductores/{id_conductor}/documentacion` | **Solo operador** | Cualquiera |
| `POST /conductores/{id_conductor}/vehiculos` | **Solo operador** | Cualquiera |
| `POST /conductores/{id_conductor}/vehiculos/{id}/habilitacion` | **Solo operador** | Cualquiera |
| `POST /conductores/{id_conductor}/vehiculos/{id}/documentacion` | **Solo operador** | Cualquiera |
| `PATCH /conductores/{id_conductor}/vehiculos/{id}` | **Solo operador** | Cualquiera |

## Respuesta de error

```json
{"codigo": "ACCESO_PROHIBIDO", "mensaje": "No tenés permiso para acceder a los datos de este conductor"}
```

HTTP `403`. Se agrega `ACCESO_PROHIBIDO` al catálogo de errores de [errores.md de Iteración 1](../iteracion1/contracts/errores.md).

## Implementación

- **Stack 1**: `backend/app/aplicacion/politicas/acceso_conductor.py` — función pura `verificar_acceso_conductor(id_del_token, id_del_recurso)` que lanza `AccesoProhibido` si no coinciden y el token no es de operador.
- **Stack 2**: dependencia FastAPI `exigir_acceso_propio_o_operador` en `backend/app/api/seguridad.py` que extrae el claim del token inyectado y llama a la función del Stack 1. Se aplica en cada router afectado.

## Tokens para pruebas

Los tests de API (Stack 2) firman tokens con los claims `id_conductor` o `id_operador` según el escenario. No dependen de Keycloak, igual que en Iteración 1.

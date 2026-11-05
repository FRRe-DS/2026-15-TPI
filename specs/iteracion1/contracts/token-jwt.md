# Contrato interno: token JWT

Punto de sincronización entre el **Stack 3** (emite, vía Keycloak), el **Stack 2** (valida) y el **Stack 5** (obtiene).

## Emisor

- Servicio: Keycloak, realm `m3`.
- Claves públicas (JWKS): `{KEYCLOAK_URL}/realms/m3/protocol/openid-connect/certs`.
- Emisor esperado (`iss`): `{KEYCLOAK_URL}/realms/m3`. La URL se configura por variable de entorno.

## Claims que la API exige

| Claim | Tipo | Uso |
|---|---|---|
| `iss` | texto | Debe coincidir con el emisor configurado |
| `exp` | número | Token vencido → `401` |
| `realm_access.roles` | lista | Contiene `operador`, `conductor` y/o `servicio` |
| `id_operador` | entero | Solo en usuarios operador; se guarda en el evento de habilitación |
| `id_conductor` | entero | Solo en usuarios conductor; identifica al conductor dueño del token |

## Reglas de validación

1. Sin encabezado `Authorization: Bearer ...`, firma inválida, token vencido o emisor distinto → `401`.
2. Las lecturas de `GET /conductores`, detalle, habilitación, vehículos, tipos de servicio, `/estado` y `/ubicacion` admiten `operador` y `servicio`; un `conductor` solo puede leer sus propios datos y recibe `403` en `GET /conductores`.
3. Las operaciones de escritura requieren `operador` o `conductor`; el rol `servicio` es de solo lectura y recibe `403` en cualquier escritura, incluido `PATCH /conductores/{id}/estado` y `POST /solicitudes/{id}`.
4. Las acciones de habilitación exigen el rol `operador`; sin él → `403`.
5. Un operador sin `id_operador` numérico en el token → `403` en las acciones de habilitación.
6. Un conductor que consulta o modifica datos de otro conductor → `403 ACCESO_PROHIBIDO`; la comprobación se hace antes de buscar el recurso.
7. Un conductor sin `id_conductor` numérico → `403 ACCESO_PROHIBIDO` en cualquier operación sobre un conductor.

## Realm de prueba (Stack 3)

| Elemento | Detalle |
|---|---|
| Roles | `operador`, `conductor`, `servicio` |
| Usuario operador de prueba | Rol `operador`, atributo `id_operador` numérico incluido como claim mediante un mapeador |
| Usuario conductor de prueba | Rol `conductor` |
| Usuario de servicio de prueba | Rol `servicio` (solo lectura) |
| Cliente para el frontend | Confidencial, con concesión de contraseña habilitada, solo para el entorno local |
| Secretos y contraseñas | Variables de entorno con sustitución en el archivo del realm; sin valores en el repo |

## Tokens para pruebas

Los tests de la API (Stack 2) y de contrato/integración (Stack 4) firman sus propios tokens con una clave RSA de prueba generada en el test, y exponen su JWKS a la dependencia de validación. No dependen de Keycloak.

### Helpers de token

- Deben existir helpers equivalentes para los tres roles: conductor, operador y `servicio`.
- `headers_servicio` (o el nombre acordado) firma un token con `roles=["servicio"]`, sin `id_operador` ni `id_conductor`.
- El helper base debe aceptar `roles`, `id_conductor` e `id_operador` para cubrir la matriz completa: conductor propio, conductor ajeno, operador y servicio.
- La cuenta técnica de servicio la define el grupo de Datos y seguridad; en pruebas se representa con un token firmado, no con una cuenta real de Keycloak.

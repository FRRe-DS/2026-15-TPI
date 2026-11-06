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
| `realm_access.roles` | lista | Contiene `operador` y/o `conductor` |
| `id_operador` | entero | Solo en usuarios operador; se guarda en el evento de habilitación |

## Reglas de validación

1. Sin encabezado `Authorization: Bearer ...`, firma inválida, token vencido o emisor distinto → `401`.
2. Cualquier rol válido (`operador` o `conductor`) puede usar los endpoints, salvo las acciones de habilitación.
3. Las acciones de habilitación exigen el rol `operador`; sin él → `403`.
4. Un operador sin `id_operador` numérico en el token → `403` en las acciones de habilitación.

## Realm de prueba (Stack 3)

| Elemento | Detalle |
|---|---|
| Roles | `operador`, `conductor` |
| Usuario operador de prueba | Rol `operador`, atributo `id_operador` numérico incluido como claim mediante un mapeador |
| Usuario conductor de prueba | Rol `conductor` |
| Cliente para el frontend | Confidencial, con concesión de contraseña habilitada, solo para el entorno local |
| Secretos y contraseñas | Variables de entorno con sustitución en el archivo del realm; sin valores en el repo |

## Tokens para pruebas

Los tests de la API (Stack 2) y de contrato/integración (Stack 4) firman sus propios tokens con una clave RSA de prueba generada en el test, y exponen su JWKS a la dependencia de validación. No dependen de Keycloak.

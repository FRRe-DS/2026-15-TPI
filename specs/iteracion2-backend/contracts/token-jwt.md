# Contrato interno: token JWT y política de acceso (ampliación)

Punto de sincronización entre el **Stack 3** (emite, vía Keycloak), el **Stack 2** (valida y aplica la política) y el **Stack 1** (política pura). Amplía el [contrato de la Iteración 1](../../iteracion1/contracts/token-jwt.md): el emisor, la validación de firma y vencimiento y los tokens de prueba no cambian.

## Claims que la API exige

| Claim | Tipo | Uso | Cambio |
|---|---|---|---|
| `iss` | texto | Debe coincidir con el emisor configurado | sin cambios |
| `exp` | número | Token vencido → `401` | sin cambios |
| `realm_access.roles` | lista | Contiene `operador`, `conductor` y/o `servicio` | suma `servicio` |
| `id_operador` | entero | Solo operadores; se guarda en el evento de habilitación | sin cambios |
| `id_conductor` | entero | Solo conductores; identifica al conductor dueño del token | **nuevo** |

- `id_conductor` y `id_operador` deben ser enteros. Un valor booleano no es válido.
- Un token de rol `servicio` no necesita otro claim: la cuenta técnica de M4 solo trae el rol. Es de solo lectura.
- El backend no usa el `id_conductor` del cuerpo ni de la consulta para decidir el acceso: siempre el del token.

## Reglas de validación

1. Sin encabezado `Authorization: Bearer ...`, firma inválida, token vencido o emisor distinto → `401`.
2. Un token sin ningún rol reconocido (`operador`, `conductor`, `servicio`) → `403`.
3. Cada operación admite ciertos roles (matriz de abajo). Un rol que no está admitido → `403` `SIN_PERMISOS`. El rol `servicio` solo puede leer: cualquier escritura → `403`.
4. Un token de conductor sin `id_conductor` numérico → `403` `ACCESO_PROHIBIDO` en cualquier operación sobre un conductor.
5. Un conductor que opera sobre el `id_conductor` de otro → `403` `ACCESO_PROHIBIDO`. Esto se evalúa **antes** de buscar el recurso: aunque el otro conductor no exista, la respuesta es `403` y no `404`.
6. Con varios roles en el token, vale lo que permita cualquiera de ellos. Si un token es de conductor y de operador, el acceso de operador no queda limitado por el `id_conductor`.
7. Las acciones de habilitación exigen además un `id_operador` numérico (sin cambios).

## Matriz de acceso por operación

**`propio`**: un conductor solo puede operar sobre su propio `id_conductor`. **—**: no permitido (`403` `SIN_PERMISOS`).

| # | Operación | operador | conductor | servicio |
|---|---|---|---|---|
| 1 | `POST /conductores` | sí | sí | — |
| 2 | `GET /conductores` | sí | — | sí |
| 3 | `GET /conductores/{id}` | sí | propio | sí |
| 4 | `GET /conductores/{id}/habilitacion` | sí | propio | sí |
| 5 | `POST /conductores/{id}/habilitacion` | sí (con `id_operador`) | — | — |
| 6 | `POST /conductores/{id}/documentacion` | sí | propio | — |
| 7 | `POST /conductores/{id}/vehiculos` | sí | propio | — |
| 8 | `GET /conductores/{id}/vehiculos` | sí | propio | sí |
| 9 | `GET /conductores/{id}/vehiculos/{id_vehiculo}` | sí | propio | sí |
| 10 | `POST /conductores/{id}/vehiculos/{id_vehiculo}/habilitacion` | sí (con `id_operador`) | — | — |
| 11 | `GET .../vehiculos/{id_vehiculo}/tipos-servicio` | sí | propio | sí |
| 12 | `POST .../vehiculos/{id_vehiculo}/documentacion` | sí | propio | — |
| 13 | `GET /conductores/{id}/estado` | sí | propio | sí |
| 14 | `PATCH /conductores/{id}/estado` | sí | propio | — |
| 15 | `GET /conductores/{id}/ubicacion` | sí | propio | sí |
| 16 | `GET /conductores/{id}/solicitudes` | sí | propio | — |
| 17 | `POST /solicitudes/{id_solicitud}` | sí | solo si es la dueña | — |

Notas:
- El alta (`POST /conductores`) es de operador y conductor porque todavía no existe un `id_conductor` propio. El rol `servicio` no da altas.
- En la operación 17 el conductor dueño se conoce al leer la solicitud: inexistente → `404`; ajena, pedida por un conductor → `403` `ACCESO_PROHIBIDO`.
- Los operadores y las cuentas de servicio no tienen restricción por conductor dentro de lo que su rol permite.
- El contrato 1.2.0 no tiene operaciones de integración: el rol `servicio` solo aparece en las lecturas de la matriz (operaciones 2, 3, 4, 8, 9, 11, 13 y 15).

## Cómo se aplica

- **Stack 1**: `backend/app/aplicacion/politicas/acceso.py`, función pura sin dependencias de FastAPI ni de JWT. Recibe roles, ids y los roles admitidos de la operación.
- **Stack 2**: dependencias reutilizables en `backend/app/api/seguridad.py`, una por patrón de la matriz: operador o servicio; conductor propio, operador o servicio; conductor propio u operador; solo operador (la existente). Cada router elige la que corresponde a su operación.
- Un cambio en la matriz se hace primero en este documento y después en las dependencias y sus tests.

## Realm de prueba (Stack 3)

Lo que Backend necesita de Datos y seguridad (issue #36):

| Elemento | Detalle |
|---|---|
| Rol `servicio` | Rol de realm nuevo |
| Cuenta técnica | Una de M4 con el rol `servicio` (solo lectura); credenciales por variables de entorno, sin valores en el repo |
| Usuario conductor de prueba | Su claim `id_conductor` debe coincidir con un conductor del seed |
| Mapeador | El claim `id_conductor` se incluye como entero en el token de acceso, igual que `id_operador` |

## Tokens para pruebas

Los tests de API firman sus propios tokens con la clave RSA de prueba, como en la Iteración 1. Hace falta un ayudante que acepte la lista de roles y el `id_conductor` o `id_operador` según el caso, para cubrir la matriz completa sin Keycloak.

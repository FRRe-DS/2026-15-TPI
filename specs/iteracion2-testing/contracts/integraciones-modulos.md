# Matriz de contratos bilaterales M3

## Regla de aceptación

Cada doble debe construirse a partir del contrato OpenAPI/JWT/evento aprobado por el módulo propietario y validarlo automáticamente. Un OpenAPI que solo incluya `info` y `version` no constituye contrato verificable. Los cambios incompatibles deben hacer fallar el job de CI; no se arregla un test relajando el esquema.

## Contrato vigente de M3

El contrato de M3 tiene **17 operaciones** (antes 19). Se retiraron `PATCH /integraciones/m4/.../disponibilidad` y `POST /integraciones/m6/.../finalizacion`: M3 ya no expone escrituras para otros módulos.

- `Conductor.estado` reemplaza a `conectado` y `disponible`, con los valores `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`.
- `GET /conductores` filtra por `estado`; el filtro `disponible` ya no existe.
- `OCUPADO` lo asigna M3 cuando un conductor acepta una solicitud. No se puede solicitar en `PATCH /conductores/{id}/estado`: responde `400`.
- El rol `servicio` es de solo lectura.

### Catálogo de errores ampliado

Para la Iteración 2, `CODIGOS_POR_ESTADO` de `backend/tests/contrato/test_openapi_ejemplos.py` debe incluir:

| HTTP | Código | Cuándo ocurre |
|---|---|---|
| 403 | `ACCESO_PROHIBIDO` | Un conductor opera sobre otro conductor o sobre una solicitud ajena, o su token no trae `id_conductor` numérico |
| 409 | `SOLICITUD_YA_RESPONDIDA` | La solicitud ya fue aceptada o rechazada |
| 410 | `SOLICITUD_VENCIDA` | La oferta superó `vence_en` o ya figura como `VENCIDA` |
| 422 | `CONDUCTOR_NO_HABILITADO` | No puede quedar `DISPONIBLE` (sin aprobación o sin vehículo activo aprobado) ni aceptar una solicitud (además, `DESCONECTADO` u `OCUPADO`) |

Se reutilizan `SOLICITUD_INVALIDA` (400), `NO_AUTENTICADO` (401), `SIN_PERMISOS` (403), `NO_ENCONTRADO` (404), `DATOS_INVALIDOS` (422) y `ERROR_INTERNO` (500). El contrato local debe reflejar estos códigos en sus ejemplos; si no coincide, se corrige el ejemplo en una PR de contrato.

### Operaciones de la Iteración 2 y roles

| Operación | operador | conductor | servicio |
|---|---|---|---|
| `GET .../vehiculos/{id}/tipos-servicio` | sí | propio | sí |
| `POST .../vehiculos/{id}/documentacion` | sí | propio | no (`403`) |
| `GET /conductores/{id}/estado` | sí | propio | sí |
| `PATCH /conductores/{id}/estado` | sí | propio | no (`403`) |
| `GET /conductores/{id}/ubicacion` | sí | propio | sí |
| `GET /conductores/{id}/solicitudes` | sí | propio | no (`403`) |
| `POST /solicitudes/{id}` | sí | solo si es la dueña | no (`403`) |

**Reglas de rol**: `servicio` recibe `403` en cualquier escritura, en `PATCH /estado` y en `POST /solicitudes/{id}`. Un conductor recibe `403` al consultar o modificar datos de otro conductor y en `GET /conductores`; en `POST /solicitudes/{id}`, una solicitud inexistente da `404` y una ajena da `403 ACCESO_PROHIBIDO`. Se requiere un helper de token `servicio` equivalente a los de conductor y operador; la cuenta técnica la define Datos y seguridad.

## Matriz

| Módulo | Rol de M3 / operaciones a verificar | Documento actual comprobado | Requisito para cerrar la frontera |
|---|---|---|---|
| M1 Identidad | Validación de JWT/JWKS y roles; usar token real Keycloak del Compose para E2E. Verificar el rol `servicio` de solo lectura. | [`specs/iteracion1/contracts/token-jwt.md`](../../iteracion1/contracts/token-jwt.md) describe `realm_access.roles` e `id_operador`; ahora incluye `operador`, `conductor` y `servicio` (solo lectura). No se encontró OpenAPI de M1 en el repo común. | M1 debe publicar el contrato canónico de emisor, claims, JWKS, roles de servicio/usuario y errores. El rol `servicio` solo puede ejecutar lecturas; cualquier escritura responde `403`. Acordar mapeo compatible con los tokens del realm de prueba; no aceptar claims alternativos sin acuerdo. |
| M4 Ubicación | M4 consulta M3 en solo lectura: `GET /conductores`, `GET /conductores/{id_conductor}`, `GET /conductores/{id_conductor}/estado` y `GET /conductores/{id_conductor}/ubicacion`. M4 no escribe en M3. El acceso se hace con token `servicio` (solo lectura). | El README local documenta las lecturas y un mapeo preliminar; `contratos/m4_ubicacion/openapi.yml` común solo contiene metadata. | Acordar nombres y tipos (en particular `estado` con sus cuatro valores, ID entero, coordenadas nulas —nunca `0,0`— y tipo de vehículo), seguridad y respuestas/errores; completar OpenAPI antes del doble. |
| M5 Solicitud | M5 consume M3: `GET /conductores/{id_conductor}/solicitudes` y `POST /solicitudes/{id_solicitud}`. Sin cambios en esta iteración. | OpenAPI local incluye los endpoints y esquema `Solicitud`; son de la Iteración 2 y todavía no existen en `dev`. `contratos/m5_solicitud/openapi.yml` común solo contiene metadata. | Acordar modelo, estados, campos de respuesta/solicitud, códigos HTTP (`410 SOLICITUD_VENCIDA`, `409 SOLICITUD_YA_RESPONDIDA`, `422 CONDUCTOR_NO_HABILITADO`) y token de servicio; completar el contrato propietario antes del doble. |

**M6 no forma parte de las fronteras de esta iteración.** Sus operaciones se retiraron del contrato de M3, M3 no implementa clientes HTTP salientes y M6 tampoco escribe en M3.

## Tipos de pruebas

- **M1**: doble de JWKS/emisor que firma JWT conforme al contrato aprobado para pruebas de integración contractual; E2E aparte obtiene tokens del Keycloak real de Compose.
- **M4/M5**: validar el contrato consumidor de M3 (campos HTTP que M3 expone). M4 es de solo lectura y M5 queda para la Iteración 2; en esta iteración M3 no implementa clientes HTTP salientes ni endpoints de escritura para M4/M6. Para las lecturas con rol `servicio`, el doble es un **token firmado con ese rol**, no un endpoint HTTP simulado. No acceder a DBs de los módulos.
- **Mensajes**: RabbitMQ real con una cola exclusiva temporal; validar envelope y payload contra [`eventos-m3.md`](./eventos-m3.md) cuando esté aprobado. **Bloqueado**: no se implementa ni se prueba mientras FR-007/FR-013 siga sin decisión.

Hasta completar los artefactos faltantes, una prueba de esquema local puede cubrir OpenAPI M3 propio pero no se reporta como prueba de integración contractual del módulo vecino.

## Decisiones de planificación

- **Eventos**: el contrato 1.2.0 no define eventos y el backend de la Iteración 2 no los incluye. FR-013 prohíbe introducir funcionalidades de negocio nuevas. La Historia 3/FR-007–FR-009 y la PR 3 quedan bloqueadas hasta que la cátedra decida si M3 publica eventos (spec propio de Backend) o si se retiran.
- **PR 4**: se limita a lo que M3 expone: lecturas de M4 (`GET /conductores`, detalle, `/estado`, `/ubicacion`) y solicitudes de M5. No prueba clientes salientes ni escrituras de M4/M6.
- **Orden**: PR 1 y PR 2 usan endpoints existentes y pueden avanzar sin esperar. La migración `0002` reemplaza `conectado`/`disponible` por `estado`; los tests que usan esas columnas se ajustan cuando llegue. Las pruebas de los 7 endpoints dependen de esa migración y del backend, y van después.
- **Cobertura/CI**: el umbral vigente es `65 %`; se propone `70 %` para la Iteración 2. Las pruebas nuevas de contrato e integración deben ejecutarse en el jobs existentes de `ci.yml` (`contrato`, `test` y `entorno`).

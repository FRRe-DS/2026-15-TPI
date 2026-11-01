# Matriz de contratos bilaterales M3

## Regla de aceptación

Cada doble debe construirse a partir del contrato OpenAPI/JWT/evento aprobado por el módulo propietario y validarlo automáticamente. Un OpenAPI que solo incluya `info` y `version` no constituye contrato verificable. Los cambios incompatibles deben hacer fallar el job de CI; no se arregla un test relajando el esquema.

## Matriz

| Módulo | Rol de M3 / operaciones a verificar | Documento actual comprobado | Requisito para cerrar la frontera |
|---|---|---|---|
| M1 Identidad | Validación de JWT/JWKS y roles; usar token real Keycloak del Compose para E2E. | [`specs/iteracion1/contracts/token-jwt.md`](../../iteracion1/contracts/token-jwt.md) describe `realm_access.roles` e `id_operador`. La fuente común M6 describe `sub`/`identidad_id` y `role`/`roles`. No se encontró OpenAPI de M1 en el repo común. | M1 debe publicar el contrato canónico de emisor, claims, JWKS, roles de servicio/usuario y errores. Acordar mapeo compatible con los tokens del realm de prueba; no aceptar claims alternativos sin acuerdo. |
| M4 Ubicación | M4 consulta M3: `GET /conductores` y `GET /conductores/{id_conductor}`; disponibilidad, ubicación, fecha y tipos/IDs conforme al esquema acordado. | El README local documenta esas lecturas y un mapeo preliminar; `contratos/m4_ubicacion/openapi.yml` común solo contiene metadata. | Acordar nombres y tipos (en particular ID entero, coordenadas nulas y tipo de vehículo), seguridad y respuestas/errores; completar OpenAPI antes de doble. |
| M5 Solicitud | M5 consume M3: `GET /conductores/{id_conductor}/solicitudes` y `POST /solicitudes/{id_solicitud}`. | OpenAPI local incluye los endpoints y esquema `Solicitud`; `contratos/m5_solicitud/openapi.yml` común solo contiene metadata. | Acordar modelo, estados, campos de respuesta/solicitud, códigos HTTP y token servicio; completar el contrato propietario. |
| M6 Viajes | M3 consume consulta, cierre y cancelación de viaje; validar cliente HTTP saliente frente al contrato M6. | Contrato común `FRRe-DS/2026-TPI`, commit `69e9481c754063fc054c8d0ecfdec18d71bf48e6`, `contratos/m6_viajes/openapi.yml`: `GET /trips/{id}`, `POST /trips/{id}/complete`, `POST /trips/{id}/cancel`; OpenAPI local M3 muestra rutas `/viajes/...` y nombres `/finalizar`, `/cancelar`. | Acordar explícitamente contrato consumido y compatibilidad de rutas, UUID vs. ID entero, estados, payloads, roles M1 y errores. M6 también menciona evento `TripCompleted` hacia M3; el alcance actual dice que M3 no consume eventos, por lo que esa dirección debe confirmarse y excluirse o incorporarse mediante cambio de alcance antes de probarla. |

## Tipos de pruebas

- **M1**: doble de JWKS/emisor que firma JWT conforme al contrato aprobado para pruebas de integración contractual; E2E aparte obtiene tokens del Keycloak real de Compose.
- **M4/M5**: validar el contrato consumidor de M3 (campos HTTP que M3 expone) y el lado proveedor si M3 implementa llamadas a esos servicios; no acceder a DBs de los módulos.
- **M6**: doble HTTP que valida solicitudes salientes y respuestas simuladas contra la copia versionada del OpenAPI M6; prueba cada ruta y error que M3 realmente consume.
- **Mensajes**: RabbitMQ real con una cola exclusiva temporal; validar envelope y payload contra [`eventos-m3.md`](./eventos-m3.md) cuando esté aprobado.

Hasta completar los artefactos faltantes, una prueba de esquema local puede cubrir OpenAPI M3 propio pero no se reporta como prueba de integración contractual del módulo vecino.

# Especificación: Iteración 2 — Frontend de M3 (app del conductor)

**Grupo 15 · Módulo M3 (Conductores y Vehículos) · Equipo de Frontend**

**Plan**: [plan.md](./plan.md) | **Tareas**: [tasks.md](./tasks.md) | **Contrato**: `docs/contract/openapi.yaml` (1.2.0)

## Resumen

La Iteración 1 dejó una sola pantalla: el listado de conductores. En la Iteración 2 el frontend pasa «de mocks a la API real» (diapositiva de la cátedra) y suma la **app del conductor**, con las funcionalidades que indicaron los profesores:

- Iniciar sesión.
- Ponerse en línea (disponible para trabajar).
- Recibir pedidos y aceptarlos o rechazarlos.
- Confirmar cuando sube el pasajero.
- Finalizar el viaje.
- Enviar la ubicación simulada al M4 durante el viaje. No se muestra mapa.

El equipo decide el diseño. El trabajo se hace en dos fases: primero con datos mock, sin depender del backend, y después contra la API real.

## Historias de usuario

### US1 — Iniciar sesión (P1)

Como conductor quiero iniciar sesión con mi usuario y contraseña para usar la app con mi propia identidad.

**Escenarios de aceptación**

1. Con credenciales válidas, el conductor llega a la pantalla de estado.
2. Con credenciales inválidas, se muestra un mensaje de error y no se avanza.
3. Sin sesión, cualquier pantalla del conductor redirige al login.
4. Las credenciales y el token nunca llegan al código que corre en el navegador.

### US2 — Ponerse en línea (P1)

Como conductor quiero cambiar mi estado (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`) para controlar si recibo viajes.

**Escenarios de aceptación**

1. Se muestra el estado actual y los tres estados que se pueden pedir. `OCUPADO` nunca se ofrece.
2. Al pedir `DISPONIBLE` sin habilitación o sin vehículo activo aprobado, se muestra el error `CONDUCTOR_NO_HABILITADO` (422) y el estado no cambia.
3. Mientras se guarda se ve el estado de carga, y ante un fallo se ve el estado de error.

### US3 — Pedidos entrantes (P1)

Como conductor quiero ver mis solicitudes y aceptarlas o rechazarlas.

**Escenarios de aceptación**

1. Se listan las solicitudes con su estado (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`). Solo las `PENDIENTE` tienen botones de aceptar y rechazar.
2. Cada solicitud pendiente muestra cuánto falta para que venza (`vence_en`) y, al vencer, deja de ofrecer los botones.
3. Sin solicitudes se muestra «No hay solicitudes».
4. Si la oferta ya venció (410) se muestra «oferta vencida». Si hay conflicto (409) se muestra el conflicto.
5. Al aceptar, el conductor pasa a `OCUPADO` y la app lo lleva al viaje en curso.

### US4 — Viaje en curso (P2)

Como conductor quiero confirmar que subió el pasajero y finalizar el viaje.

**Escenarios de aceptación**

1. Tras aceptar una solicitud se muestra el viaje en curso.
2. «Pasajero subió» avanza el paso mostrado.
3. «Finalizar viaje» pide el estado `DISPONIBLE`, libera al conductor y vuelve a las solicitudes.

### US5 — Ubicación simulada (P2)

Como conductor quiero que la app informe mi ubicación durante el viaje para que M4 pueda leerla.

**Escenarios de aceptación**

1. Mientras el conductor está `OCUPADO`, la app envía puntos de un recorrido simulado cada N segundos, con `latitud` y `longitud` juntas.
2. El envío se detiene cuando el viaje termina.
3. Se muestra la última coordenada y su fecha. Si la ubicación es desconocida (los tres campos en `null`), se muestra «desconocida», nunca (0, 0).
4. No se muestra mapa.

### US6 — Listado de conductores (ya existe)

La pantalla de la Iteración 1 se mantiene como vista de operador y servicio. Se actualiza al contrato 1.2.0 y muestra badges por estado de habilitación.

**Escenarios de aceptación**

1. Cada conductor muestra su estado de habilitación con un color distinto (verde, amarillo o rojo).
2. Se muestran los estados de carga, error y lista vacía.
3. El conductor no puede usar esta pantalla: el contrato le prohíbe `GET /conductores`.

## Requisitos funcionales

- **FR-001**: Toda pantalla del conductor tiene estados de carga, error y vacío.
- **FR-002**: Las pantallas funcionan con datos mock sin backend (`USE_MOCK=true`) y con la API real (`USE_MOCK=false`), sin cambiar el código de las pantallas.
- **FR-003**: Los errores de la API se muestran a partir de `{codigo, mensaje}`.
- **FR-004**: El frontend consume el contrato 1.2.0: `estado` operativo en lugar de `conectado` y `disponible`, más `id_vehiculo_activo`, `puntaje_promedio` y `cantidad_calificaciones`.
- **FR-005**: Al responder una solicitud se envía `respuesta` y `hora_rta` (fecha y hora, obligatoria en el contrato).
- **FR-006**: Una ubicación `null` se trata como desconocida.

## Fuera de alcance

- Mapa y GPS real.
- Calificaciones, documentación y alta de conductores o vehículos desde la app del conductor.
- Endpoint propio para «pasajero subió» (el contrato no lo tiene): es un estado local de la pantalla.
- Cambios al backend, al contrato o al realm de Keycloak.

## Criterios de éxito

- **SC-001**: Un conductor de prueba recorre sin errores login, disponible, pedido, aceptar y finalizar, primero en modo mock y después contra la API real.
- **SC-002**: `npm run test`, `npm run lint` y `npm run build` pasan en verde en CI.
- **SC-003**: Cada pantalla muestra los tres estados (carga, error y vacío) y coincide con su diseño.
- **SC-004**: El `frontend/README.md` explica cómo correr en modo mock y en modo real.

## Supuestos y dependencias

- Todo lo que necesita el backend (`estado`, `ubicacion`, `solicitudes`) está en el contrato 1.2.0 pero **todavía no está mergeado en `dev`**. Los mocks permiten avanzar hasta que se publique. La integración real está bloqueada hasta entonces (ver [plan.md](./plan.md)).
- El token del conductor trae el claim entero `id_conductor` (contrato, `bearerAuth`) y el realm `m3` ya lo mapea.
- «Finalizar viaje» como `PATCH` a `DISPONIBLE` falta acordarlo con M4 y M6.

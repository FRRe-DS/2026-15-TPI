# Tareas: Iteración 2 — Frontend de M3

**Fuentes**: [spec.md](./spec.md), [plan.md](./plan.md) y `docs/contract/openapi.yaml` (1.2.0).

**Numeración**: T701–T799, reservada para Frontend. Las numeraciones anteriores (`M-xx`, `F-xx`, `T242`–`T249`) se reemplazan por esta.

**Formato**: `- [ ] Txxx [P] [USn] Descripción con ruta`. `[P]` indica que se puede hacer en paralelo. Cada `[Test]` va antes de su `[Impl]` y los dos van en la misma PR. Las rutas son `frontend/…`.

**Dueños**: stack A (datos y mocks), stack B (interfaz) y pantallas. Ver [plan.md](./plan.md).

## Fase 1: Diseño y estilos (stack B, sin código de lógica)

- [x] T701 [P] Crear en `src/app/diseno/` un prototipo visual aislado de las pantallas login, estado, pedidos, viaje en curso y ubicación, cada una con sus estados de carga, error y vacío. Se autorizó esta alternativa en React a Stitch/Figma; documentar cómo abrirla en `specs/iteracion2-frontend/diseno.md`.
- [x] T702 Documentar en `specs/iteracion2-frontend/diseno.md` los valores base del prototipo (colores, tipografías, espaciados y radios de borde).
- [x] T703 Pasar esos valores como variables CSS a `src/app/globals.css` e importar la hoja desde el layout de la aplicación.

## Fase 2: Cimientos (bloquean las pantallas)

**Stack A · tipos y cliente de API** (una PR desde `dev`)

- [ ] T704 Actualizar `src/lib/tipos.ts` al contrato 1.2.0: `estado` operativo (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) en lugar de `conectado` y `disponible`; sumar `id_vehiculo_activo`, `puntaje_promedio` y `cantidad_calificaciones`; agregar los tipos `EstadoConductor`, `EstadoConductorRequest`, `UbicacionConductor`, `Solicitud` y `RespuestaSolicitudRequest` (`respuesta` y `hora_rta` obligatorios). Ajustar mocks y tests existentes.
- [ ] T705 [Test] Extender `src/lib/api.test.ts`: `obtenerEstado`, `actualizarEstado` (PATCH con estado, ubicación opcional y `latitud` con `longitud` juntas), `listarSolicitudes` (filtro `estado`), `responderSolicitud` y `obtenerUbicacion` envían `Authorization: Bearer`, usan el método y la URL del contrato y lanzan `ErrorApi` con `{codigo, mensaje}` ante 401, 403, 404, 409, 410 y 422.
- [ ] T706 [Impl] Implementar esas funciones en `src/lib/api.ts` hasta que pase T705.

**Stack A · sesión del conductor** (apilada sobre T706)

- [ ] T711 [Test] `src/lib/sesion.test.ts`: la cookie es `httpOnly`; `id_conductor` se lee del claim del token; un token vencido o ausente cuenta como sin sesión; las credenciales nunca se devuelven al cliente.
- [ ] T712 [Impl] `src/lib/sesion.ts` y `src/app/api/sesion/route.ts` (login y logout contra Keycloak, realm `m3`) hasta que pase T711.

**Stack B · estados de pantalla**

- [x] T707 [Test] [P] `src/components/estados/estados.test.tsx`: `EstadoCarga`, `EstadoError` (con `role="alert"`) y `EstadoVacio` muestran su mensaje.
- [x] T708 [Impl] `src/components/estados/` hasta que pase T707.

**Stack B · navegación**

- [x] T709 [Test] [P] `src/components/Navegacion.test.tsx`: hay un enlace a cada pantalla y se marca la activa.
- [x] T710 [Impl] `src/components/Navegacion.tsx` y `src/app/layout.tsx` hasta que pase T709.

## Fase 3: Modo mock (stack A)

- [ ] T713 [Test] `src/mocks/conductores.mock.test.ts`: datos variados según el contrato (habilitación `APROBADA`, `PENDIENTE` y `RECHAZADA`; con y sin ubicación).
- [ ] T714 [Impl] `src/mocks/conductores.mock.ts` hasta que pase T713.
- [ ] T715 [Test] `src/app/page.test.tsx`: con `USE_MOCK=true` la pantalla usa los mocks y con `USE_MOCK=false` llama a la API.
- [ ] T716 [Impl] Soporte de `USE_MOCK` en `.env.example` y `src/app/page.tsx` hasta que pase T715. Va apilada sobre T714.
- [ ] T717 [Test] [P] `src/mocks/conductor.mock.test.ts`: conductor en cada estado operativo; solicitudes en `PENDIENTE`, `ACEPTADO`, `RECHAZADO` y `VENCIDA`; ubicación con valor y con los tres campos en `null`.
- [ ] T718 [Impl] `src/mocks/conductor.mock.ts` hasta que pase T717, respetando `USE_MOCK`.

## Fase 4: Listado de conductores con badges (US6)

Una sola PR desde `dev`, después de T704.

- [ ] T719 [Test] [US6] En `src/components/ListadoConductores.test.tsx`, verificar el renderizado de badges y colores por estado de habilitación (`APROBADA`, `PENDIENTE`, `OBSERVADA`, `SUSPENDIDA`, `RECHAZADA`).
- [ ] T720 [Impl] [US6] Mostrar los badges con colores diferenciados (verde, amarillo, rojo) en `src/components/ListadoConductores.tsx`. Va en la misma PR que T719.

## Fase 5: Pantallas del conductor

Una PR por pantalla, cada una con mocks primero y según su diseño de T701. Dependen de T706, T708, T710, T712 y T718.

**US1 · Iniciar sesión**

- [x] T721 [Test] [US1] `src/components/FormularioLogin.test.tsx` y `src/app/login/page.test.tsx`: campos usuario y contraseña, mensaje ante credenciales inválidas, redirección al autenticarse y redirección al login sin sesión. Las credenciales se procesan en el servidor, nunca en el navegador.
- [x] T722 [Impl] [US1] `src/components/FormularioLogin.tsx` y `src/app/login/page.tsx` hasta que pase T721.

**US2 · Ponerse en línea**

- [x] T723 [Test] [US2] `src/components/ControlEstado.test.tsx`: botones para `DESCONECTADO`, `CONECTADO` y `DISPONIBLE`; no ofrece `OCUPADO`; muestra el error `CONDUCTOR_NO_HABILITADO` (422); estados de carga y error.
- [x] T724 [Impl] [US2] `src/components/ControlEstado.tsx` y `src/app/estado/page.tsx` hasta que pase T723.

**US3 · Pedidos entrantes**

- [x] T725 [Test] [US3] `src/components/ListadoSolicitudes.test.tsx`: aceptar y rechazar solo en las `PENDIENTE`; cuenta regresiva con `vence_en` y botones deshabilitados al vencer; el cuerpo enviado trae `respuesta` y `hora_rta`; vacío «No hay solicitudes»; 410 muestra «oferta vencida»; 409 muestra el conflicto; carga y error.
- [x] T726 [Impl] [US3] `src/components/ListadoSolicitudes.tsx` y `src/app/solicitudes/page.tsx` hasta que pase T725.

**US4 · Viaje en curso**

- [x] T727 [Test] [US4] `src/components/ViajeEnCurso.test.tsx`: tras aceptar se muestra el viaje; «Pasajero subió» cambia el paso mostrado; «Finalizar viaje» pide `DISPONIBLE` y vuelve a las solicitudes.
- [x] T728 [Impl] [US4] `src/components/ViajeEnCurso.tsx` y `src/app/viaje/page.tsx` hasta que pase T727.

**US5 · Ubicación simulada**

- [x] T729 [Test] [US5] `src/lib/simuladorUbicacion.test.ts` (timers falsos de Vitest): genera puntos de un recorrido, envía `latitud` y `longitud` juntas cada N segundos mientras el conductor está `OCUPADO` y se detiene al terminar. Más `src/components/UbicacionActual.test.tsx`: muestra la última coordenada y su fecha; `null` se muestra como «desconocida», nunca como (0, 0).
- [x] T730 [Impl] [US5] `src/lib/simuladorUbicacion.ts`, `src/components/UbicacionActual.tsx` y `src/app/api/ubicacion/route.ts` hasta que pase T729. Sin mapa.

## Fase 6: Calidad

- [ ] T731 Validar que pasen en verde `npm run test`, `npm run lint` y `npm run build`.
- [ ] T732 Escribir `frontend/README.md`: cómo correr en modo mock y en modo real, y el recorrido de pantallas.

## Fase 7: Integración con la API real — BLOQUEADA

> **Bloqueada** hasta que el backend publique en `dev` `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. Hoy no están en `backend/`; están planificadas en `specs/iteracion2-backend/`. Cuando se publiquen, desbloquear esta fase y repetir T731.

- [ ] T733 Configurar `frontend/.env.local` con `USE_MOCK=false` y las variables de Keycloak y la API (copiar de `.env.example`).
- [ ] T734 Levantar el stack local con Docker Compose en `infra/` y verificar la salud en `http://localhost:8080/salud`.
- [ ] T735 Validar el login del conductor de prueba contra Keycloak y que el token traiga el claim `id_conductor`.
- [ ] T736 Probar `GET /api/v1/conductores` y validar el formato de respuesta.
- [ ] T737 Probar `GET` y `PATCH …/estado`, `GET …/ubicacion`, `GET …/solicitudes` y `POST /solicitudes/{id}` contra la API y comparar con los tipos de T704.
- [ ] T738 Verificar en el navegador (`npm run dev`) con los datos reales del seed: lista vacía y manejo de errores.
- [ ] T739 Recorrer con el compose y el seed login, disponible, pedido, aceptar y finalizar con `USE_MOCK=false`. Verificar carga, error y vacío en cada pantalla, el aspecto contra el diseño de T701 y anotar las diferencias con el contrato.
- [ ] T740 Corregir lo que salga de T737 y T739 y repetir T731.

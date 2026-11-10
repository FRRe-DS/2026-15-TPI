# Plan de implementación: Iteración 2 — Frontend de M3

**Spec**: [spec.md](./spec.md) | **Tareas**: [tasks.md](./tasks.md) | **Contrato**: `docs/contract/openapi.yaml` (1.2.0)

## Resumen

Se agregan las pantallas del conductor (login, estado, solicitudes, viaje en curso y ubicación) al frontend existente en `frontend/`, y se actualiza el listado de conductores al contrato 1.2.0. Cada pantalla se hace primero con mocks y después contra la API real.

## Contexto técnico

- **Stack** (ya justificado en la Iteración 1): Next.js 16.4, React 19.3, TypeScript 5.9, Vitest y ESLint. Un solo gestor de paquetes (`npm`) y un solo lockfile.
- **Estilos**: CSS Modules y variables en `frontend/src/app/globals.css`. No se agrega Tailwind (hoy no está instalado). Si el equipo decide otra cosa, se avisa al líder antes de sumar una dependencia.
- **Pruebas**: Vitest con TDD. El test va primero, no se modifica para hacerlo pasar y va en la misma PR que el código. Los timers se prueban con timers falsos de Vitest.
- **Punto de partida**: `frontend/src/lib/tipos.ts` y `frontend/src/lib/api.ts` están en el contrato de la Iteración 1. `frontend/src/lib/token.ts` pide el token de un usuario de servicio fijo (variables de entorno) y alimenta solo el listado de conductores.

## Decisiones tomadas

| # | Decisión | Motivo |
|---|---|---|
| D1 | Las pantallas viven en `frontend/`. No existe `app-conductor/`. | `frontend/` ya tiene CI, tests y el stack justificado. |
| D2 | **Sesión del conductor en el servidor de Next.** El formulario de login llama a un route handler propio. Ese handler pide el token a Keycloak (realm `m3`, cliente `m3-api`, flujo de contraseña) y lo guarda en una cookie `httpOnly`, `SameSite=Lax` y `Secure` fuera de desarrollo. | `m3-api` es un cliente confidencial: su secreto no puede llegar al navegador. |
| D3 | **`id_conductor` sale del claim `id_conductor` del token**, que se decodifica en el servidor (la firma la valida la API). No se agrega un endpoint. | Lo define el contrato (`bearerAuth`) y el realm ya lo mapea para `conductor.m3`. |
| D4 | **Las llamadas a M3 se hacen desde el servidor de Next** (route handlers). El navegador solo llama a esos handlers. El simulador de ubicación también pasa por ellos. | El token nunca queda en código de navegador. |
| D5 | `token.ts` (usuario de servicio) se mantiene solo para el listado de conductores de operador y servicio. Las pantallas del conductor no lo usan. | El rol `conductor` no puede listar conductores. |
| D6 | **«Pasajero subió»** es un estado local de la pantalla (no hay endpoint). **«Finalizar viaje»** es `PATCH …/estado` con `DISPONIBLE`. | Lo que permite el contrato. Falta acordar el cierre del viaje con M4 y M6. |
| D7 | `hora_rta` la genera el servidor de Next con la hora actual al responder una solicitud. | El contrato la exige en `RespuestaSolicitudRequest`. |
| D8 | Se muestra una cuenta regresiva con `vence_en` y se deshabilitan los botones al vencer. | Evita el 410 evitable. |

## Contrato que consume el frontend

| Operación | Uso | Notas |
|---|---|---|
| Keycloak (realm `m3`) | Login | No es un endpoint de M3. |
| `GET /conductores` | Listado de operador y servicio | El conductor recibe 403. |
| `GET /conductores/{id}/estado` | Estado actual | `EstadoConductor`: `estado`, `id_vehiculo_activo`, `actualizado`. |
| `PATCH /conductores/{id}/estado` | Ponerse en línea, finalizar, enviar ubicación | Al menos un campo; `latitud` y `longitud` juntas; `estado` solo `DESCONECTADO`, `CONECTADO` o `DISPONIBLE`. 422 `CONDUCTOR_NO_HABILITADO`. |
| `GET /conductores/{id}/ubicacion` | Mostrar la última ubicación | Los tres campos en `null` = desconocida. |
| `GET /conductores/{id}/solicitudes` | Pedidos | Filtro opcional `estado`. |
| `POST /solicitudes/{id}` | Aceptar o rechazar | Cuerpo `{respuesta, hora_rta}`. 409 y 410. Al aceptar, el conductor pasa a `OCUPADO`. |

## Estructura y dueños de archivos

Dos personas se reparten stacks completos, sin tocar los mismos archivos.

| Stack | Contenido | Archivos |
|---|---|---|
| **A · Datos y mocks** | Tipos, cliente de API, sesión, mocks, simulador | `frontend/src/lib/`, `frontend/src/mocks/`, `frontend/src/app/api/` |
| **B · Interfaz** | Diseño, estilos, navegación, estados de pantalla, componentes | `frontend/src/components/`, `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx` |
| **Pantallas** | Una PR por pantalla, apilada sobre A y B | `frontend/src/app/{login,estado,solicitudes,viaje}/` |

`frontend/src/app/page.tsx` y `ListadoConductores` los toca el stack A (mocks) primero y el stack B (badges) después.

## Reglas de trabajo

- Todo entra por PR contra `dev`. Nadie pushea a `main` ni a `dev`.
- PRs chicas, de pocos cientos de líneas. Antes de cada commit, revisar con `git diff --cached --stat`.
- **Stack de PRs**: se apila lo que depende de lo anterior. La primera rama sale de `dev` y apunta a `dev`; las siguientes salen de la anterior y apuntan a ella.
- Commits y PRs en español, con formato convencional (`feat:`, `test:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- Sin archivos generados, sin dependencias sin uso y sin secretos. Las credenciales van en `.env`, que no se commitea.
- Antes de empezar una tarea, avisar y marcarla en la issue de seguimiento para no duplicar trabajo.

## Orden de las PRs

1. **Stack A**: T704 a T706 (tipos y cliente), T711 y T712 (sesión), T713 a T718 (mocks y `USE_MOCK`).
2. **Stack B**: T701 a T703 (diseño y estilos), T707 a T710 (estados y navegación), T719 y T720 (badges, después de T704).
3. **Pantallas** US1 a US5 (T721 a T730): una PR por pantalla, una vez mergeados los cimientos.
4. **Calidad** (T731 y T732).
5. **Integración con la API real** (T733 en adelante): **bloqueada**, ver abajo.

## Diseño con Stitch o Figma

- Se usa para bocetar y acordar el aspecto antes de escribir los componentes.
- No se copia el código generado: se toman los valores (colores, espaciados) y los componentes se escriben a mano con TDD.
- Cada diseño muestra los tres estados: carga, error y vacío.
- Los tests verifican comportamiento; el aspecto se revisa a ojo contra el diseño en el recorrido manual.

## Bloqueos y dependencias externas

**Bloqueado hasta que el backend lo publique en `dev`**: `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. Hoy `backend/` no tiene código de estas operaciones; están planificadas en `specs/iteracion2-backend/`.

Afecta a la fase de integración (T733 a T740). No frena el resto: las pantallas se desarrollan y prueban con mocks.

Otras dependencias:

- Cerrar con M4 y M6 cómo termina un viaje (D6).
- Compose y seed de `infra/` con un usuario conductor y solicitudes de ejemplo (Datos y seguridad).

## Riesgos

- Si el backend cambia el contrato, los tipos y los mocks se desactualizan. Se mitiga validando contra `openapi.yaml` en T704 y repitiéndolo al integrar.
- Dos personas en `page.tsx` y `ListadoConductores`: se resuelve con el orden de PRs de arriba.

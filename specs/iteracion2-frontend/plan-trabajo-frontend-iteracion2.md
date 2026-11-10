# Plan de trabajo de Frontend — Iteración 2

**Grupo 15 · Desarrollo de Software · Módulo M3 (Conductores y Vehículos) · Equipo de Frontend**

Documento de trabajo para repartir y ordenar las tareas de la Iteración 2. Todo lo marcado como propuesta se puede cambiar si el equipo o el líder deciden otra cosa.

## 1. Objetivo

Según la diapositiva «De mocks a la API real» (Iteración 2 · Módulo 3):

- **Libertad de diseño:** el equipo decide la cara del módulo.
- **Dos fases:** primero con datos mock, sin depender del backend; después con la API real.
- **Cómo sabemos que terminó:** pantallas navegables, estados de carga, error y vacío, y consumo real del contrato.

Funcionalidades que indicaron los profesores para la app del conductor:

- Iniciar sesión.
- Ponerse en línea (disponible para trabajar).
- Recibir pedidos y aceptarlos o rechazarlos.
- Confirmar cuando sube el pasajero.
- Finalizar el viaje.
- Enviar la ubicación simulada al M4 durante el viaje. No se muestra mapa.

## 2. Punto de partida

- El frontend oficial vive en `frontend/` (Next.js 16.4, React 19.3, TypeScript 5.9, Vitest y ESLint). En la Iteración 1 se hizo una sola pantalla con el listado de conductores.
- La issue **#23** cubre los mocks (M-01, M-02), las badges (T246, T247), la integración con la API real (T242 a T245 y T249) y la calidad (T248). No cubre las pantallas del conductor ni el estado de carga.
- Las PRs anteriores se dieron de baja para rehacerlas en formato stack.
- `frontend/src/lib/tipos.ts` quedó desactualizado respecto del contrato (ver sección 3).

## 3. Qué dice el contrato

Se revisó `docs/contract/openapi.yaml` versión **1.2.0** (rama `main`). Ya incluye Disponibilidad y Solicitudes:

- **Iniciar sesión:** Keycloak (realm `m3`, rol `conductor`). No es un endpoint de M3.
- **Ponerse en línea:** `PATCH /conductores/{id}/estado` con `CONECTADO`, `DISPONIBLE` o `DESCONECTADO`. `OCUPADO` no se puede pedir.
- **Ver pedidos:** `GET /conductores/{id}/solicitudes`, con filtro opcional `estado`.
- **Aceptar o rechazar:** `POST /solicitudes/{id}`. Responde 410 si la oferta venció y, al aceptar, el conductor pasa a `OCUPADO`.
- **Finalizar viaje:** `PATCH` del estado a `DISPONIBLE`, que lo libera. Falta acordarlo con M4 y M6.
- **Ubicación:** `PATCH` del estado con `latitud` y `longitud`; M4 la lee con `GET .../ubicacion`.
- **Pasajero subió:** no hay endpoint propio.

Cambios que afectan al código actual:

- El conductor ahora tiene `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) en lugar de `conectado` y `disponible`.
- Se suman `id_vehiculo_activo`, `puntaje_promedio` y `cantidad_calificaciones`.
- No se leyeron los schemas completos de `Solicitud`, `EstadoConductorRequest` y `RespuestaSolicitudRequest`. Hay que revisarlos en F-01 antes de escribir tipos y tests.

## 4. Decisiones pendientes (Fase 0)

- **Dónde viven las pantallas:** en `frontend/` o en `app-conductor/`. Propuesta: `frontend/`, que ya tiene CI, tests y el stack justificado. Si `app-conductor/` se mantiene, hay que documentar el motivo en `specs/` y pedir que el CI lo cubra.
- **Cómo inicia sesión el conductor** y de dónde sale su `id_conductor`.
- **Qué hacer con «pasajero subió» y «finalizar viaje»**, que no tienen endpoint propio.
- **Estilos:** instalar Tailwind (hoy los componentes usan clases tipo Tailwind pero no está instalado) o usar CSS Modules. Si se agrega una dependencia, avisar al líder.

## 5. Reglas de trabajo

- Nadie pushea a `main` ni a `dev`: todo entra por PR.
- PRs chicas, de pocos cientos de líneas. Antes de cada commit, revisar con `git diff --cached --stat`.
- Un solo gestor de paquetes (`npm`) y un solo lockfile. No se suben archivos generados ni dependencias sin uso.
- **Stack de PRs:** se apila lo que depende de lo anterior. La primera rama sale de `dev` y apunta a `dev`; las siguientes salen de la anterior y apuntan a ella.
- Commits y PRs en español, con formato convencional (`feat:`, `test:`, `fix:`, `docs:`, `chore:`, `refactor:`).
- **TDD:** el test va primero y no se modifica para hacerlo pasar. Test y código van en la misma PR para que el CI pase.
- Cero secretos en el repo. Las credenciales van en `.env`, que no se commitea.
- Antes de empezar una tarea, avisar y marcarla en la issue para no duplicar trabajo.

## 6. Lista de tareas

Incluye las tareas originales de la issue **#23** (M-01, M-02, T242 a T249) y las nuevas (F-xx). Cada `[Impl]` va después de su `[Test]`. `[P]` indica que se puede hacer en paralelo. La numeración F-xx es provisoria.

### Fase 0: Decisiones previas (sin código)

- **F-00 [Manual]** Acordar con el líder y dejar escrito en `specs/iteracion2/` los puntos de la sección 4.
- **F-00b [Manual]** Diseñar las pantallas (login, estado, pedidos, viaje en curso y ubicación) en Stitch o Figma. Guardar los enlaces y una captura por pantalla.
- **F-00c [Manual]** Sacar del diseño los valores base: colores, tipografías, espaciados y radios de borde.
- **F-00d [Armado]** Pasar esos valores al código como variables en `frontend/src/app/globals.css` (o la configuración de Tailwind, si se aprueba).

### Fase 1: Cimientos (bloquean lo demás)

- **F-01 [Armado]** Actualizar `frontend/src/lib/tipos.ts` al contrato v1.2.0: estado operativo en lugar de `conectado` y `disponible`, más `id_vehiculo_activo`, `puntaje_promedio` y `cantidad_calificaciones`; agregar los tipos de estado, ubicación y solicitud. Ajustar mocks y tests existentes.
- **F-02 [Test]** `frontend/src/lib/api.test.ts`: `obtenerEstado`, `actualizarEstado` (PATCH con estado y ubicación opcional), `listarSolicitudes` (filtro `estado`), `responderSolicitud` y `obtenerUbicacion` envían `Authorization: Bearer`, usan el método y la URL del contrato y lanzan `ErrorApi` con `{codigo, mensaje}` ante 401, 403, 404, 409, 410 y 422.
- **F-03 [Impl]** `frontend/src/lib/api.ts` hasta que pase F-02.
- **F-04 [Test] [P]** `frontend/src/components/estados/estados.test.tsx`: `EstadoCarga`, `EstadoError` (con `role=alert`) y `EstadoVacio` muestran su mensaje.
- **F-05 [Impl]** `frontend/src/components/estados/` hasta que pase F-04.
- **F-06 [Test] [P]** `frontend/src/components/Navegacion.test.tsx`: hay un enlace a cada pantalla y se marca la activa.
- **F-07 [Impl]** `frontend/src/components/Navegacion.tsx` y `frontend/src/app/layout.tsx` hasta que pase F-06.

### Fase 2: Modo mock (desarrollo sin backend)

- **M-01 [Mock]** Crear `frontend/src/mocks/conductores.mock.ts` con datos variados según el contrato (estados APROBADA, PENDIENTE y RECHAZADA, con y sin ubicación). Test primero: `conductores.mock.test.ts`.
- **M-02 [Env]** Agregar soporte para `USE_MOCK=true` en `frontend/.env.example` y en `frontend/src/app/page.tsx` para alternar entre mock y API real. Test primero en `page.test.tsx`. Va apilada sobre M-01.
- **F-08 [Test] [P]** `frontend/src/mocks/conductor.mock.test.ts`: conductor en cada estado operativo; solicitudes en PENDIENTE, ACEPTADO, RECHAZADO y VENCIDA; ubicación con valor y con los tres campos en null.
- **F-09 [Mock]** `frontend/src/mocks/conductor.mock.ts` hasta que pase F-08, respetando `USE_MOCK`.

### Fase 3: UI y experiencia de usuario

- **T246 [Test]** Agregar test en `frontend/src/components/ListadoConductores.test.tsx` que verifique el renderizado de badges/colores por estado (APROBADA, PENDIENTE, OBSERVADA, SUSPENDIDA, RECHAZADA).
- **T247 [Impl]** Modificar `frontend/src/components/ListadoConductores.tsx` para mostrar badges con colores diferenciados según el estado (verde, amarillo, rojo). Va en la misma PR que T246.

### Fase 4: Pantallas del conductor (cada una con mock primero)

Cada pantalla se implementa según su diseño de F-00b.

#### US1 · Iniciar sesión

- **F-10 [Test]** `FormularioLogin.test.tsx` y `app/login/page.test.tsx`: campos usuario y contraseña, mensaje ante credenciales inválidas, redirección al autenticarse, y las credenciales se procesan en el servidor, nunca en el navegador.
- **F-11 [Impl]** `FormularioLogin.tsx` y `app/login/page.tsx` hasta que pase F-10.

#### US2 · Ponerse en línea

- **F-12 [Test]** `ControlEstado.test.tsx`: botones para DESCONECTADO, CONECTADO y DISPONIBLE; no ofrece OCUPADO; muestra el error `CONDUCTOR_NO_HABILITADO` (422); estados de carga y error.
- **F-13 [Impl]** `ControlEstado.tsx` y `app/estado/page.tsx` hasta que pase F-12.

#### US3 · Pedidos entrantes

- **F-14 [Test]** `ListadoSolicitudes.test.tsx`: aceptar y rechazar solo en PENDIENTE; vacío «No hay solicitudes»; 410 muestra «oferta vencida»; 409 muestra el conflicto; carga y error.
- **F-15 [Impl]** `ListadoSolicitudes.tsx` y `app/solicitudes/page.tsx` hasta que pase F-14.

#### US4 · Viaje en curso

- **F-16 [Test]** `ViajeEnCurso.test.tsx`: tras aceptar se muestra el viaje; «Pasajero subió» cambia el paso mostrado; «Finalizar viaje» pide DISPONIBLE y vuelve a las solicitudes.
- **F-17 [Impl]** `ViajeEnCurso.tsx` y `app/viaje/page.tsx` hasta que pase F-16.

#### US5 · Ubicación simulada

- **F-18 [Test]** `lib/simuladorUbicacion.test.ts` (timers falsos de Vitest): genera puntos de un recorrido, envía latitud y longitud juntas cada N segundos mientras está OCUPADO y se detiene al terminar.
- **F-19 [Impl]** `simuladorUbicacion.ts` y `UbicacionActual.tsx`: muestra la última coordenada y su fecha; ubicación null se muestra como «desconocida», nunca como (0, 0). Sin mapa.

### Fase 5: Integración con la API real

- **T242 [Config]** Configurar `frontend/.env.local` con `USE_MOCK=false` y las variables de Keycloak/API.
- **T243 [Infra]** Levantar el stack local con Docker Compose en `infra/` y verificar salud en `http://localhost:8080/salud`.
- **T244 [Auth]** Validar obtención de token desde Keycloak con usuario de prueba.
- **T245 [API]** Probar llamada `GET /api/v1/conductores` y validar formato de respuesta.
- **T249 [Manual]** Verificar en navegador (`npm run dev`) con datos reales del seed, manejo de lista vacía y manejo de errores.
- **F-20 [Manual]** Con el Compose y el seed, recorrer login, disponible, pedido, aceptar y finalizar con `USE_MOCK=false`. Verificar carga, error y vacío en cada pantalla y anotar las diferencias con el contrato.

### Fase 6: Calidad

- **T248 [Build]** Validar que pasen en verde: `npm run test`, `npm run lint` y `npm run build`.
- **F-21 [Armado]** `frontend/README.md`: cómo correr en modo mock y en modo real, y el recorrido de pantallas.

## 7. Orden y reparto propuesto

- **Stack de datos:** F-01, después F-02 y F-03, después F-08 y F-09. M-01 y M-02 van en su propio stack (M-02 sobre M-01).
- **Stack de interfaz:** F-04 y F-05, después F-06 y F-07, después F-00d.
- **T246 y T247:** una sola PR desde `dev`, después de F-01.
- **Pantallas (US1 a US5):** una PR por pantalla, una vez mergeados los cimientos o apiladas sobre ellos.
- **Fase 5:** necesita el backend levantado en `dev` y las decisiones de F-00.
- **Reparto:** cada persona se hace cargo de un stack completo, sin tocar los mismos archivos que la otra. Anotar en la issue quién toma cuál.

## 8. Diseño con Stitch o Figma

- Se usa para bocetar y acordar el aspecto de las pantallas antes de escribir los componentes.
- Se exporta a Figma o a imágenes. No se copia en el repositorio el código generado: se toman como referencia los valores (colores, espaciados) y los componentes se escriben a mano con TDD.
- Los tests verifican comportamiento; el aspecto se revisa a ojo contra el diseño en F-20 y T249.
- Cada diseño tiene que mostrar los tres estados: carga, error y vacío.

## 9. Pendientes de confirmar

- La numeración F-xx, las rutas y los nombres de archivo son propuestas.
- Los schemas completos de `Solicitud`, `EstadoConductorRequest` y `RespuestaSolicitudRequest` se revisan en F-01.

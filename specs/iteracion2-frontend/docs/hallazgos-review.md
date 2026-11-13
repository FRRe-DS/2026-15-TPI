# Review r2 (code-reviewer): Changes Requested

Head revisado: `68be2cd13990d1ecab093e08dbec3c781711acd6` (`origin/dev`) contra `fee80b0431fe0ace1e81f63e9c6085819798b85a` (`origin/main`) para el release. Cada PR se revisó además contra su base histórica completa. Archivos y líneas del diff integrado. Fecha: 13/11/2026.

Tres agentes `code-reviewer` revisaron las PRs completas, sus cuerpos, documentación del repositorio y callers pertinentes.

| PRs | Alcance | Estado |
|---|---|---|
| #93, #94, #95 | Tipos/cliente, estados/navegación y listado mock | Integradas |
| #97 | Mocks del conductor | Cerrada sin merge; reemplazada por #98 |
| #98 | Mocks del conductor | Integrada |
| #99 | Sesión del conductor | Cerrada sin merge; reemplazada por #100 |
| #100, #101, #102 | Sesión, prototipo/estilos y login | Integradas |
| #103, #104, #105, #106 | Solicitudes, ubicación, estado y viaje | Integradas |
| #107, #108 | Badges y documentación/calidad | Integradas |

#92 es un revert de testing; no existe una PR #96. Las alternativas cerradas se distinguieron del código integrado. No se encontraron hallazgos independientes en #93, #95, #100 y #107 dentro del alcance.

## Limitaciones del review

- Se excluyeron las integraciones con backend, Keycloak y BBDD.
- No se ejecutó un recorrido en navegador.
- Validación nueva de esta ronda: 24 archivos y 181 tests aprobados, ESLint sin errores y build de Next.js aprobado, incluido TypeScript.
- Se usaron los entrypoints locales de Vitest, ESLint y Next con Node del runtime de Codex: el shim de npm del entorno no encuentra su versión configurada.
- Las reproducciones específicas se identifican en la confianza de cada hallazgo. No se reutilizaron ejecuciones de la ronda anterior como evidencia nueva.
- Los reviewers no editaron código. El cambio de preparación del release se limita a documentación y conciliación de tareas; estos hallazgos funcionales siguen abiertos.

## Hallazgos de la ronda anterior

F1–F8 siguen presentes, al igual que el desborde menor del prototipo. Se verificaron nuevamente por lectura. En esta ronda se agregó el bloqueo del modo mock por el proxy, confirmado por ejecución. Los IDs COR de abajo son los de seguimiento de esta ronda; los antiguos F1–F8 son antecedentes.

## Security

**Sin hallazgos de seguridad** dentro del alcance revisado.

Se revisaron renderizado de datos y mensajes, exposición de credenciales, atributos de cookies, entradas de coordenadas y guardas locales. La validación externa de identidad, permisos y consultas a servicios quedó excluida.

## Performance

**Sin hallazgos.** Se revisaron recorridos de colecciones, renderizado, temporizadores, limpieza de intervalos y programación de envíos. No se detectaron costes no acotados ni recursos locales sin liberar que justifiquen un hallazgo independiente.

## Correctness

- `frontend/src/proxy.ts:6` 🟡 — **COR-1: el proxy bloquea el modo mock (#102).**
  - Cómo falla: con `USE_MOCK=true` y sin cookie, `/estado`, `/solicitudes` y `/viaje` redirigen a `/login` antes de ejecutar sus ramas mock.
  - Confianza: confirmado por ejecución nueva del proxy real con `NextRequest`: las tres rutas devolvieron `307` hacia `/login`. Los helpers tampoco contemplan el modo mock.
  - Fix: permitir el recorrido mock sin sesión en desarrollo/pruebas mediante una política compartida; conservar la protección del modo real y probar ambas configuraciones.

- `frontend/src/components/Navegacion.tsx:13` 🟡 — **COR-2: enlace a una pantalla inexistente (#94; anterior F1).**
  - Cómo falla: «Ubicación» lleva a `/ubicacion`, pero solo existe el handler `/api/ubicacion`; la pantalla termina en 404.
  - Confianza: confirmado por lectura y manifiesto del build.
  - Fix: implementar la pantalla o retirar el enlace hasta disponer de ella; verificar los destinos de navegación.

- `frontend/src/mocks/conductor.mock.ts:57` 🟡 — **COR-3: la única oferta pendiente del mock ya venció (#98; anterior F2).**
  - Cómo falla: el vencimiento fijo `2026-11-12T20:30:00Z` deja deshabilitados aceptar y rechazar desde antes del merge.
  - Confianza: confirmado por lectura y cálculo ejecutado del vencimiento para el 13/11/2026: cero segundos restantes.
  - Fix: generar una oferta pendiente con reloj inyectable y vencimiento relativo al inicio del escenario; mantener otra vencida y probar ambos estados.

- `frontend/src/components/ListadoSolicitudes.tsx:116` 🟡 — **COR-4: aceptar no abre el viaje (#103; anterior F3).**
  - Cómo falla: una aceptación exitosa actualiza la tarjeta, pero el usuario permanece en `/solicitudes`. No hay navegación ni callback de aceptación en el componente o su página.
  - Confianza: confirmado por lectura del handler y sus callers.
  - Fix: navegar a `/viaje` tras aceptar, identificando la solicitud activa, y probar esa transición.

- `frontend/src/app/solicitudes/page.tsx:36` 🟡 — **COR-5: la respuesta mock no se conserva (#103; anterior F8).**
  - Cómo falla: responder devuelve una copia; al salir y volver, la oferta continúa pendiente. El viaje selecciona otra solicitud aceptada del fixture. Con reloj previo al vencimiento se observa el mismo problema; es independiente de COR-3.
  - Confianza: confirmado por lectura; el cambio solo se guarda en el estado local del componente.
  - Fix: guardar respuesta, estado operativo y solicitud activa en un estado mock compartido entre pantallas; al aceptar, pasar el conductor a `OCUPADO`.

- `frontend/src/lib/simuladorUbicacion.ts:61` 🟡 — **COR-6: la ubicación no se ejecuta durante el viaje (#104; documentación #108; anterior F4).**
  - Cómo falla: ninguna pantalla inicia el simulador ni monta `UbicacionActual`, aunque `frontend/README.md:100` describe envíos periódicos durante el viaje.
  - Confianza: confirmado por lectura y búsqueda completa de callers; los consumidores están en tests.
  - Fix: conectar simulador y vista al recorrido, detenerlo al finalizar/desmontar y ajustar la documentación al comportamiento entregado.

- `frontend/src/app/viaje/page.tsx:22` 🟡 — **COR-7: finalizar el viaje mock no cierra el escenario (#106; anterior F5).**
  - Cómo falla: solo cambia la fecha de una plantilla; al regresar reaparece el viaje 5521 y el estado activo del conductor no cambia.
  - Confianza: confirmado por lectura de las acciones, selección de solicitud y estados entre páginas.
  - Fix: limpiar el viaje activo y guardar `DISPONIBLE` en el estado mock compartido; probar finalizar y volver a ambas pantallas.

- `frontend/src/components/ListadoSolicitudes.tsx:108` 🟡 — **COR-8: el bloqueo permite respuestas duplicadas (#103; anterior F6).**
  - Cómo falla: iniciar A y luego B reemplaza el único ID de carga y rehabilita A mientras su primera respuesta sigue pendiente. Cualquier `finally` limpia además el bloqueo de la otra operación.
  - Confianza: confirmado por lectura del estado, botones y ausencia de guarda en el handler.
  - Fix: mantener un conjunto de IDs en vuelo o bloquear todas las respuestas mientras haya una pendiente; probar A → B → A con promesas controladas.

- `frontend/src/app/solicitudes/page.tsx:61` y `frontend/src/app/estado/page.tsx:51` 🟡 — **COR-9: los errores pierden sus campos al cruzar Server Actions (#103/#105/#106; anterior F7).**
  - Cómo falla: los componentes esperan `instanceof ErrorApi`, `status` y `codigo`, pero React reconstruye un error genérico y en producción oculta el mensaje. Los mensajes específicos de conflicto, oferta vencida o habilitación no funcionan como en los tests de callbacks directos.
  - Confianza: confirmado por lectura de acciones, consumidores y transporte del runtime instalado: `react-server-dom-webpack-server.node.production.js:2006` serializa `{digest}` y `react-server-dom-webpack-client.browser.production.js:1701` reconstruye un `Error`. No requiere servicios externos.
  - Fix: devolver errores esperados como resultados serializables con `status`, `codigo` y `mensaje`; reservar excepciones para errores inesperados.

- `frontend/src/app/diseno/diseno.module.css:229` 🔵 — **COR-10: el prototipo desborda pantallas angostas (#101).**
  - Cómo falla: a 375 px, el padding deja 327 px disponibles, pero la grilla exige columnas mínimas de 360 px.
  - Confianza: confirmado por lectura y cálculo; no medido en navegador.
  - Fix: usar `repeat(auto-fit, minmax(min(100%, 360px), 1fr))` y verificar a 320 y 375 px.

Todos los hallazgos se introdujeron en las PRs indicadas. No se atribuyen a sus diffs problemas preexistentes de otras PRs ni se duplican entre agentes.

## Maintainability

**Sin hallazgos independientes.** Se revisaron nombres, componentes compartidos, tipos, estado mock, callers y pruebas. Las carencias de pruebas y documentación asociadas a los fallos anteriores se incluyen en sus fixes para no duplicarlas.

## Sumario y Veredicto

- Veredicto: **Changes Requested**, por fallos locales que interrumpen el recorrido del conductor.
- Sumario: se revisaron las PRs completas con tres agentes. Hay **0 🔴, 9 🟡 y 1 🔵**. Los tests, lint y build pasan, pero no cubren los recorridos señalados. Para aprobar deben corregirse los importantes o quedar explícitamente decididos y delimitados en el alcance del release.

El usuario decidió preparar el release corrigiendo únicamente README y conciliación de tareas. Los hallazgos quedan registrados como pendientes; no se aplican correcciones funcionales ni se cierra T733–T740 con esta entrega.

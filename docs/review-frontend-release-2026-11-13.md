# Revisión de frontend previa al release — 13/11/2026

Base auditada: `origin/dev`, commit `68be2cd13990d1ecab093e08dbec3c781711acd6`.
Comparación de release: `origin/main...origin/dev`. Tres agentes `code-reviewer`
revisaron los diffs completos de las PRs de frontend y el estado integrado,
aplicando la skill `code-review-excellence` y sus guías pertinentes.

## Alcance

Se revisó lógica local, componentes, navegación, mocks, temporizadores, pruebas
y documentación del frontend. Se excluyeron interoperabilidad y validaciones
contra backend, Keycloak y base de datos. No se ejecutó un recorrido en navegador.
Los hallazgos funcionales se informan; este cambio solo corrige documentación
y seguimiento de tareas.

| PRs | Contenido | Estado en el alcance auditado |
|---|---|---|
| #93 | Tipos y cliente | Integrada |
| #94 | Estados y navegación | Integrada |
| #95 | Listado mock y selector de modo | Integrada |
| #97 | Mocks del conductor | Cerrada sin merge; reemplazada por #98 |
| #98 | Mocks del conductor | Integrada |
| #99 | Sesión del conductor | Cerrada sin merge; reemplazada por #100 |
| #100 | Sesión del conductor | Integrada |
| #101 | Prototipo y estilos | Integrada |
| #102 | Pantalla de login | Integrada |
| #103 | Solicitudes | Integrada |
| #104 | Utilidades y componentes de ubicación | Integrada |
| #105 | Control de estado | Integrada |
| #106 | Viaje en curso | Integrada |
| #107 | Badges de habilitación | Integrada |
| #108 | Calidad y README | Integrada |

#92 revierte cambios de testing y no es una PR de frontend. No existe una PR #96.
Las PRs cerradas sin merge se revisaron como antecedentes, sin atribuir sus
diferencias al código entregado. No hubo hallazgos independientes en #93, #95,
#100, #102 y #107 dentro del alcance indicado.

## Hallazgos funcionales

Todos los números de línea siguientes corresponden al commit auditado.

### F1 — P2: enlace a una pantalla inexistente (#94)

`frontend/src/components/Navegacion.tsx:13` ofrece `/ubicacion`, pero no existe
`app/ubicacion/page.tsx`. El build solo registra `/api/ubicacion`, que es un
handler y no una pantalla. Pulsar el enlace termina en 404.

Corrección sugerida: implementar la pantalla o retirar el enlace hasta que exista,
y verificar que los destinos de navegación tengan una ruta implementada.

### F2 — P2: la oferta pendiente del mock ya está vencida (#98)

`frontend/src/mocks/conductor.mock.ts:57` fija el vencimiento de la única oferta
pendiente en `2026-11-12T20:30:00Z`, anterior incluso al merge de la PR.
`ListadoSolicitudes` deshabilita aceptar y rechazar al llegar a cero. El escenario
mock entregado no permite recorrer esas acciones.

Corrección sugerida: construir el escenario con un reloj inyectable y una oferta
que venza respecto del inicio del recorrido; mantener otra oferta vencida.

### F3 — P2: aceptar no abre el viaje (#103)

`frontend/src/components/ListadoSolicitudes.tsx:115` guarda la respuesta en estado
local, pero no navega ni avisa a un contenedor para abrir `/viaje`. La página
`app/solicitudes/page.tsx` tampoco hace esa transición. Aun con una respuesta
exitosa simulada, el usuario permanece en la lista.

Corrección sugerida: navegar al viaje tras una aceptación exitosa y cubrir esa
transición con un callback simulado, sin servicios externos.

### F4 — P2: ubicación implementada de forma aislada (#104, documentación #108)

`frontend/src/lib/simuladorUbicacion.ts:61` define el simulador y
`frontend/src/components/UbicacionActual.tsx` define la vista, pero ninguno tiene
un caller productivo. No hay una pantalla que arranque/detenga el temporizador o
muestre esa vista. La afirmación del README de frontend de que se envían puntos
cada cinco segundos durante el viaje excede lo implementado.

Corrección sugerida: conectar el ciclo del simulador y la vista al recorrido
local, con limpieza al finalizar o desmontar, o documentar la entrega como
utilidades aisladas hasta completar esa conexión.

### F5 — P2: finalizar el viaje mock no cierra el escenario (#106)

`frontend/src/app/viaje/page.tsx:19` solo cambia el timestamp de la plantilla
`MOCK_ESTADOS_CONDUCTOR.DISPONIBLE`; no cambia el estado activo usado por
`/estado` ni la solicitud aceptada. La misma página vuelve a seleccionar siempre
la solicitud aceptada del fixture. Tras finalizar y volver a `/viaje`, reaparece
el viaje anterior.

Corrección sugerida: usar un estado mock común al recorrido, registrar su viaje
activo y limpiarlo al finalizar. Probar aceptar, finalizar y volver a abrir.

La ejecución del código transpileado en memoria confirmó que se muestra el viaje
5521 antes y después de finalizar y que el estado activo continúa `CONECTADO`.

### F6 — P2: un único ID de carga permite respuestas duplicadas (#103)

`frontend/src/components/ListadoSolicitudes.tsx:108`, `:127` y `:138` usan un único
`respondiendo`. Si se responde A y luego B antes de resolver A, el ID pasa a B y
rehabilita A. Al resolver cualquiera, se limpia también el bloqueo de la otra.
El componente puede emitir respuestas repetidas mientras siguen en vuelo.

Corrección sugerida: bloquear toda respuesta mientras haya una en curso o mantener
un conjunto de IDs pendientes con una guarda contra duplicados. Probar dos ofertas
vigentes con promesas controladas.

El componente ejecutado con promesas pendientes produjo llamadas `[1, 2, 1]`:
el botón de A estaba bloqueado tras iniciar A y se rehabilitó al iniciar B.

### F7 — P2: errores de acciones de servidor tratados como instancias locales (#103, #105, #106)

`frontend/src/app/solicitudes/page.tsx` y `app/estado/page.tsx` propagan excepciones
desde funciones `use server`; los componentes comprueban `instanceof ErrorApi`
para mostrar códigos y mensajes específicos. El transporte React de Server Actions
no conserva esa instancia ni sus campos y oculta el mensaje de excepciones en
producción. Los tests llaman callbacks en memoria y no cubren ese límite interno
del frontend. Esto puede verificarse con una acción que arroje un error simulado,
sin conectar servicios externos.

Corrección sugerida: devolver resultados serializables para errores esperados,
por ejemplo una unión de éxito/error con `status`, `codigo` y `mensaje`, y renderizar
esos datos. Reservar las excepciones para errores inesperados.

### F8 — P2: responder una oferta mock no conserva el cambio (#103)

`frontend/src/app/solicitudes/page.tsx:36` devuelve una copia de la solicitud sin
actualizar el escenario compartido. Al salir de la pantalla se pierde la respuesta;
al entrar al viaje se selecciona la oferta aceptada preexistente, no la que se acaba
de aceptar. Una ejecución en memoria confirmó `returned: ACEPTADO` frente a
`store: PENDIENTE`. Este fallo es independiente del vencimiento fijo de F2.

Corrección sugerida: persistir la respuesta en el estado mock del recorrido,
actualizar el conductor a `OCUPADO` al aceptar y registrar la solicitud activa.

## Observación menor

En `frontend/src/app/diseno/diseno.module.css:229` (#101), la grilla exige columnas
de 360 px y su contenedor tiene 48 px de padding horizontal. Un viewport de 375 px
solo deja 327 px. Se infiere desborde por las reglas CSS; no se midió en navegador.
Afecta al prototipo `/diseno`. Usar un mínimo adaptable al ancho disponible.

## Validación

- Suite completa local: **24 archivos, 181 tests aprobados**.
- ESLint: sin errores.
- Build de Next.js: aprobado, incluida comprobación TypeScript.
- `git diff --check`: aprobado para los ajustes documentales.
- Se ejecutaron los entrypoints locales de Vitest, ESLint y Next con Node del
  runtime de Codex: el shim de `npm` del PATH no encuentra su versión configurada.
- No se cambiaron tests ni código funcional para obtener estos resultados.

## Conciliación autorizada

- Cerrar T704–T706 (#93), T711–T712 (#100), T713–T716 (#95), T717–T718 (#98),
  con evidencia de implementación y pruebas aisladas; corregir las rutas de test
  de T705 y T715 para que coincidan con los archivos entregados.
- Cerrar Seguridad T523: su dependencia Testing T617 se integró en #91.
- Backend: su listado no tiene tareas abiertas; no se modificó.
- Mantener T733–T740 abiertas y corregir T734 para ejecutar Compose desde la raíz.
- Actualizar el README principal con pantallas, pruebas automáticas ya entregadas,
  umbral vigente, resultados fechados y cuenta de operador para el listado.
- T729–T730 acreditan utilidades y componentes aislados; no acreditan que el
  recorrido completo de ubicación esté conectado (F4).

## Dictamen

**Solicitar cambios funcionales en una entrega posterior o declarar estas
limitaciones al publicar.** El CI verde acredita las pruebas existentes, pero no
resuelve los casos anteriores. Por instrucción del usuario este cambio no corrige
esos comportamientos ni cierra la integración real. No se publicó el release
durante esta revisión; el informe se entrega antes de ese paso.

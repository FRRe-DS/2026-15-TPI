# Investigación: Iteración 2 — Backend de M3

Decisiones técnicas con su justificación. El stack y las versiones son los de la [Iteración 1](../iteracion1/research.md) y no cambian: no se agregan dependencias nuevas. Todo lo que sigue se resolvió a partir del [spec.md](./spec.md), del contrato `docs/contract/openapi.yaml` (1.2.0) y del código de `dev`.

## Decisiones de diseño

### 1. Una sola regla de concurrencia: bloqueo de fila del conductor

- **Decisión**: toda operación que cambia el estado de un conductor (`PATCH /estado` y aceptar una solicitud) abre una transacción y llama primero a `bloquear_conductor` (`SELECT ... FOR UPDATE`, ya existente). Las que además tocan una solicitud la bloquean después (`bloquear_solicitud`). Orden fijo de bloqueos: **conductor → solicitud**.
- **Motivo**: serializa los cambios del mismo conductor sin agregar columnas ni mecanismos nuevos, y evita bloqueos cruzados (deadlocks) porque todos toman los bloqueos en el mismo orden. Cubre "PATCH de estado contra aceptar una solicitud" (SC-011).
- **Para responder una solicitud**: como el conductor dueño se conoce recién al leer la solicitud, el caso de uso la lee sin bloqueo, bloquea al conductor, bloquea la solicitud y vuelve a validar su estado. Dos respuestas simultáneas quedan en fila: la primera gana y la segunda ve la solicitud ya respondida (`409`).
- **Alternativas**: bloqueo optimista con columna de versión (obliga a reintentos y a una columna más) y nivel de aislamiento serializable (más caro y con reintentos por fallas de serialización).

### 2. Idempotencia de la finalización de viaje *(retirada)*

- Se retiró con el contrato 1.2.0, que sacó `POST /integraciones/m6/.../finalizacion`. Ya no hay tabla `viaje_finalizado` ni idempotencia por `id_viaje`. El número se conserva para no cambiar las referencias.

### 3. Pedidos de M4 más viejos que el último cambio *(retirada)*

- Se retiró con el contrato 1.2.0, que sacó `PATCH /integraciones/m4/.../disponibilidad`. Ya no hay comparación de `actualizado` contra un pedido externo ni riesgo de reloj desfasado. `fecha_ultimo_cambio_estado` sigue existiendo solo para devolver `actualizado`.

### 4. Cálculo de `puntaje_promedio`

- **Decisión**: el conductor guarda `suma_puntajes` y `cantidad_calificaciones` (enteros). `puntaje_promedio = suma / cantidad`, calculado en el dominio con `Decimal`, redondeado a 2 decimales (mitad hacia arriba) y expuesto como número; `null` si la cantidad es 0.
- **Solo lectura**: ningún endpoint del contrato 1.2.0 escribe estos totales. Se leen y se calculan; el seed carga datos de ejemplo. De dónde vendrán en producción se define con M6 y M2.
- **Motivo**: no se guarda un promedio derivado que pueda quedar inconsistente, y los enteros no tienen errores de punto flotante.
- **Alternativas**: guardar el promedio (se desincroniza si alguien escribe los totales) y calcularlo desde una tabla de calificaciones (innecesario sin un endpoint que las cree).

### 5. Reglas del estado del conductor en un solo lugar del dominio

- **Decisión**: el conductor tiene un único campo `estado` con cuatro valores (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) que reemplaza a `conectado` y `disponible`. Un módulo `dominio/disponibilidad.py` concentra la regla "puede quedar `DISPONIBLE`" (conductor `APROBADA`, vehículo activo existente y `APROBADA`) y la función que aplica un cambio de estado. Lo usan `actualizar_estado_conductor` y `responder_solicitud`.
- **Quién asigna cada valor**: el conductor o el operador piden `DESCONECTADO`, `CONECTADO` o `DISPONIBLE` con `PATCH /estado`. `OCUPADO` lo asigna solo M3 al aceptar una solicitud y no se puede pedir (`400`). Ningún otro módulo escribe el estado: si M4 o M6 necesitan marcarlo, hay que acordar una operación de escritura con ellos.
- **Resultados** que comparten los dos casos de uso:

| Situación | Resultado |
|---|---|
| Pide `DISPONIBLE` y no cumple la regla | `ConductorNoHabilitado` (`422`) y no cambia nada |
| Pide `DISPONIBLE` estando `DESCONECTADO` o `OCUPADO` y cumple la regla | queda `DISPONIBLE` (conecta o libera) |
| Pide `DESCONECTADO` o `CONECTADO` | queda en ese estado, desde cualquier estado |
| Pide `OCUPADO` | `DatosInvalidos` (`400`) |
| Quita el vehículo activo (`null`) estando `DISPONIBLE` | pasa a `CONECTADO` |
| Cambia a un vehículo activo no `APROBADA` estando `DISPONIBLE` | pasa a `CONECTADO` |
| Vehículo activo inexistente o de otro conductor | `NoEncontrado` (`404`) |
| Acepta una solicitud y está `CONECTADO` o `DISPONIBLE`, `APROBADA` y con vehículo activo `APROBADA` | pasa a `OCUPADO` |
| Acepta una solicitud y está `DESCONECTADO`, `OCUPADO` o no cumple la regla | `ConductorNoHabilitado` (`422`) |
| Rechaza una solicitud | no cambia el estado |
| El pedido no cambia ningún valor | no cambia `actualizado` |

- **Motivo**: una regla escrita una sola vez evita que el `PATCH` y la aceptación de solicitudes se contradigan, y se prueba con tests unitarios sin base. Con un solo campo no existen combinaciones imposibles como "disponible pero desconectado".
- **Supuestos de este plan, a confirmar con el equipo**: pedir `DISPONIBLE` desde `DESCONECTADO` conecta y deja disponible en un paso; un conductor `OCUPADO` no puede aceptar otra solicitud.
- **`actualizado`**: cambia solo cuando cambia el estado o el vehículo activo; no cambia por actualizar solo la ubicación (FR-025).

### 6. Ubicación simulada fija

- **Decisión**: el caso de uso `actualizar_estado_conductor` recibe la coordenada simulada como dato inyectado. Si el conductor pasa de `DESCONECTADO` a otro estado, no tiene ubicación y el pedido no trae `latitud` y `longitud`, se le asigna esa coordenada con `fecha_act_ubic` igual a la hora del servidor. Después, las actualizaciones sin ubicación no la tocan.
- **Coordenada y configuración**: por defecto `-27.4511, -58.9867` (la del ejemplo del contrato). Se configura con `UBICACION_SIMULADA_LATITUD` y `UBICACION_SIMULADA_LONGITUD` en la configuración de la API, con ese valor por defecto. No son secretos.
- **Motivo**: la regla vive en la lógica (testeable con valores fijos) y el valor en la configuración (cambiable sin tocar el código). La coordenada nunca es `0,0`.
- **Alternativa**: leer la variable de entorno dentro del dominio (rompe el aislamiento de la capa).

### 7. Solicitud vencida

- **Decisión**: `Solicitud.estado_efectivo(ahora)` devuelve `VENCIDA` si el estado guardado es `PENDIENTE` y `ahora > vence_en`; si no, devuelve el estado guardado. `ahora` sale del puerto `Reloj` ya existente, de modo que los tests lo fijan. Responder hasta `vence_en` inclusive es válido.
- **Filtro del listado**: se aplica sobre el estado efectivo, en el caso de uso. El repositorio devuelve todas las solicitudes del conductor y el caso de uso las filtra. Una solicitud `PENDIENTE` ya vencida aparece como `VENCIDA` y no como `PENDIENTE`.
- **Motivo**: no hace falta un proceso que marque las vencidas y la regla queda en el dominio. El volumen por conductor es chico.
- **Alternativa**: filtrar en SQL con `ahora` como parámetro (más rápido con muchas filas, más difícil de probar; se retoma si el volumen crece).

### 8. Acceso por rol y acceso propio del conductor

- **Decisión**: una política pura `aplicacion/politicas/acceso.py` recibe los roles del token, el `id_conductor` del token, el del recurso y qué roles puede cada operación, y lanza `AccesoProhibido` o `SinPermisos`. La API la envuelve en dependencias de FastAPI reutilizables en `api/seguridad.py`.
- **Reglas**:
  - El identificador del conductor sale del claim `id_conductor` del token, nunca del cuerpo ni de la consulta (FR-040).
  - Un token de conductor sin `id_conductor` numérico recibe `403` en cualquier operación sobre un conductor. Igual que `id_operador`, un valor booleano no es válido.
  - La política se evalúa **antes** de buscar el recurso. Un conductor que pide el `id` de otro recibe `403` aunque ese conductor no exista, para que no pueda sondear qué ids existen.
  - Si el token trae varios roles se permite lo que permita cualquiera de ellos.
  - La matriz completa está en [contracts/token-jwt.md](./contracts/token-jwt.md).
- **Responder una solicitud**: la política necesita al conductor dueño, así que se evalúa después de leerla. Solicitud inexistente → `404`; solicitud de otro conductor, pedida por un conductor → `403` `ACCESO_PROHIBIDO`.
- **Motivo**: la regla pura se prueba sin servidor y las dependencias evitan repetir el chequeo en cada router.
- **Alternativa**: un middleware que revise la ruta (más difícil de ajustar por operación y de leer).

### 9. Cuándo un tipo de servicio queda habilitado

- **Decisión**: la columna `vehiculo_tipo_servicio.habilitado` se mantiene sincronizada con la habilitación del vehículo, dentro de la acción de habilitación que ya existe (misma transacción y mismo bloqueo): al **aprobar** un vehículo se habilitan todos sus tipos de servicio, y al **suspender** o **rechazar** se deshabilitan. Observar no los toca.
- **Motivo**: el contrato no tiene un endpoint para habilitar un tipo de servicio por separado, y el spec pide que `habilitado` deje de estar siempre en falso. Esta es la forma de cumplirlo sin agregar un endpoint fuera del contrato (constitución, principio IV).
- **Es un supuesto nuevo del plan** que no estaba en el spec: se agrega a sus *Supuestos* y hay que confirmarlo con el equipo. Si hace falta habilitar tipos de servicio de forma independiente, requiere un cambio de contrato.
- **Alternativa**: derivar `habilitado` al leer a partir de la habilitación del vehículo, sin tocar la columna (funciona hoy, pero la columna queda sin uso y confunde a quien lea la base).

### 10. Filtro `tipo_servicio` del listado

- **Decisión**: devuelve los conductores que tienen **al menos un vehículo** con ese tipo de servicio habilitado. Es la misma forma en que `tipo_vehiculo` filtra hoy (cualquier vehículo del conductor).
- **Motivo**: mantiene una sola semántica entre los dos filtros de vehículo. `latitud` y `longitud` siguen aceptándose y no filtran ni ordenan.
- **Alternativa**: usar solo el vehículo activo (más preciso para M4, pero distinta a `tipo_vehiculo` y deja afuera a los conductores sin vehículo activo marcado).

### 11. Un cambio de resolución del spec

- El spec dice, en la historia 5, que una solicitud "inexistente o de otro conductor" responde `404`, y en la historia 8 que responder la de otro conductor da `403`. Se resuelve así: **inexistente → `404`; ajena, para un conductor → `403`**. El operador puede responder cualquiera. Se corrigió el escenario de la historia 5.

### 12. Cobertura

- **Propuesta**: subir el umbral de `--cov-fail-under` de 65 a **70** una vez integradas las PRs de lógica. La lógica nueva es casi toda dominio y casos de uso con tests unitarios, donde la cobertura es alta y barata.
- **Quién lo aplica**: el cambio está en `.github/workflows/ci.yml`, que es del grupo de Testing; se les pide en la integración de planificaciones. Backend entrega cada PR sin bajar del umbral vigente.

### 13. Tamaño de las PRs

- **Regla**: cada PR toca una sola responsabilidad. Las estimaciones del plan quedan por debajo de 600 líneas de diff con tests; una PR que llegue a **1500–2000 líneas** sigue siendo aceptable y no hace falta partirla, pero por encima de eso se parte. La pantalla (Frontend) y los volcados generados no cuentan para este límite, pero este plan no los incluye.
- **Motivo**: las PRs grandes se revisan peor. Este plan separa dominio, puertos, casos de uso, repositorios y routers, y cada grupo de casos de uso tiene su PR de lógica y su PR de servidor.

### 14. Cambios de contrato y versión

- **Versión de la API**: pasa de `1.0.0` a `1.2.0` en la aplicación, igual que el contrato.
- **Contrato**: la PR #39 ya lo dejó en 1.2.0 (sin integraciones de M4 y M6, con `estado`). Queda pendiente solo la descripción de roles de `bearerAuth`, que dice que el conductor puede consultar conductores. Es una PR de contrato aparte y chica, y no bloquea a las demás.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Las PRs de repositorios SQL esperan la migración y los modelos de Datos y seguridad | La lógica y el servidor avanzan con repositorios en memoria; las PRs SQL se abren cuando esa migración está en `dev` |
| Los nombres de tablas y columnas pueden cambiar en Datos y seguridad | El [data-model.md](./data-model.md) es la interfaz acordada; cualquier cambio se avisa y se actualiza ahí primero |
| El token del conductor todavía no trae `id_conductor` en el realm | Los tests de API firman sus propios tokens; el realm lo agrega el otro grupo (issue #36) |
| El código de la Iteración 1 todavía usa `conectado` y `disponible` | La PR de dominio (L1) y la migración de Datos y seguridad los reemplazan por `estado`; hasta entonces el contrato y el código difieren |
| M4 o M6 pueden necesitar escribir el estado | Hoy no hay operación para eso; se acuerda con ellos y, si hace falta, se suma al contrato |

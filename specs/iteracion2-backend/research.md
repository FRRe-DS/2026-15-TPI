# Investigación: Iteración 2 — Backend de M3

Decisiones técnicas con su justificación. El stack y las versiones son los de la [Iteración 1](../iteracion1/research.md) y no cambian: no se agregan dependencias nuevas. Todo lo que sigue se resolvió a partir del [spec.md](./spec.md), del contrato `docs/contract/openapi.yaml` (1.1.0) y del código de `dev`.

## Decisiones de diseño

### 1. Una sola regla de concurrencia: bloqueo de fila del conductor

- **Decisión**: toda operación que cambia el estado de un conductor (`PATCH /estado`, `PATCH` de M4, aceptar una solicitud y finalizar un viaje) abre una transacción y llama primero a `bloquear_conductor` (`SELECT ... FOR UPDATE`, ya existente). Las que además tocan una solicitud la bloquean después (`bloquear_solicitud`). Orden fijo de bloqueos: **conductor → solicitud**.
- **Motivo**: serializa los cambios del mismo conductor sin agregar columnas ni mecanismos nuevos, y evita bloqueos cruzados (deadlocks) porque todos toman los bloqueos en el mismo orden. Cubre "PATCH de estado contra PATCH de M4" y "aceptar contra cambio de M4" (SC-011).
- **Para responder una solicitud**: como el conductor dueño se conoce recién al leer la solicitud, el caso de uso la lee sin bloqueo, bloquea al conductor, bloquea la solicitud y vuelve a validar su estado. Dos respuestas simultáneas quedan en fila: la primera gana y la segunda ve la solicitud ya respondida (`409`).
- **Alternativas**: bloqueo optimista con columna de versión (obliga a reintentos y a una columna más) y nivel de aislamiento serializable (más caro y con reintentos por fallas de serialización).

### 2. Idempotencia de la finalización de viaje

- **Decisión**: el registro del viaje procesado usa `viaje_finalizado.id_viaje` como clave primaria y se inserta con `INSERT ... ON CONFLICT DO NOTHING` (el puerto devuelve si insertó). Dentro de la misma transacción, y con el conductor bloqueado, si se insertó se aplican la ubicación y el puntaje; si no se insertó, se lee el registro existente:
  - mismos datos (`id_conductor`, `fecha_finalizacion`, destino y puntaje) → `200` con el resultado de la primera vez, sin efectos nuevos;
  - datos distintos para el mismo `id_viaje` → `409` con `VIAJE_EN_CONFLICTO`.
- **Motivo**: la clave primaria garantiza una sola fila aunque lleguen veinte pedidos a la vez (SC-010), y distingue un reintento legítimo de M6 de un informe contradictorio. Así el `409` que el contrato ya define tiene un uso claro.
- **Respuesta en el reintento**: se arma con lo guardado (`ubicacion_actualizada` y `puntaje_registrado` quedan como en la primera respuesta). Por eso `viaje_finalizado` guarda también si la ubicación se aplicó.
- **Ubicación fuera de orden**: el destino pasa a ser la ubicación del conductor solo si `fecha_finalizacion` no es anterior a su `fecha_act_ubic` actual; si es anterior, `ubicacion_actualizada` es falso. Evita pisar una ubicación más nueva con un informe viejo.
- **Alternativas**: devolver siempre `409` en el reintento (descartado en la clarificación) y un candado por viaje fuera de la base (innecesario con la clave primaria).

### 3. Pedidos de M4 más viejos que el último cambio

- **Decisión**: se compara `actualizado` del pedido con `fecha_ultimo_cambio_estado` del conductor. **Estrictamente anterior → se ignora** y se responde `200` con el estado vigente. **Igual o posterior → se aplica**, y `fecha_ultimo_cambio_estado` pasa a valer el `actualizado` de M4. Un cambio que hace el propio conductor guarda la hora del servidor.
- **Motivo**: así gana siempre el cambio más reciente, venga de quien venga, y un reintento idéntico se aplica de nuevo sin cambiar nada (el mismo valor). El empate se aplica para no perder un cambio legítimo con la misma marca de tiempo.
- **Riesgo conocido**: si el reloj de M4 está adelantado, sus pedidos pueden ganarles a cambios posteriores del conductor. Se acepta para la Iteración 2 y se documenta en el [quickstart](./quickstart.md); coordinar con M4 que el reloj sea UTC sincronizado.
- **Alternativa**: guardar siempre la hora del servidor y usar `actualizado` solo para comparar (se pierde la referencia del tiempo de M4 y se rompe el orden entre reintentos).

### 4. Cálculo de `puntaje_promedio`

- **Decisión**: el conductor guarda `suma_puntajes` y `cantidad_calificaciones` (enteros). `puntaje_promedio = suma / cantidad`, calculado en el dominio con `Decimal`, redondeado a 2 decimales (mitad hacia arriba) y expuesto como número; `null` si la cantidad es 0. El puntaje y su cantidad se suman dentro de la misma transacción con el conductor bloqueado.
- **Motivo**: no se guarda un promedio derivado que pueda quedar inconsistente, y los enteros se suman sin errores de punto flotante. Un viaje sin puntaje no toca ningún contador.
- **Alternativas**: guardar el promedio y recalcularlo de forma incremental (acumula error de redondeo) y recalcular desde una tabla de calificaciones por cada lectura (más costoso, innecesario hoy; `viaje_finalizado` conserva el puntaje por si hace falta auditar).

### 5. Reglas de disponibilidad en un solo lugar del dominio

- **Decisión**: un módulo `dominio/disponibilidad.py` concentra la regla "puede estar disponible" (conductor conectado, conductor `APROBADA`, vehículo activo existente y `APROBADA`) y la función que aplica un cambio de estado. Lo usan `actualizar_estado_conductor`, `actualizar_disponibilidad_desde_m4` y `responder_solicitud`.
- **Resultados**, que los tres casos de uso comparten:

| Situación | Resultado |
|---|---|
| Pide `disponible = true` y no cumple la regla | `ConductorNoHabilitado` (`422`) y no cambia nada |
| Pide `conectado = false` | queda `disponible = false` aunque pida otra cosa |
| Quita el vehículo activo (`null`) | queda `disponible = false` |
| Cambia a un vehículo activo no `APROBADA` estando disponible | queda `disponible = false` |
| Vehículo activo inexistente o de otro conductor | `NoEncontrado` (`404`) |
| El pedido no cambia ningún valor | no cambia `actualizado` |

- **Motivo**: una regla escrita una sola vez evita que el `PATCH` del conductor, el de M4 y la aceptación de solicitudes se contradigan, y se prueba con tests unitarios sin base.
- **`actualizado`**: cambia solo cuando cambia la conexión, la disponibilidad o el vehículo activo; no cambia por actualizar solo la ubicación (FR-025).

### 6. Ubicación simulada fija

- **Decisión**: el caso de uso `actualizar_estado_conductor` recibe la coordenada simulada como dato inyectado. Si el conductor pasa de desconectado a conectado, no tiene ubicación y el pedido no trae `latitud` y `longitud`, se le asigna esa coordenada con `fecha_act_ubic` igual a la hora del servidor. Después, las actualizaciones sin ubicación no la tocan.
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

- **Versión de la API**: pasa de `1.0.0` a `1.1.0` en la aplicación, igual que el contrato.
- **Contrato**: el YAML no cambia por este plan, salvo la descripción de roles de `bearerAuth`, que dice que el conductor puede consultar conductores. Es una PR de contrato aparte y chica, y no bloquea a las demás.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Las PRs de repositorios SQL esperan la migración y los modelos de Datos y seguridad | La lógica y el servidor avanzan con repositorios en memoria; las PRs SQL se abren cuando esa migración está en `dev` |
| Los nombres de tablas y columnas pueden cambiar en Datos y seguridad | El [data-model.md](./data-model.md) es la interfaz acordada; cualquier cambio se avisa y se actualiza ahí primero |
| El token del conductor todavía no trae `id_conductor` en el realm | Los tests de API firman sus propios tokens; el realm lo agrega el otro grupo (issue #36) |
| Reloj de M4 desfasado | Documentado en la decisión 3; coordinar con M4 |

# Especificación de la Funcionalidad: Iteración 2 — Backend de M3 (Conductores y Vehículos)

**Rama de la Funcionalidad**: `docs/planificacion-iteracion2-backend`

**Creada**: 2026-11-03

**Estado**: Borrador

**Entrada**: Iteración 2 del Módulo 3, parte de Backend (lógica de negocio y servidor HTTP). Cubrir los 9 endpoints de `docs/contract/openapi.yaml` (versión 1.1.0) que la Iteración 1 dejó sin implementar y adaptar lo ya implementado a los cambios del contrato. El contrato tiene 19 operaciones y es la fuente de verdad.

## Clarificaciones

### Sesión 2026-11-03

- Q: ¿Cómo llegan las ofertas de M5 a las solicitudes de M3? → A: Queda fuera de esta iteración. Se implementan listar y responder solicitudes; el origen de las solicitudes se define con M5 después. Las pruebas y los datos de prueba cargan las solicitudes directamente.
- Q: ¿Qué responde M3 si M6 informa un viaje ya procesado? → A: `200` con el mismo resultado de la primera vez, sin duplicar efectos.
- Q: ¿Entra en esta iteración que cada conductor acceda solo a sus propios datos? → A: Sí, en todos los endpoints con `{id_conductor}` (y en responder solicitudes, que se miden contra el conductor dueño). El operador y el servicio no tienen esa restricción. Cualquier intento de un conductor sobre datos de otro responde `403`.
- Q: ¿Puede un conductor listar a todos los conductores con `GET /conductores`? → A: No. Recibe `403`; solo operador y servicio listan. El conductor consulta lo suyo con `GET /conductores/{id_conductor}`.
- Q: Los parámetros `latitud` y `longitud` de `GET /conductores`, ¿ordenan por cercanía o excluyen a los lejanos? → A: Ninguna de las dos. M3 no filtra ni ordena por ubicación: la búsqueda por cercanía la hace otro módulo (M4) y M3 solo presenta las coordenadas de cada conductor. Los parámetros se siguen aceptando y se ignoran, como en la Iteración 1.
- Q: Al responder una solicitud, ¿la oferta vence según la hora del servidor o según la `hora_rta` que manda el cliente? → A: Según la hora del servidor al recibir el pedido. La `hora_rta` del cliente es obligatoria (como pide el contrato) y se guarda tal cual, pero no decide el vencimiento.
- Q: Cuando un conductor acepta una solicitud, ¿M3 cambia su disponibilidad a "no disponible"? → A: Sí. Al aceptar, el conductor pasa a no disponible en el mismo paso, y rechazar no cambia su disponibilidad. Sigue valiendo lo que M4 informe después por `PATCH .../disponibilidad`.
- Q: Si un conductor se conecta o actualiza su estado sin informar ubicación, ¿M3 inventa una ubicación simulada? → A: Solo la primera vez: si el conductor no tiene ubicación y se conecta sin informarla, M3 le asigna una simulada fija. Después no la cambia.

## Alcance

Este spec cubre **solo el backend**. Los grupos de Datos y seguridad, Testing y Frontend planifican por separado y las planificaciones se integran después. Lo que Backend necesita de los otros grupos se detalla en *Dependencias con otros grupos*.

**En alcance (9 endpoints nuevos):**

| # | Endpoint | Roles | Grupo del contrato |
|---|---|---|---|
| 1 | `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` | conductor, operador, servicio | Vehículos |
| 2 | `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | conductor, operador | Documentación |
| 3 | `GET /conductores/{id_conductor}/estado` | conductor, operador, servicio | Disponibilidad |
| 4 | `PATCH /conductores/{id_conductor}/estado` | conductor, operador | Disponibilidad |
| 5 | `GET /conductores/{id_conductor}/ubicacion` | conductor, operador, servicio | Disponibilidad |
| 6 | `GET /conductores/{id_conductor}/solicitudes` | conductor, operador | Solicitudes |
| 7 | `POST /solicitudes/{id_solicitud}` | conductor, operador | Solicitudes |
| 8 | `PATCH /integraciones/m4/conductores/{id_conductor}/disponibilidad` | solo servicio | Integración M4 |
| 9 | `POST /integraciones/m6/viajes/{id_viaje}/finalizacion` | solo servicio | Integración M6 |

**En alcance (adaptación de lo ya implementado en la Iteración 1):**

- Aceptar el rol `servicio` en la validación del token y exigirlo en los endpoints de integración.
- Mostrar `puntaje_promedio` y `cantidad_calificaciones` en las respuestas de conductor, e `id_vehiculo_activo` en las que incluyen ubicación.
- Implementar el filtro `tipo_servicio` del listado de conductores, que hoy se acepta y se ignora. Los parámetros `latitud` y `longitud` del listado siguen aceptándose y se ignoran: M3 no filtra ni ordena por cercanía.
- Permitir que la habilitación de cada tipo de servicio de un vehículo deje de estar siempre en falso.
- Que cada conductor acceda solo a sus propios datos (diferido de la Iteración 1), en los endpoints nuevos y en los ya implementados.
- Versión de la API 1.1.0 y pruebas de paridad de rutas con las 19 operaciones.

**Fuera de alcance:**

- Lo que M3 solo consume de otros módulos: los endpoints de viajes de M6, la calificación del cliente (RF3.7) y la recepción de ubicación en M4. No figuran en nuestro contrato y no se implementan clientes HTTP hacia ellos.
- Integraciones salientes reales con M1, M4, M5 y M6.
- Migración de base de datos, datos de prueba y configuración del servicio de identidad (grupo de Datos y seguridad), pruebas de contrato e integración (grupo de Testing) y pantalla (grupo de Frontend).

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia 1 - Acceso por rol, incluido el rol de servicio (Prioridad: P1)

Los módulos vecinos (M4 y M6) llaman a M3 con una cuenta técnica de rol `servicio`. Ese rol puede leer conductores y es el único que puede usar las operaciones de integración. Conductores y operadores no pueden usarlas.

**Por qué esta prioridad**: Sin este rol, M4 y M6 reciben `403` en todo; las historias 2, 3 y 4 dependen de esto.

**Prueba independiente**: Se prueba llamando a un endpoint de lectura y a uno de integración con tokens de cada rol.

**Escenarios de aceptación**:

1. **Dado** un token con rol `servicio`, **cuando** consulta el listado de conductores, un conductor, su estado o su ubicación, **entonces** la operación se permite.
2. **Dado** un token con rol `servicio`, **cuando** intenta una acción reservada al operador (por ejemplo, aprobar la habilitación de un conductor), **entonces** se responde `403`.
3. **Dado** un token con rol `conductor` o `operador`, **cuando** llama a un endpoint de `/integraciones/...`, **entonces** se responde `403` con el mensaje "Se requiere el rol servicio".
4. **Dado** una solicitud sin token o con un token inválido, **cuando** se invoca cualquier endpoint nuevo, **entonces** se responde `401`.
5. **Dado** un token con rol `servicio`, **cuando** intenta actualizar el estado de un conductor (`PATCH /conductores/{id}/estado`) o responder una solicitud, **entonces** se responde `403`.

---

### Historia 2 - Consultar y actualizar el estado y la ubicación del conductor (Prioridad: P1)

M4 consulta la conexión, la disponibilidad, el vehículo activo y la ubicación de un conductor. El conductor (o un operador) informa su conexión, disponibilidad, vehículo activo y, opcionalmente, su ubicación.

**Por qué esta prioridad**: Es lo que M4 necesita para elegir conductores; toda la asignación de viajes depende de este estado.

**Prueba independiente**: Se prueba actualizando el estado de un conductor aprobado y consultando luego el estado y la ubicación.

**Escenarios de aceptación**:

1. **Dado** un conductor existente, **cuando** se consulta su estado, **entonces** se devuelven `conectado`, `disponible`, `id_vehiculo_activo` (nulo si no tiene) y `actualizado`, sin datos de ubicación.
2. **Dado** un conductor existente, **cuando** se consulta su ubicación, **entonces** se devuelven `latitud`, `longitud` y `fecha_act_ubic`. Si todavía no hay ubicación, se responde `200` con los tres campos en `null`, nunca con `0,0`.
3. **Dado** un conductor `APROBADA` con un vehículo activo `APROBADA`, **cuando** informa `conectado` y `disponible` verdaderos, **entonces** queda disponible y `actualizado` toma la hora del cambio.
4. **Dado** un conductor no `APROBADA`, o cuyo vehículo activo no está `APROBADA`, o desconectado, **cuando** intenta quedar disponible, **entonces** se rechaza y no cambia nada.
5. **Dado** un conductor disponible, **cuando** informa que se desconecta, **entonces** queda también no disponible.
6. **Dado** una actualización con `latitud` y `longitud`, **cuando** se aplica, **entonces** M3 guarda la ubicación y fija `fecha_act_ubic` con la hora del servidor. Si se informa una sola de las dos, se rechaza.
7. **Dado** un conductor que ya tiene ubicación, **cuando** se aplica una actualización sin ubicación, **entonces** la ubicación guardada no cambia.
8. **Dado** un conductor que todavía no tiene ubicación, **cuando** se conecta sin informar ubicación, **entonces** M3 le asigna una ubicación simulada fija (nunca `0,0`) con `fecha_act_ubic` igual a la hora del servidor, y a partir de ahí las actualizaciones sin ubicación no la cambian.
9. **Dado** un cuerpo vacío o con valores fuera de rango, **cuando** se intenta actualizar, **entonces** se rechaza con error `{codigo, mensaje}`.
10. **Dado** un conductor inexistente, **cuando** se consulta o actualiza, **entonces** se responde `404`.

---

### Historia 3 - Recibir cambios de disponibilidad desde M4 (Prioridad: P1)

M4 informa que un conductor quedó no disponible por una reserva o un viaje, o que volvió a estar disponible.

**Por qué esta prioridad**: Evita que M3 y M4 vean estados distintos del mismo conductor; sin esto se asignan viajes a conductores ocupados.

**Prueba independiente**: Se prueba con un token de servicio enviando cambios de disponibilidad en distintos órdenes.

**Escenarios de aceptación**:

1. **Dado** un conductor disponible, **cuando** M4 informa `disponible: false`, **entonces** queda no disponible, `actualizado` refleja el cambio y la respuesta trae el estado vigente.
2. **Dado** un conductor conectado y `APROBADA`, con vehículo activo `APROBADA`, **cuando** M4 informa `disponible: true`, **entonces** queda disponible.
3. **Dado** un conductor desconectado o no habilitado, o con vehículo activo no habilitado, **cuando** M4 informa `disponible: true`, **entonces** se responde `422` y no cambia nada.
4. **Dado** un pedido cuyo `actualizado` es anterior al último cambio de estado registrado, **cuando** llega, **entonces** M3 lo ignora y devuelve el estado vigente.
5. **Dado** el mismo pedido enviado dos veces, **cuando** M4 reintenta, **entonces** el resultado es el mismo y no se duplican efectos.
6. **Dado** un pedido de M4, **cuando** se aplica, **entonces** solo cambia `disponible`: la conexión, el vehículo activo, la ubicación y la habilitación no se modifican.
7. **Dado** un conductor inexistente, **cuando** M4 informa un cambio, **entonces** se responde `404`.

---

### Historia 4 - Recibir viajes finalizados desde M6 y registrar el puntaje (Prioridad: P1)

M6 informa que un viaje finalizó. M3 usa el destino como nueva ubicación del conductor y, si viene un puntaje, lo suma al promedio del conductor.

**Por qué esta prioridad**: Es la única forma en que el conductor recibe puntajes y actualiza su ubicación después de un viaje.

**Prueba independiente**: Se prueba con un token de servicio informando un viaje finalizado con y sin puntaje, y consultando luego al conductor.

**Escenarios de aceptación**:

1. **Dado** un viaje finalizado con destino y `puntaje_conductor`, **cuando** M6 lo informa, **entonces** la ubicación del conductor pasa a ser el destino, el puntaje se registra, `cantidad_calificaciones` sube en 1 y `puntaje_promedio` se recalcula. La respuesta indica `procesado`, `ubicacion_actualizada` y `puntaje_registrado` en verdadero.
2. **Dado** un viaje finalizado sin puntaje, **cuando** M6 lo informa, **entonces** se actualiza la ubicación y `puntaje_promedio` y `cantidad_calificaciones` no cambian; `puntaje_registrado` es falso.
3. **Dado** un viaje ya procesado, **cuando** M6 lo informa de nuevo, **entonces** responde `200` con el mismo resultado de la primera vez, sin volver a registrar el puntaje ni duplicar efectos.
4. **Dado** dos informes simultáneos del mismo viaje, **cuando** llegan a la vez, **entonces** el puntaje se cuenta una sola vez.
5. **Dado** un puntaje fuera de 1 a 5 o un estado distinto de `FINALIZADO`, **cuando** M6 lo informa, **entonces** se rechaza con `400`.
6. **Dado** un conductor inexistente, **cuando** M6 informa un viaje, **entonces** se responde `404`.
7. **Dado** un conductor sin calificaciones, **cuando** se consulta, **entonces** `puntaje_promedio` es `null` y `cantidad_calificaciones` es `0`.

---

### Historia 5 - Listar y responder solicitudes de viaje (Prioridad: P2)

El conductor (o un operador) lista las solicitudes de viaje que recibió, filtrando por estado, y acepta o rechaza una mientras la oferta esté vigente.

**Por qué esta prioridad**: Es el flujo con M5. El origen de las solicitudes (cómo las crea M5 en M3) queda fuera de esta iteración: se prueba con solicitudes ya cargadas.

**Prueba independiente**: Se prueba con solicitudes cargadas directamente en distintos estados, listándolas y respondiendo una vigente y una vencida.

**Escenarios de aceptación**:

1. **Dado** un conductor con solicitudes, **cuando** se listan, **entonces** se devuelven solo las de ese conductor con `id`, `id_viaje`, `estado`, `vence_en`, `respuesta` y `hora_rta`.
2. **Dado** el filtro `estado` (`PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`), **cuando** se lista, **entonces** se devuelven solo las de ese estado. Un valor inválido se rechaza con `400`.
3. **Dado** una solicitud `PENDIENTE` y vigente, **cuando** el conductor la acepta o la rechaza, **entonces** queda en el estado correspondiente con `respuesta` y con la `hora_rta` que envió el cliente, guardada tal cual. Si la acepta, el conductor pasa a no disponible en el mismo paso y `actualizado` toma la hora del cambio; si la rechaza, su disponibilidad no cambia.
4. **Dado** una solicitud cuya fecha `vence_en` ya pasó según la hora del servidor, **cuando** se intenta responder (aunque la `hora_rta` enviada sea anterior), **entonces** se responde `410` y no cambia.
5. **Dado** una solicitud ya respondida, **cuando** se intenta responder de nuevo, **entonces** se responde `409` y no cambia.
6. **Dado** un conductor `APROBADA` pero no disponible, o no habilitado, **cuando** intenta aceptar, **entonces** se responde `422`.
7. **Dado** una solicitud inexistente o de otro conductor, **cuando** se intenta responder, **entonces** se responde `404`.
8. **Dado** dos respuestas simultáneas a la misma solicitud, **cuando** llegan a la vez, **entonces** solo una se registra y la otra recibe `409`.
9. **Dado** un conductor que acaba de aceptar una solicitud, **cuando** M4 informa más tarde que volvió a estar disponible, **entonces** se aplican las reglas de la Historia 3.
10. **Dado** que una aceptación y un cambio de M4 llegan a la vez sobre el mismo conductor, **cuando** se procesan, **entonces** ninguno se pierde y el estado final es coherente.

---

### Historia 6 - Tipos de servicio y documentación del vehículo (Prioridad: P2)

Se consultan los tipos de servicio de un vehículo y su habilitación, y se registra la documentación del vehículo (seguro, cédula verde y VTV).

**Por qué esta prioridad**: Completa los datos del vehículo; M4 filtra por tipo de servicio.

**Prueba independiente**: Se prueba registrando un vehículo, consultando sus tipos de servicio y cargándole documentos.

**Escenarios de aceptación**:

1. **Dado** un vehículo existente, **cuando** se consultan sus tipos de servicio, **entonces** se devuelve cada tipo (`PASAJEROS`, `ENVIOS`) con su estado `habilitado`.
2. **Dado** un documento válido (`SEGURO`, `CEDULA_VERDE` o `VTV`, con número, fechas y archivo), **cuando** se registra, **entonces** queda guardado con el estado calculado (`VIGENTE` o `VENCIDO`).
3. **Dado** una fecha de vencimiento anterior a la emisión, **cuando** se intenta registrar, **entonces** se rechaza con `422`.
4. **Dado** un tipo de documento inválido o un archivo que no es una URL, **cuando** se intenta registrar, **entonces** se rechaza con `400`.
5. **Dado** un vehículo que no pertenece al conductor indicado, **cuando** se consulta o se registra un documento, **entonces** se responde `404`.
6. **Dado** un vehículo con documentos, **cuando** se consulta el vehículo, **entonces** `documentos` los incluye con su estado calculado en lugar de la lista vacía de la Iteración 1.
7. **Dado** que un tipo de servicio del vehículo está habilitado, **cuando** se consulta el vehículo o el listado de conductores con ese `tipo_servicio`, **entonces** se refleja.

---

### Historia 7 - Listado de conductores con los filtros y datos nuevos (Prioridad: P2)

Se listan conductores filtrando por tipo de servicio y por ubicación, y las respuestas incluyen el puntaje y el vehículo activo.

**Por qué esta prioridad**: M4 usa este listado para buscar conductores; hoy el filtro por tipo de servicio se ignora y faltan los datos de puntaje y vehículo activo. La búsqueda por cercanía la resuelve M4 con las coordenadas que M3 presenta.

**Prueba independiente**: Se prueba con conductores en distintas ubicaciones y con distintos tipos de servicio habilitados.

**Escenarios de aceptación**:

1. **Dado** conductores con distintos tipos de servicio habilitados, **cuando** se filtra por `tipo_servicio`, **entonces** se devuelven solo los que tienen ese tipo habilitado en su vehículo.
2. **Dado** conductores con ubicación, **cuando** se lista, **entonces** cada uno incluye sus coordenadas y la fecha de su ubicación (nulas si no hay), y el orden del listado no depende de ninguna coordenada.
3. **Dado** que se envían `latitud` y `longitud` en el listado, **cuando** se lista, **entonces** se aceptan y no cambian el resultado ni el orden. Un valor fuera de rango se rechaza con `400`.
4. **Dado** que se combinan filtros, **cuando** se lista, **entonces** se aplican todos a la vez (`habilitado`, `disponible`, `tipo_vehiculo`, `tipo_servicio`).
5. **Dado** cualquier conductor devuelto por el listado o por la consulta individual, **cuando** se lee, **entonces** incluye `puntaje_promedio`, `cantidad_calificaciones` e `id_vehiculo_activo`.

---

### Historia 8 - Cada conductor accede solo a sus propios datos (Prioridad: P1)

Un conductor autenticado solo puede consultar y modificar sus propios recursos. Los operadores y las cuentas de servicio mantienen el acceso que su rol permite.

**Por qué esta prioridad**: Es un requisito de seguridad diferido de la Iteración 1; sin él, cualquier conductor ve y cambia datos de otro.

**Prueba independiente**: Se prueba con el token de un conductor consultando recursos propios y ajenos en distintos endpoints.

**Escenarios de aceptación**:

1. **Dado** un conductor autenticado, **cuando** consulta su propio conductor, sus vehículos, su documentación, su habilitación, su estado, su ubicación o sus solicitudes, **entonces** obtiene los datos.
2. **Dado** un conductor autenticado, **cuando** intenta consultar o modificar cualquier recurso de otro conductor, **entonces** se responde `403` con el código `ACCESO_PROHIBIDO` y no cambia nada.
3. **Dado** un conductor autenticado, **cuando** intenta responder una solicitud que pertenece a otro conductor, **entonces** se responde `403`.
4. **Dado** un operador autenticado, **cuando** consulta o modifica datos de cualquier conductor dentro de lo que su rol permite, **entonces** se permite.
5. **Dado** una cuenta de servicio, **cuando** lee conductores, estados y ubicaciones, **entonces** se permite sin restricción por conductor.
6. **Dado** un token de conductor sin el dato de su propio identificador, **cuando** intenta cualquier operación sobre un conductor, **entonces** se responde `403`.
7. **Dado** un conductor autenticado, **cuando** consulta el listado de conductores (`GET /conductores`), **entonces** se responde `403`; el operador y el servicio sí pueden.

---

### Casos Límite

- Conductor sin vehículo activo que intenta quedar disponible: se rechaza.
- Cambio de `id_vehiculo_activo` a un vehículo que no es del conductor o que no existe: se rechaza.
- Conductor suspendido mientras está disponible: la disponibilidad no se cambia sola; las reglas se aplican cuando alguien intenta volver a marcarlo disponible (ver Supuestos).
- Dos cambios de estado simultáneos sobre el mismo conductor (del conductor y de M4): ninguno se pierde y el resultado es coherente.
- Un token `servicio` sin ningún otro rol y un token con varios roles: se permite lo que cada rol permita.
- Listado sin resultados: lista vacía, no error.
- Un conductor que consulta el estado o la ubicación de otro conductor (aunque sean lecturas que M4 sí puede hacer): `403`.
- Todos los errores usan el formato `{codigo, mensaje}` del catálogo, ampliado con los códigos nuevos.

## Requisitos *(obligatorio)*

### Requisitos Funcionales

- **FR-020**: El sistema DEBE aceptar tokens con el rol `servicio`, exigirlo en `/integraciones/m4/...` y `/integraciones/m6/...` (`403` para otros roles) y permitirle leer conductores, su estado y su ubicación, pero no ejecutar acciones de operador ni actualizar estados o solicitudes.
- **FR-021**: El sistema DEBE exponer el estado vigente de un conductor (`conectado`, `disponible`, `id_vehiculo_activo`, `actualizado`) sin datos de ubicación.
- **FR-022**: El sistema DEBE exponer la última ubicación (`latitud`, `longitud`, `fecha_act_ubic`) y responder `200` con los tres campos en `null` si no hay ninguna, sin devolver nunca `0,0`.
- **FR-023**: El sistema DEBE permitir al conductor o al operador actualizar conexión, disponibilidad, vehículo activo y ubicación, con al menos un campo. `latitud` y `longitud` DEBEN venir juntas y, si vienen, `fecha_act_ubic` DEBE ser la hora del servidor. Si el conductor no tiene ubicación y se conecta sin informarla, el sistema DEBE asignarle una ubicación simulada fija una sola vez; si ya tiene ubicación, una actualización sin ubicación NO DEBE cambiarla.
- **FR-024**: Un conductor DEBE poder quedar disponible solo si está conectado y con habilitación `APROBADA`, y su vehículo activo también está `APROBADA`. Un conductor desconectado DEBE quedar siempre no disponible.
- **FR-025**: `actualizado` DEBE cambiar con cada cambio de conexión, disponibilidad o vehículo activo, y NO DEBE cambiar al actualizar solo la ubicación.
- **FR-026**: El sistema DEBE aceptar de M4 un cambio de `disponible` (solo rol `servicio`). DEBE ignorar el pedido y devolver el estado vigente si `actualizado` es anterior al último cambio registrado, DEBE rechazar con `422` el paso a disponible si no se cumplen las reglas de FR-024 y NO DEBE modificar nada más que `disponible`.
- **FR-027**: El sistema DEBE aceptar de M6 un viaje finalizado (solo rol `servicio`): guardar el destino como ubicación del conductor y, si viene `puntaje_conductor` (1 a 5), registrarlo y recalcular `puntaje_promedio` y `cantidad_calificaciones`.
- **FR-028**: El procesamiento de un viaje finalizado DEBE ser idempotente por `id_viaje`, incluso ante informes simultáneos: el puntaje se cuenta una sola vez.
- **FR-029**: `puntaje_promedio` DEBE ser `null` mientras `cantidad_calificaciones` sea 0, y estar entre 1 y 5 en otro caso. Ambos campos DEBEN aparecer en las respuestas de conductor.
- **FR-030**: El sistema DEBE listar las solicitudes de un conductor con filtro opcional por `estado`.
- **FR-031**: El sistema DEBE permitir aceptar o rechazar una solicitud `PENDIENTE` y vigente, registrando `respuesta` y `hora_rta`. Aceptar DEBE dejar al conductor no disponible en la misma operación (con `actualizado` actualizado); rechazar NO DEBE cambiar su disponibilidad. DEBE responder `410` si la oferta venció y `409` si ya fue respondida, e impedir que dos respuestas simultáneas se registren ambas.
- **FR-032**: El sistema DEBE devolver los tipos de servicio de un vehículo con su estado `habilitado`, y `404` si el vehículo no es del conductor.
- **FR-033**: El sistema DEBE registrar documentación del vehículo (`SEGURO`, `CEDULA_VERDE`, `VTV`), calcular su estado (`VIGENTE` o `VENCIDO`) al leer y rechazar con `422` un vencimiento anterior a la emisión.
- **FR-034**: El listado de conductores DEBE soportar el filtro `tipo_servicio`, combinable con `habilitado`, `disponible` y `tipo_vehiculo`. Los parámetros `latitud` y `longitud` DEBEN aceptarse (válidos en rango) y NO DEBEN filtrar ni ordenar: la búsqueda por cercanía la hace M4 con las coordenadas que M3 devuelve.
- **FR-035**: Las respuestas de conductor con ubicación DEBEN incluir `id_vehiculo_activo` (nulo si no hay).
- **FR-036**: Todas las respuestas, incluidos los errores, DEBEN cumplir `docs/contract/openapi.yaml`. El catálogo de errores DEBE ampliarse con los códigos de `410`, de disponibilidad y de solicitudes.
- **FR-037**: Los cambios de estado, de solicitudes y de puntaje DEBEN tolerar solicitudes simultáneas sin perder ni duplicar efectos, y cubrirse con pruebas (constitución, principio XI).
- **FR-038**: La lógica DEBE desarrollarse con TDD, manteniendo la cobertura sobre el umbral vigente de CI, y la versión de la API DEBE ser 1.1.0.
- **FR-039**: El backend DEBE definir en un documento compartido (`data-model.md`) qué datos necesita de la base, sin implementar la migración. No se consultan datos de otros módulos.
- **FR-040**: Un conductor DEBE poder acceder solo a los recursos de su propio `id_conductor` en todos los endpoints con `{id_conductor}` y al responder solicitudes; cualquier acceso a datos de otro conductor DEBE responder `403` con el código `ACCESO_PROHIBIDO`. El operador y el servicio no tienen esa restricción. El identificador del conductor DEBE tomarse del token y no de lo que envíe el cliente.
- **FR-041**: El listado de conductores (`GET /conductores`) DEBE quedar disponible solo para operador y servicio; un conductor recibe `403`.

### Entidades Clave

- **Estado del conductor**: conexión, disponibilidad, vehículo activo y fecha del último cambio (`actualizado`).
- **Ubicación del conductor**: latitud, longitud y fecha de registro. Puede no existir.
- **Calificación del conductor**: puntaje de 1 a 5 recibido en un viaje; sus totales forman `puntaje_promedio` y `cantidad_calificaciones`.
- **Viaje finalizado procesado**: registro de que un viaje ya fue informado por M6, con su conductor y destino, para no procesarlo dos veces.
- **Solicitud**: oferta de viaje a un conductor, con estado (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`), fecha límite, respuesta y hora de respuesta.
- **Documento del vehículo**: seguro, cédula verde o VTV con número, entidad emisora, fechas, archivo y estado calculado.
- **Tipo de servicio del vehículo**: tipo (`PASAJEROS` o `ENVIOS`) y si está habilitado.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles

- **SC-008**: Las 19 operaciones del contrato responden conforme a él en el 100% de las pruebas de contrato (las 10 de la Iteración 1 más las 9 nuevas).
- **SC-009**: El 100% de las llamadas a `/integraciones/...` con un rol distinto de `servicio` es rechazado, y el 100% de las llamadas sin token válido recibe `401`.
- **SC-010**: Ante 20 informes simultáneos del mismo viaje, el puntaje se cuenta exactamente una vez.
- **SC-011**: Ante dos cambios de estado simultáneos sobre el mismo conductor (del conductor y de M4), ninguno se pierde y el estado final es coherente en el 100% de las ejecuciones.
- **SC-012**: Un pedido de M4 más viejo que el último cambio nunca modifica el estado.
- **SC-013**: Una solicitud vencida o ya respondida nunca cambia al intentar responderla.
- **SC-014**: La cobertura de pruebas sobre lo implementado no baja del umbral vigente de CI.
- **SC-015**: El listado devuelve el mismo resultado, con el mismo orden, con o sin `latitud` y `longitud` en el 100% de los casos de prueba.
- **SC-016**: El 100% de los intentos de un conductor sobre datos de otro conductor es rechazado con `403`, y el 100% de los accesos a datos propios se permite.

## Dependencias con otros grupos

Se definen como interfaz; no se implementan en este spec.

| Grupo | Qué necesita Backend |
|---|---|
| Datos y seguridad | Migración con el vehículo activo del conductor, la fecha del último cambio de estado, los puntajes (suma y cantidad), las solicitudes, la documentación del vehículo y los viajes finalizados procesados; el rol `servicio` y las cuentas técnicas de M4 y M6; el identificador del conductor en el token de cada usuario conductor (coincidente con el conductor de los datos de prueba); datos de prueba para cada endpoint, incluidas solicitudes ya cargadas |
| Testing | Pruebas de contrato y de integración de los 9 endpoints nuevos, matriz de roles y casos de concurrencia |
| Frontend | Sin cambios requeridos por este spec |

El detalle de lo que necesita de Datos y seguridad está en el [issue #36](https://github.com/FRRe-DS/2026-15-TPI/issues/36), y lo de Testing en un comentario de la [PR #31](https://github.com/FRRe-DS/2026-15-TPI/pull/31).

## Supuestos

- El stack de la Iteración 1 (FastAPI, PostgreSQL, Keycloak) no cambia.
- `docs/contract/openapi.yaml` (1.1.0) es la fuente de verdad. No se agrega ningún endpoint que no esté en él.
- El promedio es la suma de los puntajes dividida por la cantidad de calificaciones recibidas, y un viaje sin puntaje no cuenta como calificación.
- Una solicitud `PENDIENTE` cuya fecha `vence_en` pasó, medida con la hora del servidor, se trata como `VENCIDA` al leerla y al intentar responderla, aunque la fila no se haya actualizado.
- Si M4 informa `actualizado` igual al último cambio registrado, el pedido se aplica (solo se ignora si es estrictamente anterior).
- Cambiar la habilitación de un conductor o vehículo (por un operador) no modifica `disponible` por sí solo; las reglas de disponibilidad se aplican cuando alguien intenta marcarlo disponible.
- Cambiar `id_vehiculo_activo` a un vehículo ajeno o inexistente se rechaza; `null` quita el vehículo activo y deja al conductor no disponible.
- `POST /conductores` (alta) queda permitido a cualquier rol autenticado, porque todavía no existe un `id_conductor` propio. El resto de las reglas de rol de la Iteración 1 se mantienen: las acciones de habilitación son solo del operador.
- La descripción de roles del esquema de seguridad del contrato dice que el conductor tiene "consulta de conductores y vehículos"; hay que ajustarla (cambio de contrato) para que refleje que el listado es solo de operador y servicio.
- Las solicitudes llegan a M3 por un mecanismo que define M5 más adelante; en esta iteración no hay un endpoint para crearlas.
- La ubicación simulada es una coordenada fija y configurable, distinta de `0,0`, que define el plan. Se asigna solo al conectarse por primera vez sin ubicación; no la asigna el cambio de disponibilidad de M4 ni la finalización de un viaje (esa ya trae el destino).
- Los códigos de error nuevos se agregan al catálogo de la Iteración 1 (`specs/iteracion1/contracts/errores.md`) y se documentan en el plan.
- Requisitos no funcionales de TP1 aplicables: los mismos que en la Iteración 1 (RNF-01 a RNF-08 y RNF-20).

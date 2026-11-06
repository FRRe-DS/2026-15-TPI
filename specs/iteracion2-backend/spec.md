# Especificación de la Funcionalidad: Iteración 2 — Backend de M3 (Conductores y Vehículos)

**Rama de la Funcionalidad**: `docs/planificacion-iteracion2-backend`

**Creada**: 2026-11-03

**Estado**: Borrador

**Entrada**: Iteración 2 del Módulo 3, parte de Backend (lógica de negocio y servidor HTTP). Cubrir los 7 endpoints de `docs/contract/openapi.yaml` (versión 1.2.0) que la Iteración 1 dejó sin implementar y adaptar lo ya implementado a los cambios del contrato. El contrato tiene 17 operaciones y es la fuente de verdad.

## Clarificaciones

### Sesión 2026-11-03

- Q: ¿Cómo llegan las ofertas de M5 a las solicitudes de M3? → A: Queda fuera de esta iteración. Se implementan listar y responder solicitudes; el origen de las solicitudes se define con M5 después. Las pruebas y los datos de prueba cargan las solicitudes directamente.
- Q: ¿Entra en esta iteración que cada conductor acceda solo a sus propios datos? → A: Sí, en todos los endpoints con `{id_conductor}` (y en responder solicitudes, que se miden contra el conductor dueño). El operador y el servicio no tienen esa restricción. Cualquier intento de un conductor sobre datos de otro responde `403`.
- Q: ¿Puede un conductor listar a todos los conductores con `GET /conductores`? → A: No. Recibe `403`; solo operador y servicio listan. El conductor consulta lo suyo con `GET /conductores/{id_conductor}`.
- Q: Los parámetros `latitud` y `longitud` de `GET /conductores`, ¿ordenan por cercanía o excluyen a los lejanos? → A: Ninguna de las dos. M3 no filtra ni ordena por ubicación: la búsqueda por cercanía la hace otro módulo (M4) y M3 solo presenta las coordenadas de cada conductor. Los parámetros se siguen aceptando y se ignoran, como en la Iteración 1.
- Q: Al responder una solicitud, ¿la oferta vence según la hora del servidor o según la `hora_rta` que manda el cliente? → A: Según la hora del servidor al recibir el pedido. La `hora_rta` del cliente es obligatoria (como pide el contrato) y se guarda tal cual, pero no decide el vencimiento.
- Q: Si un conductor se conecta o actualiza su estado sin informar ubicación, ¿M3 inventa una ubicación simulada? → A: Solo la primera vez: si el conductor no tiene ubicación y se conecta sin informarla, M3 le asigna una simulada fija. Después no la cambia.

### Sesión 2026-11-03 (cambio de contrato 1.2.0)

- Q: ¿Siguen las operaciones de integración con M4 y M6? → A: No. Se sacaron `PATCH /integraciones/m4/.../disponibilidad` y `POST /integraciones/m6/.../finalizacion`. M3 no expone escrituras para otros módulos. Cómo se actualizan la ubicación y el puntaje tras un viaje queda por acordar con M6 y M2.
- Q: ¿Cómo se representan la conexión y la disponibilidad? → A: Con un solo campo `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) que reemplaza a `conectado` y `disponible` en el conductor, en el estado, en el pedido de cambio y en el filtro del listado.
- Q: ¿Quién asigna `OCUPADO`? → A: M3, al aceptar una solicitud. No se puede pedir en `PATCH /conductores/{id}/estado`, y el conductor vuelve a `DISPONIBLE` pidiéndolo él. Si M4 o M6 necesitan marcarlo, hay que sumar una operación de escritura y acordarlo con ellos.
- Q: ¿Qué pasa con `puntaje_promedio` y `cantidad_calificaciones`? → A: Siguen en las respuestas de conductor como datos de lectura, calculados desde los totales guardados. Ningún endpoint los escribe en esta iteración; el origen se define con M6 y M2.

## Alcance

Este spec cubre **solo el backend**. Los grupos de Datos y seguridad, Testing y Frontend planifican por separado y las planificaciones se integran después. Lo que Backend necesita de los otros grupos se detalla en *Dependencias con otros grupos*.

**En alcance (7 endpoints nuevos):**

| # | Endpoint | Roles | Grupo del contrato |
|---|---|---|---|
| 1 | `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` | conductor, operador, servicio | Vehículos |
| 2 | `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | conductor, operador | Documentación |
| 3 | `GET /conductores/{id_conductor}/estado` | conductor, operador, servicio | Disponibilidad |
| 4 | `PATCH /conductores/{id_conductor}/estado` | conductor, operador | Disponibilidad |
| 5 | `GET /conductores/{id_conductor}/ubicacion` | conductor, operador, servicio | Disponibilidad |
| 6 | `GET /conductores/{id_conductor}/solicitudes` | conductor, operador | Solicitudes |
| 7 | `POST /solicitudes/{id_solicitud}` | conductor, operador | Solicitudes |

**En alcance (adaptación de lo ya implementado en la Iteración 1):**

- Aceptar el rol `servicio` en la validación del token. Es de solo lectura: lee conductores, vehículos, estado y ubicación.
- Reemplazar `conectado` y `disponible` por `estado` en el conductor, sus respuestas y el filtro `estado` del listado (la Iteración 1 los tiene como dos campos).
- Mostrar `puntaje_promedio` y `cantidad_calificaciones` en las respuestas de conductor, e `id_vehiculo_activo` en las que incluyen ubicación.
- Implementar el filtro `tipo_servicio` del listado de conductores, que hoy se acepta y se ignora. Los parámetros `latitud` y `longitud` del listado siguen aceptándose y se ignoran: M3 no filtra ni ordena por cercanía.
- Permitir que la habilitación de cada tipo de servicio de un vehículo deje de estar siempre en falso.
- Que cada conductor acceda solo a sus propios datos (diferido de la Iteración 1), en los endpoints nuevos y en los ya implementados.
- Versión de la API 1.2.0 y pruebas de paridad de rutas con las 17 operaciones.

**Fuera de alcance:**

- Lo que M3 solo consume de otros módulos: los endpoints de viajes de M6, la calificación del cliente (RF3.7) y la recepción de ubicación en M4. No figuran en nuestro contrato y no se implementan clientes HTTP hacia ellos.
- Recibir de M4 o de M6 cambios de disponibilidad, viajes finalizados o puntajes: el contrato ya no tiene esas operaciones y queda por acordar con ellos.
- Integraciones salientes reales con M1, M4, M5 y M6.
- Migración de base de datos, datos de prueba y configuración del servicio de identidad (grupo de Datos y seguridad), pruebas de contrato e integración (grupo de Testing) y pantalla (grupo de Frontend).

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia 1 - Acceso por rol, incluido el rol de servicio de solo lectura (Prioridad: P1)

Los módulos vecinos (M4) llaman a M3 con una cuenta técnica de rol `servicio`. Ese rol solo puede leer conductores, vehículos, estado y ubicación.

**Por qué esta prioridad**: Sin este rol, M4 recibe `403` en todo; las historias 2 y 5 dependen de esto.

**Prueba independiente**: Se prueba llamando a un endpoint de lectura y a uno de escritura con tokens de cada rol.

**Escenarios de aceptación**:

1. **Dado** un token con rol `servicio`, **cuando** consulta el listado de conductores, un conductor, su estado o su ubicación, **entonces** la operación se permite.
2. **Dado** un token con rol `servicio`, **cuando** intenta una acción reservada al operador (por ejemplo, aprobar la habilitación de un conductor), **entonces** se responde `403`.
3. **Dado** un token con rol `servicio`, **cuando** intenta actualizar el estado de un conductor (`PATCH /conductores/{id}/estado`) o responder una solicitud, **entonces** se responde `403`.
4. **Dado** una solicitud sin token o con un token inválido, **cuando** se invoca cualquier endpoint nuevo, **entonces** se responde `401`.

---

### Historia 2 - Consultar y actualizar el estado y la ubicación del conductor (Prioridad: P1)

M4 consulta el estado, el vehículo activo y la ubicación de un conductor. El conductor (o un operador) informa su estado, su vehículo activo y, opcionalmente, su ubicación.

**Por qué esta prioridad**: Es lo que M4 necesita para elegir conductores; toda la asignación de viajes depende de este estado.

**Prueba independiente**: Se prueba actualizando el estado de un conductor aprobado y consultando luego el estado y la ubicación.

**Escenarios de aceptación**:

1. **Dado** un conductor existente, **cuando** se consulta su estado, **entonces** se devuelven `estado`, `id_vehiculo_activo` (nulo si no tiene) y `actualizado`, sin datos de ubicación.
2. **Dado** un conductor existente, **cuando** se consulta su ubicación, **entonces** se devuelven `latitud`, `longitud` y `fecha_act_ubic`. Si todavía no hay ubicación, se responde `200` con los tres campos en `null`, nunca con `0,0`.
3. **Dado** un conductor `APROBADA` con un vehículo activo `APROBADA`, **cuando** informa `estado: DISPONIBLE`, **entonces** queda disponible (también si estaba `DESCONECTADO`) y `actualizado` toma la hora del cambio.
4. **Dado** un conductor no `APROBADA`, o sin vehículo activo `APROBADA`, **cuando** pide `DISPONIBLE`, **entonces** se rechaza con `422` y `CONDUCTOR_NO_HABILITADO`, y no cambia nada.
5. **Dado** un conductor disponible, **cuando** informa `CONECTADO` o `DESCONECTADO`, **entonces** queda en ese estado. Estos dos valores se aceptan siempre.
6. **Dado** un conductor `DISPONIBLE`, **cuando** quita su vehículo activo o lo cambia a uno que no está `APROBADA`, **entonces** pasa a `CONECTADO`.
7. **Dado** un conductor `OCUPADO` (por haber aceptado una solicitud), **cuando** pide `DISPONIBLE` y cumple las reglas, **entonces** queda disponible; si pide `CONECTADO` o `DESCONECTADO`, queda en ese estado.
8. **Dado** un pedido con `estado: OCUPADO`, **cuando** se intenta aplicar, **entonces** se rechaza con `400`: ese valor lo asigna M3.
9. **Dado** una actualización con `latitud` y `longitud`, **cuando** se aplica, **entonces** M3 guarda la ubicación y fija `fecha_act_ubic` con la hora del servidor. Si se informa una sola de las dos, se rechaza.
10. **Dado** un conductor que ya tiene ubicación, **cuando** se aplica una actualización sin ubicación, **entonces** la ubicación guardada no cambia.
11. **Dado** un conductor `DESCONECTADO` que todavía no tiene ubicación, **cuando** pasa a otro estado sin informar ubicación, **entonces** M3 le asigna una ubicación simulada fija (nunca `0,0`) con `fecha_act_ubic` igual a la hora del servidor, y a partir de ahí las actualizaciones sin ubicación no la cambian.
12. **Dado** un cuerpo vacío o con valores fuera de rango, **cuando** se intenta actualizar, **entonces** se rechaza con error `{codigo, mensaje}`.
13. **Dado** un conductor inexistente, **cuando** se consulta o actualiza, **entonces** se responde `404`.

---

### Historia 3 - Retirada

Era "Recibir cambios de disponibilidad desde M4". Se retiró con el contrato 1.2.0, que sacó `PATCH /integraciones/m4/.../disponibilidad`. El número se conserva para no cambiar las referencias de `tasks.md`.

---

### Historia 4 - Retirada

Era "Recibir viajes finalizados desde M6 y registrar el puntaje". Se retiró con el contrato 1.2.0, que sacó `POST /integraciones/m6/.../finalizacion`. El número se conserva para no cambiar las referencias de `tasks.md`.

---

### Historia 5 - Listar y responder solicitudes de viaje (Prioridad: P2)

El conductor (o un operador) lista las solicitudes de viaje que recibió, filtrando por estado, y acepta o rechaza una mientras la oferta esté vigente.

**Por qué esta prioridad**: Es el flujo con M5. El origen de las solicitudes (cómo las crea M5 en M3) queda fuera de esta iteración: se prueba con solicitudes ya cargadas.

**Prueba independiente**: Se prueba con solicitudes cargadas directamente en distintos estados, listándolas y respondiendo una vigente y una vencida.

**Escenarios de aceptación**:

1. **Dado** un conductor con solicitudes, **cuando** se listan, **entonces** se devuelven solo las de ese conductor con `id`, `id_viaje`, `estado`, `vence_en`, `respuesta` y `hora_rta`.
2. **Dado** el filtro `estado` (`PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`), **cuando** se lista, **entonces** se devuelven solo las de ese estado. Un valor inválido se rechaza con `400`.
3. **Dado** una solicitud `PENDIENTE` y vigente, **cuando** el conductor la acepta o la rechaza, **entonces** queda en el estado correspondiente con `respuesta` y con la `hora_rta` que envió el cliente, guardada tal cual. Si la acepta, el conductor pasa a `OCUPADO` en el mismo paso y `actualizado` toma la hora del cambio; si la rechaza, su estado no cambia.
4. **Dado** una solicitud cuya fecha `vence_en` ya pasó según la hora del servidor, **cuando** se intenta responder (aunque la `hora_rta` enviada sea anterior), **entonces** se responde `410` y no cambia.
5. **Dado** una solicitud ya respondida, **cuando** se intenta responder de nuevo, **entonces** se responde `409` y no cambia.
6. **Dado** un conductor no `APROBADA`, sin vehículo activo `APROBADA`, `DESCONECTADO` u `OCUPADO`, **cuando** intenta aceptar, **entonces** se responde `422` con `CONDUCTOR_NO_HABILITADO` y no cambia nada.
7. **Dado** una solicitud inexistente, **cuando** se intenta responder, **entonces** se responde `404`. Si es de otro conductor y quien responde es un conductor, se responde `403` (ver Historia 8).
8. **Dado** dos respuestas simultáneas a la misma solicitud, **cuando** llegan a la vez, **entonces** solo una se registra y la otra recibe `409`.
9. **Dado** un conductor `OCUPADO` por haber aceptado una solicitud, **cuando** pide `DISPONIBLE` con `PATCH /conductores/{id}/estado` y cumple las reglas, **entonces** queda disponible (Historia 2).
10. **Dado** que una aceptación y un cambio de estado del mismo conductor llegan a la vez, **cuando** se procesan, **entonces** ninguno se pierde y el estado final es coherente.

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

Se listan conductores filtrando por estado, tipo de servicio y por ubicación, y las respuestas incluyen el puntaje y el vehículo activo.

**Por qué esta prioridad**: M4 usa este listado para buscar conductores; hoy el filtro por tipo de servicio se ignora y faltan los datos de puntaje y vehículo activo. La búsqueda por cercanía la resuelve M4 con las coordenadas que M3 presenta.

**Prueba independiente**: Se prueba con conductores en distintas ubicaciones y con distintos tipos de servicio habilitados.

**Escenarios de aceptación**:

1. **Dado** conductores con distintos tipos de servicio habilitados, **cuando** se filtra por `tipo_servicio`, **entonces** se devuelven solo los que tienen ese tipo habilitado en su vehículo.
2. **Dado** conductores con ubicación, **cuando** se lista, **entonces** cada uno incluye sus coordenadas y la fecha de su ubicación (nulas si no hay), y el orden del listado no depende de ninguna coordenada.
3. **Dado** que se envían `latitud` y `longitud` en el listado, **cuando** se lista, **entonces** se aceptan y no cambian el resultado ni el orden. Un valor fuera de rango se rechaza con `400`.
4. **Dado** que se combinan filtros, **cuando** se lista, **entonces** se aplican todos a la vez (`habilitado`, `estado`, `tipo_vehiculo`, `tipo_servicio`).
5. **Dado** el filtro `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE` u `OCUPADO`), **cuando** se lista, **entonces** se devuelven solo los conductores en ese estado. Un valor inválido se rechaza con `400`.
6. **Dado** cualquier conductor devuelto por el listado o por la consulta individual, **cuando** se lee, **entonces** incluye `estado`, `puntaje_promedio`, `cantidad_calificaciones` e `id_vehiculo_activo`.
7. **Dado** un conductor sin calificaciones, **cuando** se consulta, **entonces** `puntaje_promedio` es `null` y `cantidad_calificaciones` es `0`.

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

- Conductor sin vehículo activo que pide `DISPONIBLE`: se rechaza.
- Cambio de `id_vehiculo_activo` a un vehículo que no es del conductor o que no existe: se rechaza.
- Conductor suspendido mientras está disponible: el estado no se cambia solo; las reglas se aplican cuando alguien intenta volver a marcarlo `DISPONIBLE` (ver Supuestos).
- Conductor `OCUPADO` que intenta aceptar otra solicitud: se rechaza con `422`.
- Dos operaciones simultáneas sobre el mismo conductor (un cambio de estado y la aceptación de una solicitud): ninguna se pierde y el resultado es coherente.
- Un token `servicio` sin ningún otro rol y un token con varios roles: se permite lo que cada rol permita.
- Listado sin resultados: lista vacía, no error.
- Un conductor que consulta el estado o la ubicación de otro conductor (aunque sean lecturas que M4 sí puede hacer): `403`.
- Todos los errores usan el formato `{codigo, mensaje}` del catálogo, ampliado con los códigos nuevos.

## Requisitos *(obligatorio)*

### Requisitos Funcionales

- **FR-020**: El sistema DEBE aceptar tokens con el rol `servicio` y permitirle leer conductores, vehículos, su estado y su ubicación, pero no ejecutar acciones de operador ni actualizar estados o solicitudes (`403`).
- **FR-021**: El sistema DEBE exponer el estado vigente de un conductor (`estado`, `id_vehiculo_activo`, `actualizado`) sin datos de ubicación. `estado` es uno de `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` u `OCUPADO`.
- **FR-022**: El sistema DEBE exponer la última ubicación (`latitud`, `longitud`, `fecha_act_ubic`) y responder `200` con los tres campos en `null` si no hay ninguna, sin devolver nunca `0,0`.
- **FR-023**: El sistema DEBE permitir al conductor o al operador actualizar el estado (`DESCONECTADO`, `CONECTADO` o `DISPONIBLE`), el vehículo activo y la ubicación, con al menos un campo. `latitud` y `longitud` DEBEN venir juntas y, si vienen, `fecha_act_ubic` DEBE ser la hora del servidor. Si el conductor no tiene ubicación y pasa de `DESCONECTADO` a otro estado sin informarla, el sistema DEBE asignarle una ubicación simulada fija una sola vez; si ya tiene ubicación, una actualización sin ubicación NO DEBE cambiarla. Pedir `OCUPADO` DEBE responder `400`.
- **FR-024**: Un conductor DEBE poder quedar `DISPONIBLE` solo si tiene habilitación `APROBADA` y su vehículo activo también está `APROBADA`; si no, el sistema DEBE responder `422` con `CONDUCTOR_NO_HABILITADO` sin cambiar nada. Pedir `DISPONIBLE` estando `DESCONECTADO` DEBE conectarlo, y estando `OCUPADO` DEBE liberarlo. Un conductor `DISPONIBLE` al que se le quita el vehículo activo o se lo cambia a uno no `APROBADA` DEBE pasar a `CONECTADO`.
- **FR-025**: `actualizado` DEBE cambiar con cada cambio de estado o de vehículo activo, y NO DEBE cambiar al actualizar solo la ubicación.
- **FR-026**: *(Retirado con el contrato 1.2.0: recibir cambios de disponibilidad de M4.)*
- **FR-027**: *(Retirado con el contrato 1.2.0: recibir viajes finalizados de M6.)*
- **FR-028**: *(Retirado con el contrato 1.2.0: idempotencia del viaje finalizado.)*
- **FR-029**: `puntaje_promedio` DEBE ser `null` mientras `cantidad_calificaciones` sea 0, y estar entre 1 y 5 en otro caso. Ambos campos DEBEN aparecer en las respuestas de conductor y calcularse desde los totales guardados. Ningún endpoint los modifica en esta iteración.
- **FR-030**: El sistema DEBE listar las solicitudes de un conductor con filtro opcional por `estado`.
- **FR-031**: El sistema DEBE permitir aceptar o rechazar una solicitud `PENDIENTE` y vigente, registrando `respuesta` y `hora_rta`. Aceptar DEBE dejar al conductor `OCUPADO` en la misma operación (con `actualizado` actualizado) y exigir que esté conectado, `APROBADA` y con vehículo activo `APROBADA`, y que no esté ya `OCUPADO`; rechazar NO DEBE cambiar su estado. DEBE responder `410` si la oferta venció y `409` si ya fue respondida, e impedir que dos respuestas simultáneas se registren ambas.
- **FR-032**: El sistema DEBE devolver los tipos de servicio de un vehículo con su estado `habilitado`, y `404` si el vehículo no es del conductor.
- **FR-033**: El sistema DEBE registrar documentación del vehículo (`SEGURO`, `CEDULA_VERDE`, `VTV`), calcular su estado (`VIGENTE` o `VENCIDO`) al leer y rechazar con `422` un vencimiento anterior a la emisión.
- **FR-034**: El listado de conductores DEBE soportar el filtro `tipo_servicio` y el filtro `estado`, combinables con `habilitado` y `tipo_vehiculo`. Los parámetros `latitud` y `longitud` DEBEN aceptarse (válidos en rango) y NO DEBEN filtrar ni ordenar: la búsqueda por cercanía la hace M4 con las coordenadas que M3 devuelve.
- **FR-035**: Las respuestas de conductor con ubicación DEBEN incluir `id_vehiculo_activo` (nulo si no hay).
- **FR-036**: Todas las respuestas, incluidos los errores, DEBEN cumplir `docs/contract/openapi.yaml`. El catálogo de errores DEBE ampliarse con los códigos de `410`, de estado del conductor y de solicitudes.
- **FR-037**: Los cambios de estado y de solicitudes DEBEN tolerar solicitudes simultáneas sin perder ni duplicar efectos, y cubrirse con pruebas (constitución, principio XI).
- **FR-038**: La lógica DEBE desarrollarse con TDD, manteniendo la cobertura sobre el umbral vigente de CI, y la versión de la API DEBE ser 1.2.0.
- **FR-039**: El backend DEBE definir en un documento compartido (`data-model.md`) qué datos necesita de la base, sin implementar la migración. No se consultan datos de otros módulos.
- **FR-040**: Un conductor DEBE poder acceder solo a los recursos de su propio `id_conductor` en todos los endpoints con `{id_conductor}` y al responder solicitudes; cualquier acceso a datos de otro conductor DEBE responder `403` con el código `ACCESO_PROHIBIDO`. El operador y el servicio no tienen esa restricción. El identificador del conductor DEBE tomarse del token y no de lo que envíe el cliente.
- **FR-041**: El listado de conductores (`GET /conductores`) DEBE quedar disponible solo para operador y servicio; un conductor recibe `403`.

### Entidades Clave

- **Estado del conductor**: uno de `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` u `OCUPADO`, el vehículo activo y la fecha del último cambio (`actualizado`).
- **Ubicación del conductor**: latitud, longitud y fecha de registro. Puede no existir.
- **Calificación del conductor**: totales (suma y cantidad de puntajes de 1 a 5) que forman `puntaje_promedio` y `cantidad_calificaciones`. Se leen; no hay endpoint que los escriba en esta iteración.
- **Solicitud**: oferta de viaje a un conductor, con estado (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`), fecha límite, respuesta y hora de respuesta.
- **Documento del vehículo**: seguro, cédula verde o VTV con número, entidad emisora, fechas, archivo y estado calculado.
- **Tipo de servicio del vehículo**: tipo (`PASAJEROS` o `ENVIOS`) y si está habilitado.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles

- **SC-008**: Las 17 operaciones del contrato responden conforme a él en el 100% de las pruebas de contrato (las 10 de la Iteración 1 más las 7 nuevas).
- **SC-009**: El 100% de los intentos del rol `servicio` de escribir (actualizar estado, responder solicitudes o ejecutar acciones de operador) es rechazado con `403`, y el 100% de las llamadas sin token válido recibe `401`.
- **SC-010**: *(Retirado con el contrato 1.2.0.)*
- **SC-011**: Ante dos operaciones simultáneas sobre el mismo conductor (un cambio de estado y la aceptación de una solicitud), ninguna se pierde y el estado final es coherente en el 100% de las ejecuciones.
- **SC-012**: *(Retirado con el contrato 1.2.0.)*
- **SC-013**: Una solicitud vencida o ya respondida nunca cambia al intentar responderla.
- **SC-014**: La cobertura de pruebas sobre lo implementado no baja del umbral vigente de CI.
- **SC-015**: El listado devuelve el mismo resultado, con el mismo orden, con o sin `latitud` y `longitud` en el 100% de los casos de prueba.
- **SC-016**: El 100% de los intentos de un conductor sobre datos de otro conductor es rechazado con `403`, y el 100% de los accesos a datos propios se permite.

## Dependencias con otros grupos

Se definen como interfaz; no se implementan en este spec.

| Grupo | Qué necesita Backend |
|---|---|
| Datos y seguridad | Migración que reemplaza `conectado` y `disponible` por `estado`, y suma el vehículo activo del conductor, la fecha del último cambio de estado, los puntajes (suma y cantidad), las solicitudes y la documentación del vehículo; el rol `servicio` y la cuenta técnica de M4; el identificador del conductor en el token de cada usuario conductor (coincidente con el conductor de los datos de prueba); datos de prueba para cada endpoint, incluidas solicitudes ya cargadas y conductores con puntaje |
| Testing | Pruebas de contrato y de integración de los 7 endpoints nuevos, matriz de roles y casos de concurrencia |
| Frontend | Pasar de `conectado` y `disponible` a `estado` en tipos y pantallas |

El detalle de lo que necesita de Datos y seguridad está en el [issue #36](https://github.com/FRRe-DS/2026-15-TPI/issues/36), y lo de Testing en un comentario de la [PR #31](https://github.com/FRRe-DS/2026-15-TPI/pull/31).

## Supuestos

- El stack de la Iteración 1 (FastAPI, PostgreSQL, Keycloak) no cambia.
- `docs/contract/openapi.yaml` (1.2.0) es la fuente de verdad. No se agrega ningún endpoint que no esté en él.
- El promedio es la suma de los puntajes dividida por la cantidad de calificaciones. Como ningún endpoint escribe esos totales en esta iteración, los datos de prueba los cargan directamente; de dónde vendrán en producción se define con M6 y M2.
- Una solicitud `PENDIENTE` cuya fecha `vence_en` pasó, medida con la hora del servidor, se trata como `VENCIDA` al leerla y al intentar responderla, aunque la fila no se haya actualizado.
- Cambiar la habilitación de un conductor o vehículo (por un operador) no modifica `estado` por sí solo; las reglas se aplican cuando alguien intenta marcarlo `DISPONIBLE`.
- Cambiar `id_vehiculo_activo` a un vehículo ajeno o inexistente se rechaza; `null` quita el vehículo activo y baja a `CONECTADO` a un conductor `DISPONIBLE`.
- Aceptar una solicitud exige que el conductor esté conectado (`CONECTADO` o `DISPONIBLE`), `APROBADA` y con vehículo activo `APROBADA`. Un conductor `OCUPADO` no puede aceptar otra solicitud. Esta regla es una decisión de este plan, a confirmar con el equipo.
- Pedir `DISPONIBLE` estando `DESCONECTADO` conecta y deja disponible en un solo paso. Es una decisión de este plan, a confirmar con el equipo.
- `OCUPADO` solo lo asigna M3 al aceptar una solicitud. Si M4 o M6 necesitan marcarlo o liberarlo, falta una operación de escritura que hoy no existe en el contrato; queda por acordar con ellos.
- `POST /conductores` (alta) queda permitido a cualquier rol autenticado, porque todavía no existe un `id_conductor` propio. El resto de las reglas de rol de la Iteración 1 se mantienen: las acciones de habilitación son solo del operador.
- La descripción de roles del esquema de seguridad del contrato dice que el conductor tiene "consulta de conductores y vehículos"; hay que ajustarla (cambio de contrato) para que refleje que el listado es solo de operador y servicio.
- Los tipos de servicio de un vehículo quedan habilitados al aprobar el vehículo y deshabilitados al suspenderlo o rechazarlo, porque el contrato no tiene un endpoint para habilitarlos por separado (decisión 9 de [research.md](./research.md), a confirmar con el equipo).
- Las solicitudes llegan a M3 por un mecanismo que define M5 más adelante; en esta iteración no hay un endpoint para crearlas.
- La ubicación simulada es una coordenada fija y configurable, distinta de `0,0`, que define el plan. Se asigna solo cuando un conductor sin ubicación pasa de `DESCONECTADO` a otro estado sin informarla.
- Los códigos de error nuevos se agregan al catálogo de la Iteración 1 (`specs/iteracion1/contracts/errores.md`) y se documentan en el plan.
- Requisitos no funcionales de TP1 aplicables: los mismos que en la Iteración 1 (RNF-01 a RNF-08 y RNF-20).

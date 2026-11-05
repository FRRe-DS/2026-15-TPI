# Especificación: Verificación de integración real de M3

**Rama de funcionalidad**: `001-verificacion-integracion-m3`

**Fecha**: 2026-11-01

**Estado**: Borrador

**Entrada**: Verificación automática de punta a punta de M3 con infraestructura real y módulos integrados.

## Escenarios de usuario y pruebas

### Historia 1 — Demostrar el flujo completo de habilitación (Prioridad: P1)

Como equipo, queremos comprobar el recorrido de alta de conductor, registro de licencia y vehículo, y habilitación, usando tokens reales de Keycloak y permisos por rol, para demostrar que el conductor y su vehículo quedan habilitados y que el historial es correcto.

**Por qué esta prioridad**: Es el flujo central de M3 y comprueba conjuntamente identidad, reglas de negocio, persistencia e historial.

**Prueba independiente**: Con datos exclusivos de la prueba, recorrer las operaciones de M3 desde el alta hasta las aprobaciones y consultar el estado e historial resultantes.

**Escenarios de aceptación**:

1. **Dado** un entorno limpio con Keycloak real y usuarios con roles de operador y conductor, **cuando** el operador crea un conductor, registra una licencia vigente y un vehículo, y aprueba al conductor y al vehículo, **entonces** las operaciones autorizadas responden correctamente, ambos recursos quedan aprobados y los historiales contienen las altas y aprobaciones con sus datos requeridos.
2. **Dado** un token real de conductor, **cuando** intenta realizar una acción reservada al operador, **entonces** la API deniega la acción y no cambia el estado ni agrega eventos al historial.
3. **Dado** un conductor sin licencia vigente, **cuando** se intenta aprobarlo, **entonces** la API rechaza la operación y el estado e historial permanecen sin cambios por esa solicitud.

### Historia 2 — Demostrar alta concurrente con DNI duplicado (Prioridad: P1)

Como equipo, queremos comprobar que dos altas simultáneas con el mismo DNI se resuelven de forma consistente, para evitar duplicados en producción.

**Por qué esta prioridad**: La unicidad de DNI debe resistir solicitudes concurrentes, no solo validaciones secuenciales.

**Prueba independiente**: Enviar dos solicitudes concurrentes con el mismo DNI usando datos de prueba aislados y comprobar las dos respuestas y el estado persistido.

**Escenarios de aceptación**:

1. **Dado** que no existe un conductor con el DNI elegido, **cuando** dos solicitudes de alta con ese DNI se procesan concurrentemente, **entonces** exactamente una responde `201`, la otra responde `409` con código `DNI_DUPLICADO` y existe exactamente un conductor con ese DNI.
2. **Dado** el mismo caso concurrente, **cuando** la prueba se repite en CI, **entonces** el resultado sigue cumpliendo exactamente las mismas cantidades, sin depender de un orden de ejecución accidental.

### Historia 3 — Demostrar persistencia y publicación de eventos (Prioridad: P1) — **BLOQUEADA**

> **Estado**: bloqueada hasta una decisión de cátedra. El contrato 1.2.0 no define eventos y el backend de la Iteración 2 no los incluye; además, FR-013 prohíbe introducir funcionalidades de negocio nuevas. Si se confirma que M3 debe publicar eventos, esa implementación debe ir en un spec propio de Backend. Mientras tanto, la PR 3 no se implementa. La persistencia en PostgreSQL puede verificarse por separado, sin depender de RabbitMQ.

Como equipo, queremos comprobar que los datos sobreviven al reinicio de la API y que los eventos de dominio de M3 llegan a RabbitMQ con el contrato esperado.

**Por qué esta prioridad**: La prueba debe demostrar comportamiento observable con la infraestructura real y evitar eventos que anuncien cambios que no fueron confirmados.

**Prueba independiente**: Crear datos propios, verificar el mensaje recibido en RabbitMQ, reiniciar solo la API y comprobar que los datos permanecen consultables en PostgreSQL.

**Escenarios de aceptación**:

1. **Dado** un cambio de dominio confirmado, **cuando** se observa el broker, **entonces** se recibe el evento correspondiente con el nombre, routing y contenido establecidos por el contrato acordado.
2. **Dado** que la transacción que origina un evento falla, **cuando** se consulta RabbitMQ, **entonces** no se publicó un evento que represente ese cambio fallido.
3. **Dado** un conductor o vehículo creado con datos propios, **cuando** se reinicia la API sin reiniciar PostgreSQL, **entonces** la API vuelve a consultar los mismos datos persistidos.
4. **Dado** que RabbitMQ no está disponible al generarse un cambio confirmado, **cuando** se restablece el servicio, **entonces** todos los eventos pendientes se publican al menos una vez y las entregas duplicadas se pueden reconocer y tolerar.

> Los escenarios 1, 2 y 4 no se evalúan mientras la Historia 3 siga bloqueada. El escenario 3 (persistencia tras reiniciar la API) se verifica sin RabbitMQ.

### Historia 4 — Verificar contratos con módulos vecinos (Prioridad: P2)

Como equipo, queremos verificar los puntos de integración de M3 con M1 (identidad), M4 (ubicación) y M5 (despacho), para que cualquier incompatibilidad con los contratos acordados haga fallar CI.

**Por qué esta prioridad**: Los contratos entre módulos permiten detectar incompatibilidades antes de integrar o desplegar servicios conjuntamente.

**Prueba independiente**: Ejecutar una verificación aislada por cada frontera de integración y comprobar que las peticiones, respuestas y errores cumplen su contrato.

**Escenarios de aceptación**:

1. **Dado** el contrato vigente de cada módulo vecino, **cuando** la prueba ejercita cada punto de integración de M3, **entonces** las solicitudes y respuestas observadas coinciden con los campos, tipos, estados y errores acordados.
2. **Dado** un cambio incompatible en una frontera de integración, **cuando** CI ejecuta las pruebas, **entonces** CI falla e identifica la integración que dejó de cumplir el contrato.
3. **Dado** que M1, M4 y M5 no se despliegan como parte de esta suite, **cuando** se ejecuta la verificación distribuida, **entonces** cada frontera se comprueba con un doble que respeta el contrato acordado, documentado antes de planificar.

### Historia 5 — Cubrir los 7 endpoints nuevos de la Iteración 2 (Prioridad: P1)

Como equipo de verificación, queremos cubrir con contrato e integración real los 7 endpoints que agrega la Iteración 2 —`GET .../vehiculos/{id}/tipos-servicio`, `POST .../vehiculos/{id}/documentacion`, `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`—, para demostrar que el contrato de 17 operaciones, las reglas de estado, las solicitudes, el promedio, la ubicación y los roles se comportan como se acordó.

**Por qué esta prioridad**: los 7 endpoints son la superficie nueva de M3 y concentran las reglas de negocio y los permisos que más riesgo tienen de romperse entre módulos.

**Prueba independiente**: con datos propios del seed y tokens firmados para cada rol, ejercitar los 7 endpoints contra PostgreSQL real, validar las respuestas reales con `openapi-core` y comprobar los códigos de error del catálogo ampliado.

**Escenarios de aceptación**:

1. **Dado** el contrato de M3, **cuando** se ejecuta `backend/tests/contrato/test_openapi_ejemplos.py`, **entonces** `OPERACIONES_EN_ALCANCE` contiene las 17 operaciones y `CODIGOS_POR_ESTADO` incluye `410` y los códigos nuevos; las respuestas reales de los 7 endpoints se validan contra `docs/contract/openapi.yaml` con `openapi-core`, no solo los ejemplos.
2. **Dado** un conductor no aprobado o con vehículo activo no aprobado, **cuando** se pide `estado: DISPONIBLE` por `PATCH /conductores/{id}/estado`, **entonces** responde `422 CONDUCTOR_NO_HABILITADO`; si estaba `DESCONECTADO` y cumple las condiciones, queda `DISPONIBLE`; pedir `estado: OCUPADO` responde `400`.
3. **Dado** un conductor `DISPONIBLE`, **cuando** se quita su vehículo activo o se cambia a uno no aprobado, **entonces** baja a `CONECTADO`.
4. **Dado** un conductor `CONECTADO` o `DISPONIBLE`, **cuando** acepta una solicitud, **entonces** queda `OCUPADO`; si está `DESCONECTADO` u `OCUPADO`, responde `422`; un `PATCH /estado` y una aceptación simultáneos sobre el mismo conductor no pierden cambios.
5. **Dado** un conductor con solicitudes, **cuando** acepta o rechaza una vigente, **entonces** la respuesta es correcta; una vencida responde `410 SOLICITUD_VENCIDA`; responder dos veces responde `409 SOLICITUD_YA_RESPONDIDA`, incluso si las respuestas llegan en paralelo.
6. **Dado** el seed, **cuando** se leen `puntaje_promedio` y `cantidad_calificaciones`, **entonces** coinciden con los datos sembrados; sin calificaciones son `null` y `0`; ningún endpoint de esta historia los modifica.
7. **Dado** un conductor sin ubicación, **cuando** se consulta `GET /conductores/{id}/ubicacion`, **entonces** responde `200` con `latitud`, `longitud` y `fecha_act_ubic` en `null`, nunca `0,0`; al pasar de `DESCONECTADO` a otro estado sin ubicación, M3 asigna una ubicación simulada fija.
8. **Dado** un token con rol `servicio`, **cuando** intenta una acción de operador, `PATCH /estado` o `POST /solicitudes/{id}`, **entonces** recibe `403`; sí puede leer `/estado`, `/ubicacion` y los `GET` de conductores. Un token de conductor recibe `403` al consultar o modificar datos de otro conductor y en `GET /conductores`.

### Casos límite

- Dos altas concurrentes llegan casi al mismo tiempo y ninguna transacción debe dejar datos parciales ni dos conductores.
- La solicitud que pierde la carrera recibe `DNI_DUPLICADO`, aunque la primera solicitud todavía no haya terminado al comenzar la segunda.
- Un token está ausente, vencido, no es válido o tiene un rol insuficiente; no debe producir cambios persistidos ni eventos.
- La licencia está vencida, falta o tiene vencimiento igual a la fecha actual; el resultado respeta la regla vigente de habilitación.
- La creación del recurso se confirma pero la publicación se interrumpe, o la transacción falla después de preparar el evento. Este caso solo aplica si se desbloquea la publicación de eventos.
- La API se reinicia mientras PostgreSQL conserva los datos; la inicialización de la API no debe borrar ni duplicar los datos de prueba.
- Un punto de integración responde con campos, tipos, estado o error incompatibles con el contrato.
- Las pruebas corren en cualquier orden y no leen ni modifican datos creados por otras pruebas.
- El conductor no está `APROBADA`, no tiene vehículo activo o el vehículo activo no está `APROBADA`; el `PATCH` a `DISPONIBLE` responde `422 CONDUCTOR_NO_HABILITADO` sin cambiar el estado.
- Se pide `estado: OCUPADO` por `PATCH /conductores/{id}/estado`; responde `400` porque `OCUPADO` lo asigna solo M3 al aceptar una solicitud.
- Se quita el vehículo activo o se cambia por uno no aprobado mientras el conductor está `DISPONIBLE`; baja a `CONECTADO` y no queda una combinación imposible.
- Una solicitud vence exactamente en el límite de `vence_en`; responder hasta esa hora inclusive es válido. Después responde `410 SOLICITUD_VENCIDA`.
- Dos respuestas de la misma solicitud llegan en paralelo; una gana y la otra recibe `409 SOLICITUD_YA_RESPONDIDA`, sin dobles transiciones.
- Un `PATCH /estado` y una aceptación de solicitud se ejecutan a la vez sobre el mismo conductor; el bloqueo de fila evita perder cambios.
- `puntaje_promedio` y `cantidad_calificaciones` se leen de datos del seed; sin calificaciones son `null` y `0`, y ningún endpoint de esta historia los escribe.
- La ubicación no registrada se devuelve como tres campos `null`, nunca como `0,0`; al pasar de `DESCONECTADO` a otro estado sin coordenadas se usa una ubicación simulada fija.
- Un token `servicio` intenta escribir o un conductor intenta operar sobre otro conductor; ambos reciben `403` y no se modifica ningún dato.
- La migración `0002` reemplaza `conectado` y `disponible` por `estado`; los tests que usan las columnas anteriores deben ajustarse cuando llegue esa migración.
- El contrato declara `410` pero `CODIGOS_POR_ESTADO` no lo incluye; la verificación de contrato debe fallar hasta completar el catálogo.

## Requisitos

### Requisitos funcionales

- **FR-001**: La suite DEBE demostrar el flujo de alta de conductor, registro de licencia vigente, alta de vehículo y aprobación del conductor y del vehículo.
- **FR-002**: La suite DEBE obtener tokens de un servicio Keycloak real y demostrar tanto el acceso autorizado del rol operador como la denegación de una acción de operador a un token de conductor.
- **FR-003**: La suite DEBE comprobar que la aprobación del conductor sin licencia vigente falla sin modificar el estado ni el historial.
- **FR-004**: La prueba concurrente DEBE enviar dos altas del mismo DNI en concurrencia y comprobar exactamente una respuesta `201`, una respuesta `409` con `DNI_DUPLICADO` y una sola fila de conductor.
- **FR-005**: El resultado de la prueba concurrente DEBE ser determinista y repetible, sin depender de pausas arbitrarias ni del orden casual de planificación.
- **FR-006**: La suite DEBE verificar con PostgreSQL real que los datos creados siguen disponibles después de reiniciar la API sin reiniciar la base de datos.
- **FR-007 (condicionado, bloqueado)**: Si la cátedra confirma que M3 debe publicar eventos de dominio, la funcionalidad DEBE incluirla en un spec propio de Backend. M3 DEBE publicar altas y cambios de estado de conductor y vehículo (incluidas aprobaciones, observaciones, rechazos y suspensiones), y NO DEBE consumir eventos de otros módulos. Los nombres, exchange, routing keys y formato DEBEN acordarse con el grupo y documentarse antes de implementar. Mientras FR-013 siga vigente y la decisión esté pendiente, esta obligación no se implementa.
- **FR-008 (condicionado, bloqueado)**: Si se implementa la publicación, un cambio de dominio cuya transacción falla NO DEBE publicar un evento que lo represente.
- **FR-009 (condicionado, bloqueado)**: Si se implementa la publicación, la suite DEBE verificar la recepción y contenido de los eventos acordados en un RabbitMQ real, ejecutable automáticamente en CI sin intervención manual. Todo evento correspondiente a un cambio confirmado DEBE conservarse y publicarse tras una caída del broker; se permite entrega al menos una vez y se DEBE definir y verificar la tolerancia a duplicados.
- **FR-010**: La suite DEBE probar cada punto de integración acordado con M1, M4 y M5 usando dobles que respetan los contratos. Una incompatibilidad de contrato DEBE hacer fallar CI. Antes de planificar, se DEBEN documentar los contratos para: M1, tokens JWT bearer y roles, incluido el rol `servicio` de solo lectura; M4, `GET /conductores`, `GET /conductores/{id_conductor}`, `GET /conductores/{id_conductor}/estado` y `GET /conductores/{id_conductor}/ubicacion`, con `estado` (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`) y ubicación, en solo lectura; M5, `GET /conductores/{id_conductor}/solicitudes` y `POST /solicitudes/{id_solicitud}` (Iteración 2, todavía no existen en `dev`).
- **FR-011**: Cada prueba DEBE preparar datos propios y no depender del orden, del estado residual ni de los datos creados por otra prueba.
- **FR-012**: Las pruebas de esta funcionalidad DEBEN ejecutarse automáticamente en CI y fallar si una infraestructura o verificación requerida no está disponible; no se consideran demostración las pruebas omitidas o ejecutadas manualmente.
- **FR-013**: La verificación DEBE respetar el alcance de M3 y no introducir funcionalidades de negocio nuevas ni pruebas de la interfaz web.
- **FR-014**: La suite de contrato DEBE ampliar `backend/tests/contrato/test_openapi_ejemplos.py` de 10 a 17 operaciones en `OPERACIONES_EN_ALCANCE`, agregar `410` y los códigos nuevos (`ACCESO_PROHIBIDO`, `SOLICITUD_YA_RESPONDIDA`, `SOLICITUD_VENCIDA`, `CONDUCTOR_NO_HABILITADO`) a `CODIGOS_POR_ESTADO` y validar las respuestas reales de los 7 endpoints contra `docs/contract/openapi.yaml` con `openapi-core`, no solo los ejemplos.
- **FR-015**: La suite DEBE verificar contra PostgreSQL real que `estado: DISPONIBLE` responde `422 CONDUCTOR_NO_HABILITADO` si el conductor no está aprobado o su vehículo activo no está aprobado; que desde `DESCONECTADO` y cumpliendo las condiciones queda `DISPONIBLE`; y que `estado: OCUPADO` responde `400`.
- **FR-016**: La suite DEBE verificar que quitar el vehículo activo o cambiarlo por uno no aprobado baja al conductor de `DISPONIBLE` a `CONECTADO`.
- **FR-017**: La suite DEBE verificar que aceptar una solicitud deja `OCUPADO` a un conductor `CONECTADO` o `DISPONIBLE`, que `DESCONECTADO` u `OCUPADO` responde `422`, y que un `PATCH /conductores/{id}/estado` concurrente con la aceptación de una solicitud sobre el mismo conductor no pierde cambios.
- **FR-018**: La suite DEBE verificar que aceptar o rechazar una solicitud vigente funciona, que una vencida responde `410 SOLICITUD_VENCIDA`, que responder dos veces responde `409 SOLICITUD_YA_RESPONDIDA` y que el resultado se mantiene si las respuestas llegan en paralelo.
- **FR-019**: La suite DEBE verificar que `puntaje_promedio` y `cantidad_calificaciones` se leen correctamente desde los datos del seed, que sin calificaciones son `null` y `0` y que ningún endpoint de esta historia los modifica.
- **FR-020**: La suite DEBE verificar que `GET /conductores/{id}/ubicacion` responde `200` con los tres campos en `null` cuando no hay ubicación, nunca `0,0`, y que al pasar de `DESCONECTADO` a otro estado sin ubicación M3 asigna una ubicación simulada fija.
- **FR-021**: La suite DEBE verificar que el rol `servicio` recibe `403` en las acciones de operador, en `PATCH /conductores/{id}/estado` y en `POST /solicitudes/{id}`, y que puede leer `/estado`, `/ubicacion` y los `GET` de conductores; que un conductor recibe `403` al consultar o modificar datos de otro conductor y en `GET /conductores`.
- **FR-022**: La suite DEBE incorporar un helper para firmar tokens con rol `servicio`, equivalente a los helpers existentes de conductor y operador, con la lista de roles y los claims `id_conductor`/`id_operador` según el caso. La cuenta técnica de servicio la define el grupo de Datos y seguridad.
- **FR-023**: Las pruebas de los 7 endpoints DEBEN ejecutarse después de la migración `0002` y del backend de la Iteración 2; los tests existentes que miran `conectado` y `disponible` DEBEN pasar a mirar `estado`. La cobertura DEBE subir del umbral vigente de `65 %` a `70 %` para la Iteración 2 y las pruebas nuevas de contrato e integración DEBEN ejecutarse en el job `integracion-real-m3`.

### Entidades clave

- **Conductor**: Persona registrada por M3, identificada por un DNI único, con documentos, vehículos, estado de habilitación y estado operativo (`DESCONECTADO`, `CONECTADO`, `DISPONIBLE`, `OCUPADO`).
- **Licencia**: Documento del conductor cuya vigencia condiciona la aprobación.
- **Vehículo**: Vehículo asociado a un conductor, con su propio estado e historial de habilitación, tipos de servicio habilitados y documentos.
- **Solicitud**: Oferta de viaje de M5 con estado `PENDIENTE`, `ACEPTADO`, `RECHAZADO` o `VENCIDA`, vencimiento `vence_en` y respuesta asociada; aceptar una solicitud puede dejar al conductor `OCUPADO`.
- **Ubicación**: Última posición registrada del conductor (`latitud`, `longitud`, `fecha_act_ubic`); los tres campos pueden ser `null` y `null` significa desconocida, nunca `(0, 0)`.
- **Calificación y promedio**: Totales de calificaciones del conductor; `puntaje_promedio` se deriva de `suma_puntajes` y `cantidad_calificaciones`, es `null` sin calificaciones y es de solo lectura desde los endpoints de esta historia.
- **Catálogo de errores**: Acuerdo verificable de códigos por estado HTTP, ampliado para la Iteración 2 con `410 SOLICITUD_VENCIDA`, `409 SOLICITUD_YA_RESPONDIDA`, `422 CONDUCTOR_NO_HABILITADO` y `403 ACCESO_PROHIBIDO`.
- **Evento de dominio**: Notificación de un cambio de M3 que solo puede anunciar un cambio confirmado; su implementación está bloqueada hasta la decisión sobre FR-007 y no forma parte del contrato 1.2.0.
- **Contrato de integración**: Acuerdo verificable de los mensajes, operaciones, datos y errores intercambiados entre M3 y un módulo vecino.

## Criterios de éxito

### Resultados medibles

- **SC-001**: En CI, el flujo completo termina con el conductor y el vehículo aprobados y con el historial esperado, usando tokens emitidos por Keycloak y permisos por rol.
- **SC-002**: En cada ejecución de CI, la prueba concurrente obtiene exactamente una respuesta `201`, una `409 DNI_DUPLICADO` y una sola fila para el DNI probado.
- **SC-003**: En CI, los datos creados antes del reinicio de la API siguen consultables después de reiniciarla. Si se confirma la publicación de eventos, cada evento esperado se recibe de RabbitMQ con el contenido del contrato; mientras la decisión esté pendiente, esta parte no se evalúa.
- **SC-004**: Si se implementa la publicación, en CI ninguna transacción fallida genera un evento observable que la represente. Mientras la decisión esté pendiente, no se evalúa.
- **SC-005**: Si se implementa la publicación, tras una interrupción de RabbitMQ todos los eventos de transacciones confirmadas se reciben al restablecerse el broker, con duplicados tolerados según el contrato. Mientras la decisión esté pendiente, no se evalúa.
- **SC-006**: CI ejecuta una verificación automatizada para cada frontera acordada con M1, M4 y M5 y reporta como fallo todo desvío de contrato.
- **SC-007**: Cada prueba puede ejecutarse de forma aislada y en cualquier orden, sin compartir registros de negocio ni depender de intervención manual.
- **SC-008**: En CI, el contrato enumera 17 operaciones, `CODIGOS_POR_ESTADO` incluye `410` y los códigos nuevos, y las respuestas reales de los 7 endpoints validan contra el YAML con `openapi-core`.
- **SC-009**: En PostgreSQL real, los casos de `DISPONIBLE`, `OCUPADO`, vehículo activo y aceptación de solicitud producen exactamente los estados y códigos acordados; el `PATCH` concurrente y la aceptación simultánea no pierden cambios.
- **SC-010**: Una solicitud vigente se acepta o rechaza; una vencida da `410 SOLICITUD_VENCIDA`; una segunda respuesta da `409 SOLICITUD_YA_RESPONDIDA`, también en paralelo.
- **SC-011**: El promedio y la cantidad de calificaciones coinciden con el seed, sin calificaciones son `null` y `0`, y ningún endpoint los modifica.
- **SC-012**: La ubicación ausente se lee como tres campos `null` y nunca `0,0`; el paso de `DESCONECTADO` a otro estado sin ubicación asigna la ubicación simulada fija.
- **SC-013**: Un token `servicio` solo puede leer y recibe `403` en toda escritura; un conductor recibe `403` sobre datos de otro conductor y en `GET /conductores`. El helper de token `servicio` existe y se usa en las pruebas.
- **SC-014**: Las pruebas nuevas de contrato e integración corren en el job `integracion-real-m3` y la cobertura de la Iteración 2 alcanza el `70 %` propuesto.

## Supuestos

- La API M3 conserva sus contratos REST y reglas de negocio existentes; esta funcionalidad añade verificaciones. La publicación de eventos solo se implementaría si la cátedra confirma que corresponde a M3, en un spec propio de Backend; no se agrega dentro de esta feature.
- Los servicios de PostgreSQL y Keycloak usados para demostrar el comportamiento son instancias reales de esos productos, efímeras y controladas por las pruebas/CI. RabbitMQ solo se suma si se desbloquea la publicación de eventos.
- El Compose actual contiene PostgreSQL, Keycloak, migraciones, seed y API; no incluye RabbitMQ. Si se desbloquea la publicación, la infraestructura de prueba deberá proveer el broker real sin exigir operación manual.
- Los contratos de las fronteras con M1, M4 y M5 se verificarán con dobles, no con instancias de esos módulos. El contrato de JWT/roles y las operaciones M4 y M5 enumeradas en FR-010 se documentarán antes de planificar.
- M3 no implementa clientes HTTP salientes hacia módulos vecinos en la Iteración 2. Las operaciones de M6 se retiraron del contrato de M3 y M6 no escribe en M3, por lo que M6 no forma parte de las fronteras a verificar.
- El historial de habilitación de M3 ya registra eventos de dominio en PostgreSQL; esto no demuestra por sí solo su publicación en un broker.
- CI dispone de Docker para ejecutar pruebas de integración; las pruebas requeridas por esta especificación no pueden marcarse como omitidas para obtener un resultado exitoso.
- Los 7 endpoints nuevos pertenecen a la Iteración 2 y dependen de la migración `0002` (que reemplaza `conectado`/`disponible` por `estado`) y del backend de esa iteración. Sus pruebas se ejecutan después de esas dependencias; los tests que usen las columnas anteriores se ajustan cuando llegue la migración.
- Si la cátedra confirma que M3 debe publicar eventos, esa funcionalidad se especifica e implementa en un trabajo propio de Backend. Mientras no se confirme, la Historia 3, FR-007 a FR-009 y la PR 3 quedan bloqueadas y no se implementan dentro de esta feature.
- Las PR 1 (flujo de habilitación) y PR 2 (alta concurrente con DNI duplicado) corren sobre endpoints existentes y pueden avanzar sin esperar la migración `0002` ni los 7 endpoints nuevos.
- La PR 4 se limita a lo que M3 expone: lecturas de M4 (`GET /conductores`, detalle, `/estado` y `/ubicacion`) y solicitudes de M5 (`GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`). No hay clientes HTTP salientes hacia M4 ni M6 y no se prueban escrituras de esos módulos contra M3.
- Para las lecturas con rol `servicio`, los dobles son tokens firmados con ese rol; la cuenta técnica de servicio la define el grupo de Datos y seguridad. No se crean endpoints de escritura para M4/M6.
- El umbral de cobertura vigente es `65 %` en `ci.yml`; para la Iteración 2 se propone `70 %`. Las pruebas nuevas de contrato e integración se incorporan al job `integracion-real-m3`.

## Fuera de alcance

- Cambios a reglas de negocio o nuevas capacidades funcionales no necesarias para la verificación descrita.
- Implementar eventos de dominio mientras la decisión sobre FR-007/FR-013 siga pendiente; si se confirma, va en un spec propio de Backend.
- Implementar clientes HTTP salientes de M3 hacia M4 o M6 y probar escrituras de M4/M6 contra M3: el contrato 1.2.0 no tiene esas operaciones.
- Pruebas de la interfaz web, cubiertas por E2.
- Despliegue productivo, monitoreo operativo y pruebas de rendimiento.

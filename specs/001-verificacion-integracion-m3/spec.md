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

### Historia 3 — Demostrar persistencia y publicación de eventos (Prioridad: P1)

Como equipo, queremos comprobar que los datos sobreviven al reinicio de la API y que los eventos de dominio de M3 llegan a RabbitMQ con el contrato esperado.

**Por qué esta prioridad**: La prueba debe demostrar comportamiento observable con la infraestructura real y evitar eventos que anuncien cambios que no fueron confirmados.

**Prueba independiente**: Crear datos propios, verificar el mensaje recibido en RabbitMQ, reiniciar solo la API y comprobar que los datos permanecen consultables en PostgreSQL.

**Escenarios de aceptación**:

1. **Dado** un cambio de dominio confirmado, **cuando** se observa el broker, **entonces** se recibe el evento correspondiente con el nombre, routing y contenido establecidos por el contrato acordado.
2. **Dado** que la transacción que origina un evento falla, **cuando** se consulta RabbitMQ, **entonces** no se publicó un evento que represente ese cambio fallido.
3. **Dado** un conductor o vehículo creado con datos propios, **cuando** se reinicia la API sin reiniciar PostgreSQL, **entonces** la API vuelve a consultar los mismos datos persistidos.
4. **Dado** que RabbitMQ no está disponible al generarse un cambio confirmado, **cuando** se restablece el servicio, **entonces** todos los eventos pendientes se publican al menos una vez y las entregas duplicadas se pueden reconocer y tolerar.

### Historia 4 — Verificar contratos con módulos vecinos (Prioridad: P2)

Como equipo, queremos verificar los puntos de integración de M3 con M1 (identidad), M4 (ubicación), M5 (despacho) y M6 (viajes), para que cualquier incompatibilidad con los contratos acordados haga fallar CI.

**Por qué esta prioridad**: Los contratos entre módulos permiten detectar incompatibilidades antes de integrar o desplegar servicios conjuntamente.

**Prueba independiente**: Ejecutar una verificación aislada por cada frontera de integración y comprobar que las peticiones, respuestas, eventos y errores cumplen su contrato.

**Escenarios de aceptación**:

1. **Dado** el contrato vigente de cada módulo vecino, **cuando** la prueba ejercita cada punto de integración de M3, **entonces** las solicitudes y respuestas observadas coinciden con los campos, tipos, estados y errores acordados.
2. **Dado** un cambio incompatible en una frontera de integración, **cuando** CI ejecuta las pruebas, **entonces** CI falla e identifica la integración que dejó de cumplir el contrato.
3. **Dado** que M1, M4, M5 y M6 no se despliegan como parte de esta suite, **cuando** se ejecuta la verificación distribuida, **entonces** cada frontera se comprueba con un doble que respeta el contrato acordado, documentado antes de planificar.

### Casos límite

- Dos altas concurrentes llegan casi al mismo tiempo y ninguna transacción debe dejar datos parciales ni dos conductores.
- La solicitud que pierde la carrera recibe `DNI_DUPLICADO`, aunque la primera solicitud todavía no haya terminado al comenzar la segunda.
- Un token está ausente, vencido, no es válido o tiene un rol insuficiente; no debe producir cambios persistidos ni eventos.
- La licencia está vencida, falta o tiene vencimiento igual a la fecha actual; el resultado respeta la regla vigente de habilitación.
- La creación del recurso se confirma pero la publicación se interrumpe, o la transacción falla después de preparar el evento.
- La API se reinicia mientras PostgreSQL conserva los datos; la inicialización de la API no debe borrar ni duplicar los datos de prueba.
- Un punto de integración responde con campos, tipos, estado o error incompatibles con el contrato.
- Las pruebas corren en cualquier orden y no leen ni modifican datos creados por otras pruebas.

## Requisitos

### Requisitos funcionales

- **FR-001**: La suite DEBE demostrar el flujo de alta de conductor, registro de licencia vigente, alta de vehículo y aprobación del conductor y del vehículo.
- **FR-002**: La suite DEBE obtener tokens de un servicio Keycloak real y demostrar tanto el acceso autorizado del rol operador como la denegación de una acción de operador a un token de conductor.
- **FR-003**: La suite DEBE comprobar que la aprobación del conductor sin licencia vigente falla sin modificar el estado ni el historial.
- **FR-004**: La prueba concurrente DEBE enviar dos altas del mismo DNI en concurrencia y comprobar exactamente una respuesta `201`, una respuesta `409` con `DNI_DUPLICADO` y una sola fila de conductor.
- **FR-005**: El resultado de la prueba concurrente DEBE ser determinista y repetible, sin depender de pausas arbitrarias ni del orden casual de planificación.
- **FR-006**: La suite DEBE verificar con PostgreSQL real que los datos creados siguen disponibles después de reiniciar la API sin reiniciar la base de datos.
- **FR-007**: Si la publicación de eventos de dominio de M3 no existe, la funcionalidad DEBE incluirla. M3 DEBE publicar altas y cambios de estado de conductor y vehículo (incluidas aprobaciones, observaciones, rechazos y suspensiones), y NO DEBE consumir eventos de otros módulos. Los nombres, exchange, routing keys y formato DEBEN acordarse con el grupo y documentarse antes de planificar.
- **FR-008**: Un cambio de dominio cuya transacción falla NO DEBE publicar un evento que lo represente.
- **FR-009**: La suite DEBE verificar la recepción y contenido de los eventos acordados en un RabbitMQ real, ejecutable automáticamente en CI sin intervención manual. Todo evento correspondiente a un cambio confirmado DEBE conservarse y publicarse tras una caída del broker; se permite entrega al menos una vez y se DEBE definir y verificar la tolerancia a duplicados.
- **FR-010**: La suite DEBE probar cada punto de integración acordado con M1, M4, M5 y M6 usando dobles que respetan los contratos. Una incompatibilidad de contrato DEBE hacer fallar CI. Antes de planificar, se DEBEN documentar los contratos para: M1, tokens JWT bearer y roles; M4, `GET /conductores` y `GET /conductores/{id_conductor}` con disponibilidad y ubicación; M5, `GET /conductores/{id_conductor}/solicitudes` y `POST /solicitudes/{id_solicitud}`; M6, `GET /viajes/{id_viaje}`, `POST /viajes/{id_viaje}/finalizar` y `POST /viajes/{id_viaje}/cancelar`.
- **FR-011**: Cada prueba DEBE preparar datos propios y no depender del orden, del estado residual ni de los datos creados por otra prueba.
- **FR-012**: Las pruebas de esta funcionalidad DEBEN ejecutarse automáticamente en CI y fallar si una infraestructura o verificación requerida no está disponible; no se consideran demostración las pruebas omitidas o ejecutadas manualmente.
- **FR-013**: La verificación DEBE respetar el alcance de M3 y no introducir funcionalidades de negocio nuevas ni pruebas de la interfaz web.

### Entidades clave

- **Conductor**: Persona registrada por M3, identificada por un DNI único, con documentos, vehículos y estado de habilitación.
- **Licencia**: Documento del conductor cuya vigencia condiciona la aprobación.
- **Vehículo**: Vehículo asociado a un conductor, con su propio estado e historial de habilitación.
- **Evento de dominio**: Notificación de un cambio de M3 que solo puede anunciar un cambio confirmado; sus nombres y esquema dependen del contrato por acordar.
- **Contrato de integración**: Acuerdo verificable de los mensajes, operaciones, datos y errores intercambiados entre M3 y un módulo vecino.

## Criterios de éxito

### Resultados medibles

- **SC-001**: En CI, el flujo completo termina con el conductor y el vehículo aprobados y con el historial esperado, usando tokens emitidos por Keycloak y permisos por rol.
- **SC-002**: En cada ejecución de CI, la prueba concurrente obtiene exactamente una respuesta `201`, una `409 DNI_DUPLICADO` y una sola fila para el DNI probado.
- **SC-003**: En CI, los datos creados antes del reinicio de la API siguen consultables después de reiniciarla, y cada evento esperado se recibe de RabbitMQ con el contenido del contrato.
- **SC-004**: En CI, ninguna transacción fallida genera un evento observable que la represente.
- **SC-005**: Tras una interrupción de RabbitMQ, todos los eventos de transacciones confirmadas se reciben al restablecerse el broker, con duplicados tolerados según el contrato.
- **SC-006**: CI ejecuta una verificación automatizada para cada frontera acordada con M1, M4, M5 y M6 y reporta como fallo todo desvío de contrato.
- **SC-007**: Cada prueba puede ejecutarse de forma aislada y en cualquier orden, sin compartir registros de negocio ni depender de intervención manual.

## Supuestos

- La API M3 conserva sus contratos REST y reglas de negocio existentes; esta funcionalidad añade verificaciones e implementa solo el comportamiento de publicación de eventos que falte.
- Los servicios de PostgreSQL, Keycloak y RabbitMQ usados para demostrar el comportamiento son instancias reales de esos productos, efímeras y controladas por las pruebas/CI.
- El Compose actual contiene PostgreSQL, Keycloak, migraciones, seed y API; no incluye RabbitMQ. La infraestructura de prueba deberá proveer el broker real sin exigir operación manual.
- Los contratos de las fronteras con M1, M4, M5 y M6 se verificarán con dobles, no con instancias de esos módulos. El contrato de JWT/roles y las operaciones M4, M5 y M6 enumeradas en FR-010 se documentarán antes de planificar.
- El historial de habilitación de M3 ya registra eventos de dominio en PostgreSQL; esto no demuestra por sí solo su publicación en un broker.
- CI dispone de Docker para ejecutar pruebas de integración; las pruebas requeridas por esta especificación no pueden marcarse como omitidas para obtener un resultado exitoso.

## Fuera de alcance

- Cambios a reglas de negocio o nuevas capacidades funcionales no necesarias para publicar los eventos acordados.
- Pruebas de la interfaz web, cubiertas por E2.
- Despliegue productivo, monitoreo operativo y pruebas de rendimiento.

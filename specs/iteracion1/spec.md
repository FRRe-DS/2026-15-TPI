# Especificación de la Funcionalidad: Iteración 1 — Base de M3 (Conductores y Vehículos)

**Rama de la Funcionalidad**: `docs/planificacion-iteracion1`

**Creada**: 2026-10-22

**Estado**: Borrador

**Entrada**: Iteración 1 (TP1) del Módulo 3. Dejar una base funcional, testeada y ejecutable, dividida en cuatro grupos de trabajo en paralelo, que cubra 10 de los 16 endpoints propios de `docs/contract/openapi.yaml`.

## Clarificaciones

### Sesión 2026-10-22

- Q: ¿Qué cambios de estado de habilitación se permiten al aplicar una acción sobre un conductor o un vehículo? → A: Matriz fija: `PENDIENTE` → `APROBADA`, `OBSERVADA` o `RECHAZADA`; `OBSERVADA` → `APROBADA` o `RECHAZADA`; `APROBADA` → `SUSPENDIDA`; `SUSPENDIDA` → `APROBADA` o `RECHAZADA`; `RECHAZADA` es final. Cualquier otra transición devuelve `409`.
- Q: ¿De dónde sale el número que se guarda como `id_operador` al aplicar una acción de habilitación? → A: El usuario operador tiene un atributo numérico `id_operador` en el servicio de identidad, que viaja dentro del token; M3 lo lee de ahí y el contrato no cambia.
- Q: ¿Qué puede hacer cada tipo de usuario con los endpoints de conductores, licencia y vehículos, además de las acciones de habilitación? → A: Cualquier usuario autenticado (operador o conductor) puede usar todos los endpoints, salvo las acciones de habilitación, que son solo del operador. El acceso de cada conductor únicamente a sus propios datos queda para la Iteración 2.
- Q: ¿Qué filtros del listado de conductores se implementan en esta iteración? → A: `habilitado`, `disponible` y `tipo_vehiculo`. Los filtros por ubicación (`latitud`/`longitud`) y `tipo_servicio` quedan para la Iteración 2.
- Q: ¿Se puede aprobar la habilitación de un conductor que no tiene una licencia vigente cargada? → A: No. Aprobar a un conductor exige una licencia `VIGENTE` cargada; si no la tiene se rechaza con `422`. La regla aplica al conductor, no al vehículo.

## Alcance

**En alcance (10 endpoints):**

| # | Endpoint | Grupo del contrato |
|---|---|---|
| 1 | `POST /conductores` | Conductores |
| 2 | `GET /conductores` | Conductores |
| 3 | `GET /conductores/{id_conductor}` | Conductores |
| 4 | `GET /conductores/{id_conductor}/habilitacion` | Habilitación |
| 5 | `POST /conductores/{id_conductor}/habilitacion` | Habilitación |
| 6 | `POST /conductores/{id_conductor}/documentacion` | Documentación (licencia) |
| 7 | `POST /conductores/{id_conductor}/vehiculos` | Vehículos |
| 8 | `GET /conductores/{id_conductor}/vehiculos` | Vehículos |
| 9 | `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}` | Vehículos |
| 10 | `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion` | Habilitación |

**Fuera de alcance (Iteración 2):** acceso de cada conductor solo a sus propios datos, filtros del listado por ubicación y tipo de servicio, tipos de servicio del vehículo, documentación del vehículo, actualización de estado/disponibilidad, solicitudes, calificación del cliente, los 3 endpoints de M6 (solo consumidos), integraciones con M1/M4/M5/M6.

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia 1 - Registrar y consultar conductores (Prioridad: P1)

Un operador registra un conductor con sus datos personales y puede listar los conductores y consultar uno por su identificador.

**Por qué esta prioridad**: Todo el módulo depende de que existan conductores; es la base de las demás historias.

**Prueba independiente**: Se puede probar registrando un conductor y consultándolo por id y en el listado; entrega valor aun sin habilitación ni vehículos.

**Escenarios de aceptación**:

1. **Dado** datos válidos (DNI de 7 u 8 dígitos, nombre, apellido, teléfono y email), **cuando** se registra el conductor, **entonces** queda creado con habilitación `PENDIENTE`, desconectado y no disponible.
2. **Dado** un conductor con un DNI ya registrado, **cuando** se intenta registrar otro con el mismo DNI, **entonces** se rechaza con conflicto (`409`).
3. **Dado** datos inválidos (por ejemplo DNI con letras), **cuando** se intenta registrar, **entonces** se rechaza con error `{codigo, mensaje}`.
4. **Dado** conductores existentes, **cuando** se consulta el listado, **entonces** se devuelven todos con sus datos y estado.
5. **Dado** conductores en distintos estados, **cuando** se filtra por `habilitado`, `disponible` o `tipo_vehiculo`, **entonces** se devuelven solo los que cumplen el filtro (`habilitado=true` significa habilitación `APROBADA`).
6. **Dado** un id inexistente, **cuando** se consulta el conductor, **entonces** se responde "no encontrado" (`404`).

---

### Historia 2 - Habilitar al conductor (Prioridad: P2)

Un operador autorizado revisa a un conductor y puede aprobar, observar, suspender o rechazar su habilitación, indicando siempre el motivo; cualquiera puede consultar el estado actual y el historial.

**Por qué esta prioridad**: Un conductor sin habilitación aprobada no puede operar; es la regla de negocio central del módulo.

**Prueba independiente**: Se prueba registrando un conductor, cargándole una licencia vigente, aplicándole acciones de habilitación y verificando estado e historial.

**Escenarios de aceptación**:

1. **Dado** un conductor `PENDIENTE` con una licencia `VIGENTE` cargada, **cuando** un operador lo aprueba con un motivo, **entonces** pasa a `APROBADA` y se registra un evento con motivo, operador y fecha.
2. **Dado** un conductor sin licencia `VIGENTE` cargada (sin licencia o con la licencia `VENCIDO`), **cuando** un operador intenta aprobarlo, **entonces** se rechaza con `422` y el estado no cambia.
3. **Dado** una acción sin motivo, **cuando** se intenta aplicar, **entonces** se rechaza.
4. **Dado** una transición no permitida entre estados (por ejemplo, cualquier acción sobre un conductor `RECHAZADA`, o `OBSERVAR` sobre uno `APROBADA`), **cuando** se intenta aplicar, **entonces** se rechaza con conflicto (`409`).
5. **Dado** un conductor `APROBADA`, **cuando** un operador lo suspende con motivo y luego lo aprueba de nuevo, **entonces** ambas transiciones son válidas y quedan en el historial.
6. **Dado** un conductor con varias acciones aplicadas, **cuando** se consulta su habilitación, **entonces** se obtiene el estado actual y el historial completo en orden.

---

### Historia 3 - Cargar la licencia del conductor (Prioridad: P3)

Se registra la licencia del conductor con su número, categoría, fechas y archivo asociado.

**Por qué esta prioridad**: Es el único documento del conductor en esta iteración y respalda la decisión de habilitar.

**Prueba independiente**: Se prueba cargando una licencia a un conductor existente y verificando su estado.

**Escenarios de aceptación**:

1. **Dado** un conductor existente y una licencia con fecha de vencimiento futura, **cuando** se registra, **entonces** queda `VIGENTE`.
2. **Dado** una licencia con fecha de vencimiento pasada, **cuando** se registra, **entonces** queda `VENCIDO`.
3. **Dado** un conductor inexistente, **cuando** se intenta registrar la licencia, **entonces** se responde `404`.

---

### Historia 4 - Registrar y habilitar vehículos (Prioridad: P4)

Se registra un vehículo (auto o moto) de un conductor con al menos un tipo de servicio, se lo lista y consulta, y un operador autorizado puede habilitarlo.

**Por qué esta prioridad**: Un conductor opera con un vehículo; completa el flujo de alta de punta a punta.

**Prueba independiente**: Se prueba registrando un vehículo para un conductor existente, listándolo y aplicándole una acción de habilitación.

**Escenarios de aceptación**:

1. **Dado** un conductor existente, **cuando** se registra un vehículo válido, **entonces** queda con habilitación `PENDIENTE` y sus tipos de servicio sin habilitar.
2. **Dado** una patente ya registrada, **cuando** se intenta registrar otro vehículo con esa patente, **entonces** se rechaza con conflicto (`409`).
3. **Dado** un vehículo sin tipos de servicio, **cuando** se intenta registrar, **entonces** se rechaza.
4. **Dado** un conductor con vehículos, **cuando** se listan, **entonces** se devuelven solo los de ese conductor.
5. **Dado** un vehículo `PENDIENTE`, **cuando** un operador lo aprueba con motivo, **entonces** pasa a `APROBADA` y se registra el evento.

---

### Historia 5 - Entorno ejecutable, seguridad y datos de prueba (Prioridad: P5)

El equipo levanta la API, la base de datos y el servicio de identidad con un único comando, con una base de datos propia de M3, un servicio de identidad con usuarios y roles de prueba, y datos de prueba cargados.

**Por qué esta prioridad**: Habilita que los demás grupos trabajen en paralelo sobre un entorno común y reproducible.

**Prueba independiente**: Se prueba en una máquina limpia ejecutando el comando documentado y verificando que los servicios responden y hay datos.

**Escenarios de aceptación**:

1. **Dado** el repositorio recién clonado, **cuando** se ejecuta el comando único de arranque, **entonces** el entorno queda disponible sin pasos manuales adicionales.
2. **Dado** el entorno levantado, **cuando** se consulta el listado de conductores, **entonces** aparecen los conductores de prueba.
3. **Dado** cualquier configuración sensible, **cuando** se revisa el repositorio, **entonces** no hay credenciales ni claves versionadas.
4. **Dado** una solicitud sin token o con un token inválido, **cuando** se invoca cualquier endpoint, **entonces** se responde `401`.
5. **Dado** un usuario autenticado sin rol de operador, **cuando** intenta aplicar una acción de habilitación, **entonces** se responde `403`.
6. **Dado** un operador autenticado, **cuando** aplica una acción de habilitación, **entonces** el evento queda registrado con el `id_operador` numérico que trae su token.
7. **Dado** un usuario autenticado con rol de conductor o de operador, **cuando** registra o consulta conductores, licencias y vehículos, **entonces** la operación se permite; solo las acciones de habilitación exigen el rol de operador.
8. **Dado** un token de operador sin el atributo `id_operador`, **cuando** intenta aplicar una acción de habilitación, **entonces** se rechaza con `403`.

---

### Historia 6 - Verificación automática de calidad (Prioridad: P6)

Cada cambio propuesto se valida automáticamente: estilo, pruebas, umbral de cobertura y validez del contrato.

**Por qué esta prioridad**: Protege la calidad de las entregas paralelas y hace cumplir TDD y cobertura.

**Prueba independiente**: Se prueba abriendo un cambio de prueba y observando el resultado de la verificación.

**Escenarios de aceptación**:

1. **Dado** un cambio con pruebas en verde y cobertura suficiente, **cuando** se propone, **entonces** la verificación pasa.
2. **Dado** un cambio que baja la cobertura del umbral o rompe una prueba, **cuando** se propone, **entonces** la verificación falla y bloquea el merge.
3. **Dado** un `openapi.yaml` inválido, **cuando** se propone el cambio, **entonces** la verificación falla.
4. **Dado** los endpoints implementados, **cuando** se ejecutan las pruebas de contrato e integración contra la base real, **entonces** las respuestas coinciden con el contrato.

---

### Historia 7 - Pantalla de listado de conductores (Prioridad: P7)

Una persona abre una única pantalla que muestra el listado de conductores obtenido del servicio, como demostración de que funciona de punta a punta.

**Por qué esta prioridad**: Entrega mínima de interfaz; depende de que lo anterior esté terminado.

**Prueba independiente**: Se prueba abriendo la pantalla con el entorno levantado y verificando que lista los conductores de prueba.

**Escenarios de aceptación**:

1. **Dado** el servicio disponible, **cuando** se abre la pantalla, **entonces** se muestra el listado de conductores.
2. **Dado** el servicio no disponible, **cuando** se abre la pantalla, **entonces** se muestra un mensaje de error claro, sin fallar.
3. **Dado** que no hay conductores, **cuando** se abre la pantalla, **entonces** se muestra un estado vacío.

---

### Casos Límite

- Dos solicitudes simultáneas para registrar el mismo DNI o la misma patente: solo una se crea y la otra recibe conflicto (`409`).
- Dos acciones de habilitación simultáneas sobre el mismo conductor o vehículo: el resultado es coherente y el historial no se corrompe.
- Operar sobre un vehículo que no pertenece al conductor indicado: se responde `404`.
- Token vencido o de otro emisor: se trata como inválido (`401`).
- Listado sin resultados: se devuelve una lista vacía, no un error.
- Todos los errores usan el mismo formato `{codigo, mensaje}`.

## Requisitos *(obligatorio)*

### Requisitos Funcionales

- **FR-001**: El sistema DEBE permitir registrar un conductor con DNI (7 u 8 dígitos), nombre, apellido, teléfono y email, dejándolo con habilitación `PENDIENTE`, desconectado y no disponible.
- **FR-002**: El sistema DEBE impedir DNI y patente duplicados, incluso ante solicitudes simultáneas, respondiendo conflicto (`409`).
- **FR-003**: El sistema DEBE listar conductores, con los filtros `habilitado`, `disponible` y `tipo_vehiculo`, y consultar uno por id, informando `404` cuando no existe.
- **FR-004**: El sistema DEBE permitir aprobar, observar, suspender o rechazar a un conductor y a un vehículo, con motivo obligatorio, registrando operador y fecha.
- **FR-005**: El sistema DEBE aceptar solo las transiciones de habilitación de la matriz definida en Clarificaciones (`PENDIENTE` → `APROBADA`/`OBSERVADA`/`RECHAZADA`; `OBSERVADA` → `APROBADA`/`RECHAZADA`; `APROBADA` → `SUSPENDIDA`; `SUSPENDIDA` → `APROBADA`/`RECHAZADA`; `RECHAZADA` final), rechazar el resto con conflicto (`409`) y conservar el historial completo de eventos.
- **FR-006**: El sistema DEBE permitir consultar el estado de habilitación del conductor junto con su historial.
- **FR-007**: El sistema DEBE registrar la licencia del conductor y calcular su estado (`VIGENTE` o `VENCIDO`) según la fecha de vencimiento.
- **FR-008**: El sistema DEBE permitir registrar vehículos de tipo `AUTO` o `MOTO` con al menos un tipo de servicio (`PASAJEROS`, `ENVIOS`), inicialmente sin habilitar, y listarlos y consultarlos por conductor.
- **FR-009**: Todas las respuestas, incluidos los errores, DEBEN cumplir `docs/contract/openapi.yaml`, con errores en formato `{codigo, mensaje}`.
- **FR-010**: La API, la base de datos y el servicio de identidad DEBEN poder levantarse con un único comando documentado, con una base de datos propia de M3 y datos de prueba. La pantalla se ejecuta aparte.
- **FR-011**: El esquema de datos DEBE gestionarse con migraciones versionadas.
- **FR-012**: La configuración y los secretos DEBEN estar fuera del repositorio; las imágenes DEBEN tener versiones fijas.
- **FR-013**: Cada cambio propuesto DEBE ser verificado automáticamente (estilo, pruebas, umbral de cobertura y contrato).
- **FR-014**: Una única pantalla DEBE mostrar el listado de conductores, con estados de error y vacío.
- **FR-015**: El proyecto DEBE incluir una justificación técnica breve del stack elegido y documentación versionada junto al código.
- **FR-016**: La lógica de los 10 endpoints DEBE desarrollarse con TDD, alcanzando al menos 65–70% de cobertura sobre lo implementado.
- **FR-017**: Todos los endpoints DEBEN exigir un token válido emitido por el servicio de identidad (`401` si falta o es inválido) y las acciones de habilitación DEBEN requerir el rol de operador (`403` si no lo tiene).
- **FR-018**: El servicio de identidad DEBE levantarse con el entorno, con usuarios y roles de prueba (operador y conductor) cargados automáticamente; los operadores de prueba DEBEN tener un atributo numérico `id_operador` incluido en su token.
- **FR-019**: El sistema DEBE rechazar con `422` la aprobación de un conductor que no tiene una licencia `VIGENTE` cargada.

### Entidades Clave

- **Conductor**: persona habilitada para operar; DNI único, datos de contacto, estado de habilitación, conexión y disponibilidad.
- **Vehículo**: pertenece a un conductor; tipo (auto o moto), patente única, marca, modelo, año, tipos de servicio y estado de habilitación.
- **Documento**: licencia del conductor con número, categoría, fechas, archivo y estado (vigente o vencido).
- **Evento de habilitación**: acción aplicada (aprobar, observar, suspender, rechazar) con estados anterior y nuevo, motivo, operador y fecha; forma el historial.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles

- **SC-001**: Una persona nueva levanta la API, la base de datos y el servicio de identidad con un solo comando en menos de 10 minutos.
- **SC-002**: Los 10 endpoints en alcance responden conforme al contrato en el 100% de las pruebas de contrato.
- **SC-003**: La cobertura de pruebas sobre lo implementado es de al menos 65–70%.
- **SC-004**: El 100% de los cambios propuestos pasa por la verificación automática antes de integrarse.
- **SC-005**: Ante 20 solicitudes simultáneas con el mismo DNI, exactamente una tiene éxito y el resto recibe conflicto.
- **SC-006**: La pantalla muestra el listado de conductores de prueba al abrirse con el entorno levantado.
- **SC-007**: El 100% de las solicitudes sin token válido es rechazado, y el 100% de las acciones de habilitación de un usuario sin rol de operador es rechazado.

## Supuestos

- Hay cuatro grupos en paralelo: Backend (una persona con lógica y endpoints, otra con el servidor HTTP), Datos y seguridad, Testing y Frontend; el Frontend entra al final.
- Los datos de prueba incluyen conductores en distintos estados de habilitación.
- Pila elegida por el equipo: FastAPI, PostgreSQL, Keycloak y Next.js, sujeta a aprobación y justificación técnica (RNF-01).
- Requisitos no funcionales de TP1 aplicables: RNF-01 a RNF-08 y RNF-20.
- Los endpoints, tipos de dato y reglas están definidos en `docs/contract/openapi.yaml`, que es la fuente de verdad.

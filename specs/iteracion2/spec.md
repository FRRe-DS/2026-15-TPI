# Especificación de la Funcionalidad: Iteración 2 — Integración E2E y endpoints restantes de M3

**Rama de la Funcionalidad**: `docs/planificacion-iteracion2`

**Creada**: 2026-10-30

**Estado**: Borrador

**Entrada**: Iteración 2 del Módulo 3. Completar la integración E2E del frontend con la API real, cubrir los 6 endpoints pendientes del contrato, alcanzar cobertura ≥ 70 % y cerrar las tareas de Fase 6 que quedaron abiertas al integrar la Iteración 1.

## Clarificaciones

### Sesión 2026-10-30

- Q: ¿El frontend debe seguir siendo exclusivamente un Server Component sin lógica en el cliente? → A: Sí. Las credenciales de Keycloak y el token nunca llegan al navegador. La arquitectura de Iteración 1 se mantiene sin cambios.
- Q: ¿Los filtros de ubicación (`latitud`/`longitud`) y `tipo_servicio` del listado de conductores entran en esta iteración? → A: Sí. Eran fuera de alcance en Iteración 1; en Iteración 2 se suman al `GET /conductores` y a la lógica de disponibilidad.
- Q: ¿El acceso de cada conductor solo a sus propios datos entra en esta iteración? → A: Sí. Un conductor autenticado solo puede leer y modificar sus propios recursos; cualquier intento sobre datos de otro conductor devuelve `403`.
- Q: ¿La documentación del vehículo (`vehiculo_documento`) entra en esta iteración? → A: Sí. Los 6 endpoints pendientes incluyen documentación y tipos de servicio del vehículo.
- Q: ¿La pantalla del frontend debe mostrar badges de color por estado de habilitación? → A: Sí. La tarea F1-06 quedó con el estado como texto plano; en esta iteración se agregan badges/colores diferenciados por estado.
- Q: ¿Cómo se completan las tareas de Fase 6 (T120–T125) que quedaron abiertas? → A: Se completan como parte de esta iteración, en la fase de cierre.

## Alcance

**En alcance (6 endpoints nuevos + integración E2E + cierre):**

| # | Endpoint | Grupo del contrato | Nota |
|---|---|---|---|
| 11 | `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion` | Habilitación vehículo | Historial de habilitación del vehículo |
| 12 | `PATCH /conductores/{id_conductor}` | Conductores | Actualizar estado de conexión / disponibilidad |
| 13 | `GET /conductores/{id_conductor}/documentacion` | Documentación | Listar documentos del conductor |
| 14 | `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | Documentación vehículo | Registrar documento del vehículo |
| 15 | `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | Documentación vehículo | Listar documentos del vehículo |
| 16 | `PATCH /conductores/{id_conductor}/vehiculos/{id_vehiculo}` | Vehículos | Actualizar tipos de servicio del vehículo |

**También en alcance (completar lo diferido de Iteración 1):**
- Filtros de ubicación (`latitud`/`longitud`) y `tipo_servicio` en `GET /conductores`
- Control de acceso: conductor solo accede a sus propios datos (`403` si intenta acceder a datos ajenos)
- Badges/colores por estado en la pantalla del frontend
- Integración E2E del frontend: `.env.local` con valores reales, verificación manual contra seed
- Cierre: T120–T125 (justificación de stack, README, cobertura ≥ 70 %, quickstart en máquina limpia, PR de `dev` hacia `main`)

**Fuera de alcance:** integraciones con M1/M4/M5/M6 (solo se consumen por contrato OpenAPI), calificación del cliente, solicitudes.

## Escenarios de Usuario y Pruebas *(obligatorio)*

### Historia 8 — Integración E2E del frontend (Prioridad: P0)

Un operador abre la pantalla con el stack levantado y ve el listado real de conductores del seed, con los estados de habilitación diferenciados por color/badge. Con la API caída, la pantalla muestra un error claro sin romper.

**Por qué esta prioridad**: es el criterio de éxito SC-006 de Iteración 1 que se verifica manualmente aquí, y el cierre formal de la Historia 7.

**Prueba independiente**: configurar `.env.local`, levantar el Compose, correr `npm run dev` y verificar el listado y el badge de cada estado.

**Escenarios de aceptación**:

1. **Dado** el stack levantado y `.env.local` completo, **cuando** se abre la pantalla, **entonces** se listan los conductores del seed con nombre, apellido, DNI y badge de color por estado de habilitación.
2. **Dado** la API caída, **cuando** se carga la pantalla, **entonces** muestra un mensaje de error claro sin crashear.
3. **Dado** la pantalla cargada, **cuando** la lista de conductores del seed está vacía, **entonces** muestra el mensaje "No hay conductores".
4. **Dado** `USE_MOCK=false` (o variable ausente), **cuando** se inicia el servidor Next.js, **entonces** `page.tsx` llama a Keycloak y a la API real sin usar datos ficticios.

---

### Historia 9 — Consultar historial de habilitación del vehículo (Prioridad: P1)

Un operador consulta el historial completo de acciones de habilitación de un vehículo específico de un conductor.

**Por qué esta prioridad**: cierra el ciclo de habilitación de vehículos iniciado en la Historia 4.

**Prueba independiente**: se puede probar aplicando acciones de habilitación sobre un vehículo y consultando el historial; entrega valor sin depender de los otros endpoints nuevos.

**Escenarios de aceptación**:

1. **Dado** un vehículo con eventos de habilitación, **cuando** se consulta su historial, **entonces** se devuelven todos los eventos en orden cronológico con acción, estados, motivo, operador y fecha.
2. **Dado** un vehículo sin eventos previos (solo el `ALTA`), **cuando** se consulta el historial, **entonces** se devuelve la lista con el evento de alta únicamente.
3. **Dado** un `id_vehiculo` que no pertenece al conductor indicado, **cuando** se consulta el historial, **entonces** se responde `404`.

---

### Historia 10 — Actualizar conexión y disponibilidad del conductor (Prioridad: P1)

Un conductor puede cambiar su propio estado de conexión y disponibilidad.

**Por qué esta prioridad**: habilita la lógica de asignación de viajes de M5/M6, aunque la integración no sea parte de este alcance.

**Prueba independiente**: se puede probar actualizando el estado y verificando que el listado refleja el cambio.

**Escenarios de aceptación**:

1. **Dado** un conductor autenticado, **cuando** actualiza su propio `conectado` o `disponible`, **entonces** el conductor queda actualizado y el `GET` refleja el cambio.
2. **Dado** un conductor autenticado, **cuando** intenta actualizar los datos de otro conductor, **entonces** se rechaza con `403`.
3. **Dado** un campo no modificable (por ejemplo `habilitacion`), **cuando** se intenta actualizar vía `PATCH`, **entonces** se ignora el campo o se responde `400`.

---

### Historia 11 — Documentación del conductor (Prioridad: P1)

Un operador consulta los documentos cargados de un conductor.

**Escenarios de aceptación**:

1. **Dado** un conductor con documentos cargados, **cuando** se lista su documentación, **entonces** se devuelven todos con tipo, número, categoría, fechas, URL y estado calculado (`VIGENTE`/`VENCIDO`).
2. **Dado** un conductor sin documentos, **cuando** se lista, **entonces** se devuelve lista vacía.
3. **Dado** un `id_conductor` inexistente, **cuando** se consulta, **entonces** se responde `404`.

---

### Historia 12 — Documentación del vehículo (Prioridad: P2)

Un operador carga y consulta documentos asociados a un vehículo.

**Escenarios de aceptación**:

1. **Dado** datos válidos de documento, **cuando** se registra para un vehículo, **entonces** queda guardado y aparece en el listado.
2. **Dado** un vehículo con documentos, **cuando** se lista su documentación, **entonces** se devuelven todos con estado calculado.
3. **Dado** un `id_vehiculo` que no pertenece al conductor, **cuando** se intenta registrar o listar, **entonces** se responde `404`.

---

### Historia 13 — Tipos de servicio del vehículo (Prioridad: P2)

Un operador actualiza los tipos de servicio (`PASAJEROS`, `ENVIOS`) habilitados de un vehículo.

**Escenarios de aceptación**:

1. **Dado** un vehículo existente, **cuando** se actualizan sus tipos de servicio, **entonces** quedan reflejados en el `GET` del vehículo.
2. **Dado** un valor de tipo de servicio inválido, **cuando** se intenta actualizar, **entonces** se responde `400`.
3. **Dado** un `id_vehiculo` que no pertenece al conductor, **cuando** se intenta actualizar, **entonces** se responde `404`.

---

### Historia 14 — Filtros completos en el listado de conductores (Prioridad: P1)

Un operador o conductor filtra el listado por ubicación y tipo de servicio, además de los filtros ya existentes de Iteración 1.

**Escenarios de aceptación**:

1. **Dado** conductores con distintas ubicaciones, **cuando** se filtra con `latitud` y `longitud`, **entonces** se devuelven solo los conductores dentro del área relevante (según la lógica del contrato).
2. **Dado** conductores con distintos tipos de servicio habilitados, **cuando** se filtra por `tipo_servicio`, **entonces** se devuelven solo los que tienen ese tipo habilitado.
3. **Dado** que los filtros de ubicación y tipo de servicio se combinan con los ya existentes (`habilitado`, `disponible`, `tipo_vehiculo`), **cuando** se usan juntos, **entonces** se aplican todos en conjunción (`AND`).

---

### Historia 15 — Control de acceso de conductor a sus propios datos (Prioridad: P0)

Un conductor autenticado solo puede leer y modificar sus propios recursos; los operadores mantienen acceso completo.

**Por qué esta prioridad**: requisito de seguridad diferido de Iteración 1.

**Escenarios de aceptación**:

1. **Dado** un conductor autenticado, **cuando** consulta sus propios vehículos, documentos o habilitación, **entonces** obtiene los datos correctos.
2. **Dado** un conductor autenticado, **cuando** intenta consultar los datos de otro conductor, **entonces** recibe `403`.
3. **Dado** un operador autenticado, **cuando** consulta cualquier conductor, **entonces** obtiene los datos sin restricción.

---

## Requisitos Funcionales

- **FR-020**: El sistema DEBE exponer los 6 endpoints pendientes conforme a `docs/contract/openapi.yaml`.
- **FR-021**: El sistema DEBE soportar los filtros `latitud`, `longitud` y `tipo_servicio` en `GET /conductores`.
- **FR-022**: Un conductor autenticado DEBE poder acceder únicamente a sus propios recursos; cualquier acceso a datos ajenos DEBE devolver `403`.
- **FR-023**: `PATCH /conductores/{id}` DEBE permitir actualizar `conectado` y `disponible`; los campos no modificables se ignoran o responden `400`.
- **FR-024**: `POST` y `GET` de documentación del vehículo DEBEN calcular el estado (`VIGENTE`/`VENCIDO`) al leer, igual que la documentación del conductor.
- **FR-025**: `PATCH /conductores/{id}/vehiculos/{id_vehiculo}` DEBE actualizar los tipos de servicio del vehículo sin eliminar los no mencionados, salvo que el contrato indique reemplazo completo.
- **FR-026**: La pantalla del frontend DEBE mostrar badges con colores diferenciados por estado de habilitación (`PENDIENTE`, `APROBADA`, `OBSERVADA`, `SUSPENDIDA`, `RECHAZADA`).
- **FR-027**: La cobertura de pruebas sobre lo implementado DEBE alcanzar al menos 70 %.
- **FR-028**: Todas las tareas de cierre (T120–T125) DEBEN completarse antes de la PR de `dev` hacia `main`.

### Entidades Clave (nuevas o ampliadas)

- **DocumentoVehiculo**: análogo a `DocumentoConductor`; pertenece a un vehículo; estado calculado al leer.
- **TipoServicioVehiculo**: fila de `vehiculo_tipo_servicio`; `habilitado` pasa a ser actualizable por `PATCH`.
- **UbicacionConductor**: `latitud`, `longitud` y `fecha_act_ubic` en el conductor; usados para filtrar el listado.

## Criterios de Éxito *(obligatorio)*

### Resultados Medibles

- **SC-008**: La pantalla muestra los conductores del seed con badges de color al abrir con el stack levantado.
- **SC-009**: Los 6 endpoints nuevos responden conforme al contrato en el 100 % de las pruebas de contrato.
- **SC-010**: Un conductor no puede acceder a datos de otro conductor; el 100 % de los intentos devuelve `403`.
- **SC-011**: La cobertura de pruebas es ≥ 70 % sobre lo implementado.
- **SC-012**: La PR de `dev` hacia `main` se abre con CI verde y todos los criterios de Iteración 1 y 2 cumplidos.
- **SC-013**: El quickstart se ejecuta en una máquina limpia en menos de 10 minutos (revalidación de SC-001).

## Supuestos

- El stack de Iteración 1 (FastAPI, PostgreSQL, Keycloak, Next.js) no cambia.
- El contrato `docs/contract/openapi.yaml` es la fuente de verdad; los 6 endpoints nuevos ya están definidos en él.
- Los datos de seed incluyen conductores con distintas ubicaciones y tipos de servicio.
- Las tareas de cierre T120–T125 las ejecuta el mismo grupo de Frontend / Cierre.
- Requisitos no funcionales de TP1 aplicables: los mismos que en Iteración 1 (RNF-01 a RNF-08, RNF-20) más RNF-16 si se define umbral de rendimiento.

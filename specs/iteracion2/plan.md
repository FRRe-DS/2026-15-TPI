# Plan de Implementación: Iteración 2 — Plataforma y Seguridad

**Rama**: `docs/planificacion-iteracion2` | **Contrato**: [OpenAPI 1.2.0](../../docs/contract/openapi.yaml)

**Entrada**: alcance de datos y seguridad solicitado para la Iteración 2, coordinado con el plan del [Backend](../iteracion2-backend/plan.md), el modelo de datos y el contrato vigente.

## Resumen

Preparar la base de datos, el entorno y la identidad de M3 para las 17 operaciones del contrato 1.2.0. El cambio central es una migración Alembic reversible que unifica el estado del conductor, agrega los datos de Iteración 2 y crea las tablas de solicitudes y documentos de vehículos. Se actualizarán los modelos SQLAlchemy, el seed, Keycloak y la configuración de Compose sin introducir operaciones de integración que no estén en el contrato.

Este plan cubre la plataforma y el grupo de Datos y seguridad. La lógica y los endpoints corresponden al plan de Backend; las pruebas de contrato y la integración continua se coordinan con Testing.

## Alcance e integración entre módulos

- **M4** solo consulta conductores, estado y ubicación con el rol `servicio`. M3 no expone escrituras para M4.
- **M5** es el origen de las solicitudes; M3 las consulta y permite que el conductor las acepte o rechace. El backend no crea solicitudes.
- **M6** no se consume ni se integra en esta iteración. No se implementan viajes ni calificación de clientes. `suma_puntajes` y `cantidad_calificaciones` se cargan en el seed y se exponen como datos de solo lectura.
- Las 17 operaciones del contrato OpenAPI 1.2.0 son la fuente de verdad. No agregar rutas retiradas de integración M4/M6.

## Plan de trabajo

| Área | Trabajo | Entregables | Criterio de cierre |
|---|---|---|---|
| Migración y persistencia | Crear Alembic `0002`, actualizar modelos y los mínimos consumidores existentes | Migración reversible, modelos SQLAlchemy, ajustes acotados a `sql_conductores.py` y `infra/seed/cargar_datos.py` | `upgrade` y `downgrade` funcionan sobre la revisión anterior y las pruebas de esquema pasan |
| Datos de prueba | Extender el seed de forma determinista e idempotente | Escenarios de conductor, solicitudes, vehículos, documentos y usuario conductor descritos abajo | Seed ejecutable más de una vez y cubre los escenarios del contrato |
| Keycloak y entorno | Agregar el rol técnico de solo lectura y su cuenta M4, parametrizada | Realm, variables en `.env.example`, Compose y pruebas del realm | El realm importa con variables de entorno; el token de M4 tiene `servicio` y no obtiene permisos de escritura |
| Integración de equipos | Ordenar la migración/modelos respecto de los repositorios SQL | Dependencia explícita para las PR L9 y L10 de Backend | L9 espera migración/modelos; L10 sigue a L9 y también requiere las tablas del modelo |

### Migración Alembic `0002`

La migración parte del esquema de Iteración 1 y debe incluir `downgrade` funcional.

- Reemplazar `conectado` y `disponible` por `estado`, migrando los datos existentes: `conectado=false` pasa a `DESCONECTADO`; `conectado=true, disponible=true` a `DISPONIBLE`; y `conectado=true, disponible=false` a `CONECTADO`. Después, quitar ambas columnas y el índice antiguo y crear el índice de `estado`.
- Agregar a `conductor`: `id_vehiculo_activo`, `fecha_ultimo_cambio_estado`, `suma_puntajes` y `cantidad_calificaciones`, con sus claves foráneas, valores por defecto y restricciones según el [modelo de datos](../iteracion2-backend/data-model.md).
- Crear las tablas `solicitud` y `vehiculo_documento`, con claves, restricciones e índices definidos en el modelo de datos.
- El `downgrade` recrea las columnas antiguas y su índice antes de retirar los campos/tablas nuevos. Reconstruye sus booleanos desde `estado`: `DESCONECTADO` → `false/false`, `DISPONIBLE` → `true/true`, y `CONECTADO` u `OCUPADO` → `true/false`. Las dos últimas situaciones no se pueden distinguir en el esquema anterior.

Los modelos SQLAlchemy deben representar el esquema migrado. Como `0002` elimina columnas consultadas actualmente, el mismo cambio coordinado incluye la adaptación mínima de `backend/app/infraestructura/repositorios/sql_conductores.py` y del seed para que `dev` siga levantando y cargando datos entre la migración y la integración de Backend.

### Datos de prueba requeridos

El seed debe ser determinista e idempotente e incluir:

- Conductores en los cuatro estados: `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`.
- Un conductor sin ubicación registrada y otro sin vehículo activo.
- Un conductor con calificaciones y otro sin ninguna; `suma_puntajes` y `cantidad_calificaciones` se almacenan y `puntaje_promedio` se calcula al leer. No se agrega una escritura funcional de calificación.
- Solicitudes en los cuatro estados (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`), con una solicitud pendiente vencida y otra vigente.
- Documentos de vehículo vigentes y vencidos.
- Un usuario conductor cuyo claim entero `id_conductor` coincida con un conductor del seed.

### Keycloak y autorización de servicio

- Agregar el rol `servicio` al realm. La cuenta técnica de M4 obtiene ese rol y credenciales configuradas por variables de entorno, nunca valores secretos versionados.
- Exponer las variables necesarias en `infra/.env.example` y actualizar `infra/docker-compose.yml` y `backend/tests/infra/test_realm.py`.
- Agregar el mapeador de usuario para emitir `id_conductor` como entero en el token, igual que el claim `id_operador`; el usuario de prueba debe apuntar al conductor sembrado.
- La cuenta `servicio` es de solo lectura: puede consultar conductores, vehículos, estado y ubicación; no puede actualizar estados, responder solicitudes ni ejecutar acciones de operador.
- Mantener la validación JWT con firma/JWKS, issuer, audiencia y expiración, y no guardar secretos en el repositorio.

## Orden y dependencias

La migración y los modelos de Datos y seguridad deben integrarse antes de los repositorios SQL de Backend:

1. Datos y seguridad entrega `0002`, los modelos, la adaptación mínima de `sql_conductores.py` y el seed compatible.
2. Backend implementa L9 (repositorio SQL de conductores y unidad de trabajo) sobre esos modelos y columnas.
3. Backend implementa L10 (repositorios de solicitudes y documentos de vehículos) después de L9 y con las tablas de `0002` disponibles.

Las tareas de Backend que usan repositorios en memoria pueden avanzar en paralelo; L9 y L10 no deben integrarse contra el esquema anterior. El orden de despliegue y las pruebas de migración se coordinan entre los responsables de Datos y seguridad, Backend y Testing.

## Criterios de aceptación

- La migración `0002` lleva una base de Iteración 1 al esquema 1.2.0, conserva correctamente los estados derivados de los booleanos previos y puede revertirse con `downgrade`.
- Los modelos SQLAlchemy, el repositorio SQL existente y el seed funcionan con el nuevo esquema sin referencias a las columnas retiradas.
- El seed es repetible y cubre los cuatro estados, ubicación y vehículo activos opcionales, calificaciones, solicitudes y documentos requeridos.
- Keycloak emite tokens de operador, conductor y servicio; `id_conductor` es un entero coincidente con el seed y la cuenta de servicio no puede escribir. `puntaje_promedio` y `cantidad_calificaciones` se exponen solo para lectura.
- `.env.example` documenta las variables nuevas sin incluir credenciales reales; Compose y las pruebas del realm reflejan el rol y la cuenta técnica.
- Las pruebas de migración, esquema y realm pasan, y el contrato/documentación conserva las 17 operaciones vigentes sin las integraciones M4/M6 retiradas.

## Riesgos y coordinación

- **Pérdida de distinción al hacer downgrade**: los estados `CONECTADO` y `OCUPADO` se reducen ambos a `conectado=true, disponible=false`; el comportamiento queda documentado.
- **Orden de integración**: quitar columnas antes de adaptar sus consumidores rompe el seed y el repositorio SQL. La migración, el cambio mínimo de esos consumidores y los modelos se entregan coordinados antes de L9/L10.
- **Desalineación del contrato**: cambios de rutas o permisos se resuelven contra `docs/contract/openapi.yaml`; esta iteración no agrega escrituras para M4/M6 ni operaciones de viajes/calificación.

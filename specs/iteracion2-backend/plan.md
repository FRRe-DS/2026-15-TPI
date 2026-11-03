# Plan de Implementación: Iteración 2 — Backend de M3 (Conductores y Vehículos)

**Rama**: `docs/planificacion-iteracion2-backend` | **Fecha**: 2026-11-03 | **Spec**: [spec.md](./spec.md)

**Entrada**: Especificación en `specs/iteracion2-backend/spec.md`. Continúa el backend de la [Iteración 1](../iteracion1/plan.md).

## Resumen

Entregar los 9 endpoints que faltan del contrato `docs/contract/openapi.yaml` (1.1.0) y adaptar los 10 ya implementados al contrato nuevo: rol `servicio`, acceso propio del conductor, puntaje y vehículo activo en las respuestas, filtro por tipo de servicio y versión 1.1.0. Al final, la API expone las 19 operaciones.

Este plan cubre **solo la lógica y el servidor HTTP** del backend. La migración, el seed y Keycloak (Datos y seguridad), las pruebas de contrato e integración (Testing) y la pantalla (Frontend) planifican por separado; lo que Backend necesita de ellos está en [data-model.md](./data-model.md) y [contracts/token-jwt.md](./contracts/token-jwt.md).

El trabajo se reparte en **21 PRs chicas** contra `dev`, cada una con una sola responsabilidad y estimada en menos de 600 líneas con sus tests, para que cada revisión sea acotada.

## Contexto Técnico

**Lenguaje/Versión**: Python 3.12 (gestionado con uv). Sin cambios.

**Dependencias principales**: FastAPI, Pydantic 2, SQLAlchemy 2 (síncrono) + Alembic, psycopg 3, PyJWT. **No se agregan dependencias.** Versiones en [research.md de la Iteración 1](../iteracion1/research.md).

**Almacenamiento**: PostgreSQL 17, base `m3`. Los cambios de esquema los hace Datos y seguridad; el backend los consume por el [data-model.md](./data-model.md).

**Pruebas**: pytest + pytest-cov. Unitarios con repositorios en memoria para dominio y casos de uso; de API con `TestClient` y tokens firmados en el test. Los de integración con PostgreSQL real que cubren los repositorios SQL son del backend; los de contrato y concurrencia de extremo a extremo son de Testing.

**Plataforma objetivo**: Linux en contenedores (Docker Compose). Sin cambios.

**Tipo de proyecto**: Servicio web (API REST), arquitectura en capas con dominio aislado.

**Metas de rendimiento**: Sin meta cuantitativa.

**Restricciones**: Contrato OpenAPI como fuente de verdad; sin secretos en el repo; cobertura sobre el umbral vigente de CI (65 %; se propone 70 %, ver [research.md](./research.md), decisión 12); no se implementa un endpoint que no esté en el contrato.

**Escala/Alcance**: 9 endpoints nuevos, 4 adaptaciones de los existentes, 4 entidades nuevas y 5 errores de dominio nuevos.

## Verificación contra la Constitución

*Puerta: debe pasar antes de la Fase 0. Se vuelve a verificar tras el diseño.*

| Principio | Cómo lo cumple el plan | Estado |
|---|---|---|
| I. TDD | Cada PR empieza por tests que fallan; el dominio y los casos de uso se testean sin servidor ni base | Cumple |
| II. Cobertura | Cada PR mantiene el umbral vigente; se propone subirlo a 70 % al integrar la lógica | Cumple |
| III. Pirámide de tests | Unitarios (dominio y casos de uso), de API (routers), de integración de repositorios SQL; contrato y concurrencia de punta a punta son de Testing | Cumple |
| IV. API-first | No se agrega ningún endpoint fuera del contrato; los tipos de servicio se habilitan con la acción de habilitación para no inventar uno (decisión 9) | Cumple |
| V. Migraciones | El backend no cambia el esquema: lo pide a Datos y seguridad por el [data-model.md](./data-model.md) | Cumple |
| VI. Sin secretos | La ubicación simulada es configuración sin secretos; las cuentas de servicio las define Datos y seguridad por variables de entorno | Cumple |
| VII. Código claro | ruff en CI; módulos chicos por responsabilidad | Cumple |
| VIII. Paralelización | Dos stacks de Backend con dueños de archivos explícitos; la lógica avanza con fakes sin esperar la migración | Cumple |
| IX. Documentación breve | Artefactos en `specs/iteracion2-backend/` | Cumple |
| X. Propiedad de datos | Solo tablas de M3; no se consultan datos de otros módulos | Cumple |
| XI. Concurrencia | Bloqueo de fila del conductor en toda escritura de estado, clave primaria por viaje y orden fijo de bloqueos (decisiones 1 y 2) | Cumple |

**Resultado**: sin violaciones. Se reverificó tras el diseño de la Fase 1 y se mantiene.

## Estructura del Proyecto

### Documentación (esta funcionalidad)

```text
specs/iteracion2-backend/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones de diseño
├── data-model.md        # Fase 1: lo que Backend necesita de la base (interfaz con Datos y seguridad)
├── quickstart.md        # Fase 1: cómo probar los endpoints nuevos con tokens de cada rol
├── contracts/           # Fase 1: contratos internos entre stacks
│   ├── casos-de-uso.md
│   ├── token-jwt.md
│   └── errores.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (lo genera /speckit-tasks)
```

### Código fuente afectado

```text
backend/app/
├── dominio/
│   ├── conductor.py            # campos nuevos y puntaje_promedio
│   ├── disponibilidad.py       # nuevo: regla de disponibilidad
│   ├── solicitud.py            # nuevo
│   ├── viaje_finalizado.py     # nuevo
│   ├── documento_vehiculo.py   # nuevo
│   └── errores.py              # errores nuevos
├── aplicacion/
│   ├── politicas/acceso.py     # nuevo: política pura de acceso
│   ├── casos_de_uso/           # 9 nuevos y 4 que cambian
│   └── puertos/                # 3 puertos nuevos; UnidadDeTrabajo y RepositorioConductores cambian
├── infraestructura/repositorios/   # implementaciones SQL de los puertos nuevos
└── api/
    ├── seguridad.py            # rol servicio, claim id_conductor y dependencias de acceso
    ├── errores.py              # mapeo de los errores nuevos
    ├── configuracion.py        # ubicación simulada
    ├── dependencias.py         # proveedores de los casos de uso nuevos
    ├── esquemas/               # esquemas nuevos y ampliados
    └── routers/                # endpoints nuevos y acceso en los existentes

backend/tests/
├── unitarios/                  # dominio, política y casos de uso (con fakes)
├── api/                        # routers, matriz de roles y paridad de rutas
└── integracion/repositorios/   # repositorios SQL nuevos (contra PostgreSQL real)
```

**Decisión de estructura**: igual que en la Iteración 1. El dominio y los casos de uso no importan FastAPI ni SQLAlchemy; el servidor y la lógica avanzan en paralelo contra [contracts/casos-de-uso.md](./contracts/casos-de-uso.md).

## Stacks de trabajo y dueños de archivos

Dos stacks de Backend, todas las PRs contra `dev`. Cada archivo tiene un único dueño.

| Stack | Grupo | Dueño de |
|---|---|---|
| S1 | Backend: lógica | `backend/app/dominio/`, `aplicacion/`, `infraestructura/repositorios/`, `backend/tests/unitarios/`, `backend/tests/integracion/repositorios/` |
| S2 | Backend: servidor | `backend/app/api/`, `backend/tests/api/` |

**Puntos de sincronización**: `docs/contract/openapi.yaml`, [data-model.md](./data-model.md) (con Datos y seguridad), [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) (S1 y S2), [contracts/token-jwt.md](./contracts/token-jwt.md) (S1, S2 y Datos y seguridad) y [contracts/errores.md](./contracts/errores.md) (S1, S2 y Testing).

## Regla de tamaño de las PRs

- Una PR = una responsabilidad. No mezcla dominio con servidor, ni dos grupos de casos de uso.
- Tamaño: las estimaciones de abajo están por debajo de 600 líneas con tests. Una PR que termine entre **1500 y 2000 líneas** con tests sigue siendo aceptable y no hace falta partirla; por encima de eso sí se parte antes de abrirla. Lo que no cambia es que cada PR tenga una sola responsabilidad.
- Cada PR deja la suite en verde por sí sola: no depende de código de otra PR que todavía no está en `dev`.
- Cada PR de S2 actualiza el test de paridad de rutas con sus propios pares (ruta, método): la lista esperada crece de 10 a 19 a lo largo de las PRs y la última deja las 19. Cada cambio de esa lista va precedido por el test que falla.

## PRs de S1: lógica (L1 a L13)

| PR | Rama | Contenido | Depende de | Líneas (est.) |
|---|---|---|---|---|
| L1 | `feat/s1-dominio-conductor-estado` | Campos nuevos del conductor, `puntaje_promedio`, regla y aplicación de disponibilidad, errores `ConductorNoHabilitado` | — | 450 |
| L2 | `feat/s1-dominio-solicitud-viaje-documento` | Entidades `Solicitud`, `ViajeFinalizado` y `DocumentoVehiculo` con sus validaciones y errores `SolicitudVencida`, `SolicitudYaRespondida` y `ViajeEnConflicto` | — | 450 |
| L3 | `feat/s1-politica-acceso` | Política pura de acceso, error `AccesoProhibido` y su matriz | — | 250 |
| L4 | `feat/s1-puertos-fakes-i2` | Puertos nuevos, cambios en `UnidadDeTrabajo` y `RepositorioConductores` y fakes en memoria | L1, L2 | 450 |
| L5 | `feat/s1-casos-estado-ubicacion` | `obtener_estado_conductor`, `obtener_ubicacion_conductor` y `actualizar_estado_conductor` con ubicación simulada | L4 | 500 |
| L6 | `feat/s1-caso-disponibilidad-m4` | `actualizar_disponibilidad_desde_m4` | L5 | 300 |
| L7 | `feat/s1-caso-viaje-finalizado` | `registrar_viaje_finalizado` | L4 | 450 |
| L8 | `feat/s1-casos-solicitudes` | `listar_solicitudes_conductor` y `responder_solicitud` | L5 | 500 |
| L9 | `feat/s1-casos-vehiculo-i2` | `listar_tipos_servicio_vehiculo`, `registrar_documento_vehiculo`, documentos en `obtener_vehiculo` y habilitación de tipos de servicio | L4 | 550 |
| L10 | `feat/s1-casos-conductor-i2` | `listar_conductores` con `tipo_servicio` y campos nuevos en los resultados de conductor | L4 | 350 |
| L11 | `feat/s1-sql-conductor-i2` | `SqlRepositorioConductores` y unidad de trabajo SQL con los campos nuevos, el filtro y los bloqueos, con tests de integración | L4 y migración de Datos | 500 |
| L12 | `feat/s1-sql-solicitud-viaje` | Repositorios SQL de solicitudes y de viajes finalizados, con tests de integración | L11 | 550 |
| L13 | `feat/s1-sql-documentos-vehiculo` | Repositorio SQL de documentos del vehículo y persistencia de los tipos de servicio, con tests de integración | L11 | 400 |

## PRs de S2: servidor (V1 a V8)

| PR | Rama | Contenido | Depende de | Líneas (est.) |
|---|---|---|---|---|
| V1 | `feat/s2-seguridad-rol-servicio` | Rol `servicio`, claim `id_conductor`, dependencias de acceso, mapeo de los errores nuevos y ayudante de tokens de prueba | L3 y L2 | 500 |
| V2 | `feat/s2-acceso-endpoints-existentes` | Aplicar la matriz de acceso a las 10 operaciones de la Iteración 1 y restringir `GET /conductores` | V1 | 550 |
| V3 | `feat/s2-estado-ubicacion` | Operaciones 13, 14 y 15 con esquemas y proveedores, y la ubicación simulada en la configuración | V1 y L5 | 550 |
| V4 | `feat/s2-integracion-m4` | Operación 18 (`PATCH` de M4) | V1 y L6 | 300 |
| V5 | `feat/s2-integracion-m6` | Operación 19 (viaje finalizado de M6) | V1 y L7 | 350 |
| V6 | `feat/s2-solicitudes` | Operaciones 16 y 17 | V1 y L8 | 450 |
| V7 | `feat/s2-vehiculo-i2` | Operaciones 11 y 12 y los documentos del vehículo en el detalle | V1 y L9 | 450 |
| V8 | `feat/s2-conductor-campos-nuevos` | `puntaje_promedio`, `cantidad_calificaciones` e `id_vehiculo_activo` en los esquemas, filtro `tipo_servicio` en el listado, versión 1.1.0 y paridad con las 19 operaciones | V1 y L10 | 400 |

Los números de operación son los de la [matriz de acceso](./contracts/token-jwt.md).

## Orden de integración

```text
Olas de trabajo (las PRs de una misma ola no dependen entre sí):

Ola 1:  L1  L2  L3                          (dominio y política, sin dependencias)
Ola 2:  L4  V1                              (puertos y fakes; seguridad del servidor)
Ola 3:  L5  L7  L9  L10  V2                 (casos de uso por grupo; acceso a los endpoints existentes)
Ola 4:  L6  L8  V3  V5  V7  V8              (siguen a su caso de uso)
Ola 5:  V4  V6                              (siguen a L6 y L8)
Ola 6:  L11 → L12, L13                      (repositorios SQL; esperan la migración y los modelos de Datos y seguridad)
```

- Las olas 1 a 5 trabajan con repositorios en memoria y no esperan a nadie.
- Las PRs SQL (ola 6) esperan la migración y los modelos de Datos y seguridad. Hasta entonces, la API usa los fakes en las pruebas; para que los endpoints nuevos funcionen contra la base real hace falta toda la ola 6.
- Cada PR se abre desde `dev` ya actualizada. Si dos PRs de la misma ola tocan el mismo archivo (por ejemplo `dependencias.py` o `routers/`), la segunda se rebasea sobre la primera; los dueños de archivos de arriba y la separación por grupo reducen ese caso.

## Dependencias con otros grupos

| Grupo | Qué necesita Backend | Cuándo |
|---|---|---|
| Datos y seguridad | Migración y modelos con las columnas y tablas del [data-model.md](./data-model.md); rol `servicio`, cuentas técnicas y claim `id_conductor` del conductor; seed del mínimo indicado | Antes de L11 |
| Testing | Ampliar las pruebas de contrato a 19 operaciones, cobertura 70 %, y cubrir concurrencia y matriz de roles de punta a punta | Después de la ola 6 |
| Frontend | Sin cambios | — |

## Seguimiento de Complejidad

Sin violaciones de la constitución que justificar.

## Puntos a confirmar con el equipo

1. **Habilitación de tipos de servicio con la del vehículo** ([research.md](./research.md), decisión 9). Es un supuesto del plan que no figura en el contrato.
2. **Alta de conductor**: queda permitida a operador y conductor, y no al rol `servicio` (matriz de [token-jwt.md](./contracts/token-jwt.md)).
3. **Umbral de cobertura al 70 %**, a cargo de Testing.
4. **PR de contrato aparte**: ajustar la descripción de roles de `bearerAuth` para que refleje que el listado de conductores es de operador y servicio.

# Plan de Implementación: Iteración 2 — Integración E2E y endpoints restantes de M3

**Rama**: `docs/planificacion-iteracion2` | **Fecha**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Entrada**: Especificación en `specs/iteracion2/spec.md`. Continuación directa del trabajo integrado hasta T119 en Iteración 1.

## Resumen

Completar M3 cerrando los 6 endpoints pendientes del contrato, la integración E2E del frontend con la API real, el control de acceso por conductor, los filtros de ubicación/tipo de servicio en el listado, los badges de color en la pantalla y todas las tareas de cierre (T120–T125) diferidas de Iteración 1. Al final de esta iteración, `dev` se mergea a `main` con CI verde.

## Contexto Técnico

Mismo stack que Iteración 1. No hay cambios de tecnología.

**Lenguaje/Versión**: Python 3.12 (uv); TypeScript 5.9 en Node 24 LTS

**Dependencias principales**: sin cambios respecto a [research.md de Iteración 1](../iteracion1/research.md)

**Almacenamiento**: PostgreSQL 17 — base `m3` existente; solo se agregan columnas/tablas por migraciones Alembic

**Pruebas**: pytest + pytest-cov (umbral sube a 70 %), Testcontainers, openapi-core, Vitest + Testing Library

**Tipo de proyecto**: misma API REST + misma pantalla (una sola pantalla, sin nuevas rutas frontend)

**Metas de rendimiento**: sin nueva meta cuantitativa

**Restricciones**: contrato OpenAPI como fuente de verdad; umbral de cobertura sube a 70 %; todas las tareas de cierre completas antes del merge a `main`

## Verificación contra la Constitución

| Principio | Cómo lo cumple el plan | Estado |
|---|---|---|
| I. TDD | Cada tarea de implementación está precedida por su test Red; los tests de Iteración 1 no se modifican | Cumple |
| II. Cobertura | Umbral sube a 70 %; se mide con `--cov-fail-under=70` | Cumple |
| III. Pirámide de tests | Unitarios (dominio), integración (Testcontainers), contrato (openapi-core), E2E manual (frontend) | Cumple |
| IV. API-first | Los 6 endpoints nuevos ya están en `docs/contract/openapi.yaml`; no se implementa nada fuera de él | Cumple |
| V. Migraciones | Los cambios de esquema (columnas de ubicación, tabla de documento de vehículo) se hacen con Alembic | Cumple |
| VI. Sin secretos | Sin cambios; `.env.local` del frontend es gitignored | Cumple |
| VII. Código claro | ruff obligatorio; sin nuevas excepciones | Cumple |
| VIII. Paralelización | Cuatro stacks: S1 (lógica), S2 (servidor), S3 (datos), S5 (frontend + cierre). S4 suma tests de contrato para los 6 nuevos | Cumple |
| IX. Documentación breve | Artefactos en `specs/iteracion2/`; se actualiza el README raíz | Cumple |
| X. Propiedad de datos | Sin nuevas consultas a tablas de otros módulos | Cumple |
| XI. Concurrencia | El `PATCH` de conductor usa bloqueo de fila igual que las acciones de habilitación | Cumple |

**Resultado**: sin violaciones.

## Estructura del Proyecto

### Documentación (esta funcionalidad)

```text
specs/iteracion2/
├── plan.md              # Este archivo
├── research.md          # Solo si hay nuevas decisiones técnicas
├── data-model.md        # Cambios de esquema respecto a Iteración 1
├── quickstart.md        # Actualizado con los nuevos endpoints
├── contracts/           # Solo contratos nuevos o modificados
│   └── acceso-conductor.md
└── checklists/
    └── requirements.md
tasks.md                 # Lo genera /speckit-tasks
```

### Código fuente afectado

```text
backend/app/
├── dominio/             # nuevos errores: AccesoProhibido
├── aplicacion/
│   └── casos_de_uso/    # 6 nuevos casos de uso
└── api/
    └── routers/         # 6 nuevas rutas + PATCH conductor

frontend/src/
└── components/
    └── ListadoConductores.tsx   # badges por estado

infra/
└── migraciones/         # migración: ubicacion conductor + vehiculo_documento
```

## Stacks de trabajo

Cuatro stacks, todos contra `dev`. S4 (Testing y CI) existe para los tests de contrato de los 6 nuevos endpoints; no necesita PR propia si no hay cambios de CI.

| Stack | Grupo | Dueño de | Entrega |
|---|---|---|---|
| 1 | Backend: lógica | `backend/app/dominio/`, `aplicacion/casos_de_uso/` nuevos, `aplicacion/puertos/` | Lógica de los 6 nuevos casos de uso + control de acceso por conductor |
| 2 | Backend: servidor | `backend/app/api/routers/` nuevas rutas, `backend/tests/api/` | Routers y esquemas de los 6 nuevos endpoints + `PATCH /conductores/{id}` |
| 3 | Datos y seguridad | `infra/migraciones/`, `backend/app/infraestructura/db/`, `infra/seed/` | Migración de esquema + seed con ubicaciones y tipos de servicio |
| 5 | Frontend + Cierre | `frontend/`, `docs/`, `README.md` | E2E manual, badges, `.env.local`, tareas T120–T125 |

**Puntos de sincronización**: `docs/contract/openapi.yaml` (todos) · [data-model.md](./data-model.md) (S1, S3) · [contracts/acceso-conductor.md](./contracts/acceso-conductor.md) (S1, S2) · [../iteracion1/contracts/errores.md](../iteracion1/contracts/errores.md) ampliado con `ACCESO_PROHIBIDO`.

**Orden de merge sugerido**: `feat/s3-migracion-i2` primero (desbloquea repositorios SQL de S1); `feat/s1-logica-i2` antes que `feat/s2-endpoints-i2`; `feat/s5-frontend-e2e` puede ir en cualquier momento; `feat/s5-cierre` al final.

## Seguimiento de Complejidad

Sin violaciones de la constitución que justificar.

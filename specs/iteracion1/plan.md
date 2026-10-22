# Plan de Implementación: Iteración 1 — Base de M3 (Conductores y Vehículos)

**Rama**: `docs/planificacion-iteracion1` | **Fecha**: 2026-10-22 | **Spec**: [spec.md](./spec.md)

**Entrada**: Especificación en `specs/iteracion1/spec.md`.

## Resumen

Entregar 10 de los 16 endpoints propios de M3, con TDD, sobre un backend en capas con dominio aislado (FastAPI + SQLAlchemy síncrono + PostgreSQL), autenticado con tokens JWT de Keycloak y ejecutable con Docker Compose. El trabajo se reparte en cinco stacks de PRs independientes contra `dev`, sincronizados por tres puntos: `docs/contract/openapi.yaml`, el esquema de datos ([data-model.md](./data-model.md)) y las interfaces de los casos de uso ([contracts/casos-de-uso.md](./contracts/casos-de-uso.md)).

## Contexto Técnico

**Lenguaje/Versión**: Python 3.12 (gestionado con uv); TypeScript 5.9 en Node 24 LTS para el frontend

**Dependencias principales**: FastAPI, Pydantic 2, SQLAlchemy 2 (síncrono) + Alembic, psycopg 3, PyJWT; Next.js 16 + React 19 en el frontend. Versiones exactas en [research.md](./research.md)

**Almacenamiento**: PostgreSQL 17 con dos bases separadas (`m3` y `keycloak`) en una sola instancia

**Pruebas**: pytest + pytest-cov, Testcontainers (integración contra PostgreSQL real), openapi-core (contrato), Vitest + Testing Library (frontend)

**Plataforma objetivo**: Linux en contenedores (Docker Compose); desarrollo en Windows, macOS y Linux

**Tipo de proyecto**: Servicio web (API REST) + frontend de una pantalla

**Metas de rendimiento**: Sin meta cuantitativa en TP1 (RNF-16 es de TP3)

**Restricciones**: Contrato OpenAPI como fuente de verdad; sin secretos en el repo; imágenes con versión fija; cobertura mínima 65–70% sobre lo implementado

**Escala/Alcance**: 10 endpoints, 4 entidades principales, 1 pantalla, datos de prueba de unas decenas de conductores

## Verificación contra la Constitución

*Puerta: debe pasar antes de la Fase 0. Se vuelve a verificar tras el diseño.*

| Principio | Cómo lo cumple el plan | Estado |
|---|---|---|
| I. TDD | Cada tarea del `tasks.md` empieza por un test que falla; el dominio y los casos de uso se testean sin servidor | Cumple |
| II. Cobertura | `pytest-cov` con `--cov-fail-under=65` en CI | Cumple |
| III. Pirámide de tests | Unitarios (dominio y casos de uso), integración (Testcontainers), contrato (openapi-core) | Cumple |
| IV. API-first | Los routers se validan contra `docs/contract/openapi.yaml`; los cambios de contrato van en su propia PR | Cumple |
| V. Migraciones | Alembic crea el esquema; los datos de prueba van por un seed aparte | Cumple |
| VI. Sin secretos | `.env.example`, sustitución de variables en el realm, imágenes con versión fija | Cumple |
| VII. Código claro | ruff (lint y formato) en CI | Cumple |
| VIII. Paralelización | Cinco stacks con dueños de archivos explícitos (ver abajo) | Cumple |
| IX. Documentación breve | Artefactos en `specs/iteracion1/`; README de arranque rápido | Cumple |
| X. Propiedad de datos | Base `m3` propia; Keycloak en otra base; sin consultas a tablas ajenas | Cumple |
| XI. Concurrencia | Restricciones únicas de DNI y patente + bloqueo de fila en habilitación | Cumple |

**Resultado**: sin violaciones. Se reverificó tras el diseño de la Fase 1 y se mantiene.

## Estructura del Proyecto

### Documentación (esta funcionalidad)

```text
specs/iteracion1/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y versiones
├── data-model.md        # Fase 1: entidades, tablas y transiciones
├── quickstart.md        # Fase 1: guía de arranque y validación
├── contracts/           # Fase 1: contratos internos entre stacks
│   ├── casos-de-uso.md
│   ├── token-jwt.md
│   └── errores.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (lo genera /speckit-tasks)
```

### Código fuente (raíz del repositorio)

```text
backend/
├── pyproject.toml
├── uv.lock
├── ruff.toml
├── .coveragerc
├── app/
│   ├── dominio/               # entidades, enums, matriz de habilitación, errores de dominio
│   ├── aplicacion/
│   │   ├── casos_de_uso/      # un módulo por caso de uso
│   │   └── puertos/           # interfaces de repositorios y reloj
│   ├── infraestructura/
│   │   ├── db/                # modelos SQLAlchemy y sesión
│   │   └── repositorios/      # implementaciones SQL de los puertos
│   └── api/                   # FastAPI: main, routers, esquemas, seguridad JWT, errores
└── tests/
    ├── unitarios/             # dominio y casos de uso (con repositorios en memoria)
    ├── api/                   # routers con TestClient y casos de uso simulados
    ├── integracion/           # repositorios y concurrencia con Testcontainers
    └── contrato/              # respuestas contra openapi.yaml

frontend/                      # Next.js, una pantalla
└── src/ , tests/

infra/
├── docker-compose.yml
├── .env.example
├── postgres/                  # script de inicio que crea las dos bases
├── keycloak/                  # realm.json con variables de entorno
├── migraciones/               # Alembic
└── seed/                      # script de datos de prueba

.github/workflows/ci.yml
docs/contract/openapi.yaml
```

**Decisión de estructura**: monorepo con carpetas por responsabilidad. El dominio y los casos de uso no importan FastAPI ni SQLAlchemy: dependen solo de los puertos, de modo que la lógica (Stack 1) y el servidor HTTP (Stack 2) avanzan en paralelo contra [contracts/casos-de-uso.md](./contracts/casos-de-uso.md).

## Stacks de trabajo y dueños de archivos

Cinco stacks de PRs, todas contra `dev`. Cada archivo tiene un único dueño para evitar conflictos.

| Stack | Grupo | Dueño de | Entrega |
|---|---|---|---|
| 1 | Backend: lógica | `backend/app/dominio/`, `aplicacion/`, `infraestructura/repositorios/`, `backend/tests/unitarios/`, `backend/pyproject.toml`, `uv.lock` | Dominio, casos de uso y repositorios con TDD |
| 2 | Backend: servidor | `backend/app/api/`, `backend/tests/api/`, `backend/Dockerfile` | Routers, esquemas, validación JWT, manejo de errores |
| 3 | Datos y seguridad | `infra/` completo, `backend/app/infraestructura/db/` | Compose, esquema y migraciones, modelos ORM, realm de Keycloak, seed |
| 4 | Testing y CI | `.github/workflows/`, `backend/tests/integracion/`, `backend/tests/contrato/`, `backend/ruff.toml`, `backend/.coveragerc`, validación del OpenAPI | CI, integración, contrato |
| 5 | Frontend | `frontend/` completo | Pantalla de listado |

**Puntos de sincronización**: `docs/contract/openapi.yaml` (todos), [data-model.md](./data-model.md) (Stacks 1, 3 y 4), [contracts/casos-de-uso.md](./contracts/casos-de-uso.md) (Stacks 1 y 2), [contracts/token-jwt.md](./contracts/token-jwt.md) (Stacks 2, 3 y 5).

**Conflictos esperables** (los resuelve quien integra): `backend/pyproject.toml` y `uv.lock` cuando varios stacks agregan dependencias. La mitigación es que el Stack 1 cree la base y los demás sumen solo sus grupos de dependencias.

## Seguimiento de Complejidad

Sin violaciones de la constitución que justificar.

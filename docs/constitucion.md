# Constitución de 2026-15-TPI

TP de Desarrollo de Software — Módulo 3: Conductores y Vehículos. Insumo: `docs/contract/bosquejo.txt`.

## Principios Fundamentales

### I. TDD en todo el proyecto (NO NEGOCIABLE)
Todo el código de producción nace de un test que falla primero (Red → Green → Refactor). Los tests no se modifican para hacerlos pasar. Una tarea sin test previo no está terminada.

### II. Cobertura como requisito central
La API MUST tener al menos 65–70% de cobertura, priorizando conductores, vehículos y habilitación. Se mide con pytest-cov y se exige en CI. Es un piso, no un techo; el resto se completa en la Iteración 2.

### III. Pirámide de tests
Unitarios para el dominio, de integración contra PostgreSQL real y de contrato contra el OpenAPI.

### IV. API-first
`docs/contract/openapi.yaml` es la fuente de verdad, con rutas consistentes y errores y ejemplos definidos. No se implementa un endpoint que no esté en el contrato.

### V. Persistencia con migraciones
El esquema cambia solo mediante migraciones versionadas (Alembic), con datos semilla para desarrollo.

### VI. Sin secretos en el repo
La configuración va por variables de entorno, con `.env.example` versionado. Los endpoints se protegen con roles de Keycloak. Las imágenes Docker usan versiones fijas, nunca `latest`.

### VII. Código claro
Nombres descriptivos, funciones pequeñas y ruff obligatorio (lint y formato).

### VIII. Trabajo en paralelo
Tareas mínimas e independientes. El contrato OpenAPI y el esquema de datos son los puntos de sincronización entre Backend y Datos.

### IX. Documentación breve
README de arranque rápido; los artefactos de Spec Kit viven en `specs/iteracion1/`.

### X. Propiedad de datos y modularidad
M3 es un servicio con límites explícitos y su propia base de datos. Nunca se consultan tablas de otro módulo; se integra solo por contrato OpenAPI.

### XI. Concurrencia
Las operaciones críticas MUST tolerar solicitudes simultáneas sin duplicar efectos (restricciones únicas de DNI y patente con respuesta `409`), y se cubren con tests.

## Stack y Restricciones

- **Backend**: FastAPI (Python), SQLAlchemy + Alembic, pytest + pytest-cov, ruff.
- **Datos**: PostgreSQL. **Autenticación**: Keycloak (OIDC/JWT).
- **Entorno**: Docker Compose levanta todo con un único comando; imágenes OCI reproducibles y versionadas.
- **Frontend**: Next.js + React + TypeScript (una sola pantalla), a cargo de quien se incorpora al final.
- **Equipo**: Backend, Datos y seguridad, Testing y Frontend (este último entra al final).

## Flujo de Trabajo y Git

- Ramas: `main` (estable), `dev` (integración) y una rama por tarea.
- PRs chicas apiladas sobre `dev`. Commits y PRs en español con formato convencional (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Una PR se mergea con tests en verde, cobertura sobre el umbral y una revisión.
- **Definición de terminado**: el test falló primero y ahora pasa, el contrato está actualizado, la cobertura no baja del umbral, ruff pasa y la PR está aprobada.

## Gobernanza

Esta constitución prevalece sobre otras prácticas del proyecto. Las enmiendas requieren acuerdo del equipo y se versionan con versión semántica. Toda PR MUST verificar el cumplimiento de estos principios.

**Versión**: 1.0.0 | **Ratificada**: 2026-10-22 | **Última enmienda**: 2026-10-22

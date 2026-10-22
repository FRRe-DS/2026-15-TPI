# Investigación: Iteración 1 — Base de M3

Decisiones técnicas con su justificación (RNF-01). Las versiones se verificaron el 2026-10-22 contra PyPI, npm y la tabla de soporte de cada producto. Quedan fijadas en lockfiles y en las etiquetas de imagen; nunca `latest`.

## Versiones

| Componente | Versión fijada | Justificación |
|---|---|---|
| Python | 3.12 (3.12.15) | Elegida por el equipo; con soporte de seguridad hasta 2028-10 |
| uv | última estable al construir | Lockfile reproducible (`uv.lock`) |
| FastAPI | 0.159.x | Validación automática con Pydantic y OpenAPI propio para cotejar con el contrato |
| Pydantic | 2.14.x | Validación de entrada y salida |
| SQLAlchemy | 2.1.x | ORM síncrono con transacciones y bloqueo de fila |
| Alembic | 1.20.x | Migraciones versionadas |
| psycopg | 3.3.x | Driver oficial de PostgreSQL |
| PyJWT | 2.15.x (con `cryptography`) | Verificación de firma con claves públicas (JWKS) |
| pytest / pytest-cov | 9.1.x / 7.1.x | Pruebas y cobertura |
| Testcontainers | 4.15.x | PostgreSQL real en integración |
| openapi-core | 0.23.x | Validación de respuestas contra el contrato |
| ruff | 0.17.x | Lint y formato |
| PostgreSQL | 17.11 | Versión madura, con soporte hasta 2029-11 y compatible con Keycloak 26 |
| Keycloak | 26.8.1 | Rama vigente; 26.7 deja de recibir soporte el 2026-10-01 |
| Node.js | 24 LTS (24.22.x) | LTS activa; la 26 recién pasa a LTS el 2026-10-28 |
| Next.js / React | 16.4.x / 19.3.x | Última estable; requiere Node >= 20.9 |
| TypeScript | 5.9.x | La 7.0 es muy reciente; se evita por compatibilidad con ESLint y Next |

Las etiquetas exactas de las imágenes (`python`, `postgres`, `keycloak/keycloak`) se confirman al construir y se fijan en el Compose.

## Decisiones de diseño

### Arquitectura en capas con dominio aislado
- **Decisión**: dominio, casos de uso con puertos, infraestructura y API.
- **Motivo**: permite TDD del dominio sin servidor ni base, y que una persona haga la lógica mientras otra hace el servidor HTTP.
- **Alternativas**: capas simples (la lógica queda pegada a FastAPI) y hexagonal completa (demasiada ceremonia para 10 endpoints).

### Acceso a datos síncrono
- **Decisión**: SQLAlchemy síncrono.
- **Motivo**: tests más simples y menos complejidad; alcanza para la carga de TP1.
- **Alternativa**: asíncrono, descartado por costo en pruebas.

### Validación de JWT
- **Decisión**: validación local con PyJWT y las claves públicas de Keycloak (JWKS), con caché.
- **Se verifica**: firma, vencimiento, emisor y rol. El rol `operador` se lee de `realm_access.roles`; `id_operador` es un claim numérico propio.
- **Motivo**: no depende de Keycloak en cada pedido y se testea con tokens firmados con una clave de prueba.
- **Alternativa**: introspección por pedido, descartada por acoplamiento.

### Concurrencia (RNF-08)
- **DNI y patente**: restricciones únicas en la base; el `IntegrityError` se traduce a `409`. No se verifica antes de insertar (evita la carrera).
- **Habilitación**: bloqueo de fila (`SELECT ... FOR UPDATE`) del conductor o vehículo mientras se valida la transición y se inserta el evento.
- **Prueba**: integración con hilos concurrentes sobre PostgreSQL real.

### Estado de documentos
- **Decisión**: `VIGENTE` o `VENCIDO` se calcula al leer, comparando `fecha_vencimiento` con la fecha actual de un reloj inyectable.
- **Motivo**: no hay tareas de actualización y el reloj inyectable hace determinista el test.

### Tests de integración
- **Decisión**: Testcontainers con la misma imagen de PostgreSQL que el Compose.
- **Motivo**: cada corrida es aislada y funciona igual en local y en CI.

### Tests de contrato
- **Decisión**: pytest + openapi-core validan cada respuesta contra `docs/contract/openapi.yaml`.
- **Alternativa**: Schemathesis, descartado por ser ruidoso y lento para el CI de TP1.

### Entorno con Compose
- **Servicios**: `postgres`, `keycloak`, `migraciones` (una vez), `seed` (una vez) y `api`.
- **Bases**: un script de inicio crea las bases `m3` y `keycloak` con usuarios distintos.
- **Realm**: se importa al arrancar; las contraseñas y secretos se inyectan con variables de entorno, sin valores en el repo.
- **Puertos**: API en `8080` (prefijo `/api/v1`, como el contrato), Keycloak en `8081`, PostgreSQL en `5432`.

### Frontend
- **Decisión**: el servidor de Next pide el token a Keycloak con un usuario de prueba (concesión de contraseña) y llama a la API. El navegador nunca ve credenciales.
- **Corre**: fuera del Compose, con `npm run dev`.

### CI
- **Decisión**: GitHub Actions con un workflow por PR: ruff, pruebas con cobertura mínima, validación del `openapi.yaml` y, cuando exista, lint y pruebas del frontend.
- **Umbral**: `--cov-fail-under=65`.

### Errores
- **Decisión**: formato único `{codigo, mensaje}` con un catálogo de códigos ([contracts/errores.md](./contracts/errores.md)).

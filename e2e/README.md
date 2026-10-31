# Pruebas E2E de M3 (Playwright)

Atraviesan el stack real: PostgreSQL, Keycloak, migraciones, seed, API y el
frontend de Next.js. Complements los tests de `backend/` (unitarios, API,
integración, contrato y concurrencia), que usan repositorios simulados o
contenedores sin Keycloak real.

## Qué cubre

| Proyecto | Qué prueba |
|---|---|
| `api` | Token real de Keycloak, formato de errores, alta de conductor y vehículo, licencia, habilitación y `403` por rol. |
| `ui` | Que la pantalla de Next liste los conductores del seed con su badge, y que lo creado por API aparezca en pantalla. |

## Requisitos

- Docker con Compose.
- Node 24.
- Un `infra/.env` completo (el script lo genera).

## Uso local

```bash
# 1. Crear infra/.env si no existe (secretos aleatorios)
bash e2e/scripts/stack.sh generar-env

# 2. Levantar el stack (PostgreSQL + Keycloak + migraciones + seed + API)
bash e2e/scripts/stack.sh up

# 3. Escribir frontend/.env.local a partir de infra/.env
bash e2e/scripts/stack.sh frontend-env

# 4. Instalar dependencias y navegador
cd e2e
npm install
npx playwright install chromium

# 5. Correr todo (Playwright levanta el frontend)
PW_WEBSERVER=1 npm test

# 6. Bajar el stack y borrar el volumen
bash scripts/stack.sh down --volumes
```

Para correr solo un proyecto:

```bash
npm run test:api
npm run test:ui
```

## Cómo se autentica

El token se pide a Keycloak con concesión de contraseña y se reutiliza mientras
dure el proceso (`fixtures/api.ts`). El frontend pide el token en el servidor,
así que las pruebas de UI no inician sesión: abren la página y verifican lo que
ve el usuario.

Las credenciales salen del entorno o, si no están definidas, de `infra/.env`.

## Datos de prueba

La API no expone `DELETE`, así que los tests que crean entidades son aditivos:
`fixtures/datos.ts` genera un DNI y una patente únicos por corrida. Por eso se
asertá por pertenencia (`toContain`, `getByRole`) y no por cantidades exactas.
Si necesitás un estado limpio, bajá el stack con `--volumes`.

## CI

El job `e2e` de `.github/workflows/ci.yml` genera el `.env`, levanta Compose,
instala Chromium, corre ambos proyectos y sube `playwright-report/` y
`test-results/` si algo falla. Corre con un solo worker porque todos los tests
comparten la misma base.

## Fuera de alcance por ahora

`app-conductor/` es un prototipo con datos fijos y no consume la API; un E2E ahí
todavía no probaría integración real. Se suma cuando esté conectado a M3.

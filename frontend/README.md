# Frontend — Módulo M3 (Conductores y Vehículos)

Interfaz web construida con **Next.js 16**, **React 19** y **TypeScript 5.9**. Incluye la app del conductor (login, estado, solicitudes, viaje y ubicación simulada) y el listado de conductores para operador y servicio.

## Requisitos previos

- Node.js 24 LTS (ver `.nvmrc`)
- npm

## Instalación

```bash
cd frontend
npm ci
cp .env.example .env.local
```

> El repositorio incluye `package-lock.json`; usá `npm ci` para instalar exactamente las versiones del lockfile.

## Variables de entorno

Las variables se leen en el servidor de Next. No llegan al navegador y no deben llevar el prefijo `NEXT_PUBLIC_`.

| Variable | Descripción |
|---|---|
| `USE_MOCK` | `true` usa datos simulados; `false` llama a la API real. |
| `API_URL` | URL base de la API de M3. Por defecto `http://localhost:8080/api/v1`. |
| `KEYCLOAK_URL` | URL de Keycloak. Por defecto `http://localhost:8081`. |
| `KEYCLOAK_REALM` | Realm de Keycloak. Por defecto `m3`. |
| `KEYCLOAK_CLIENT_ID` | Cliente confidencial de la API. Por defecto `m3-api`. |
| `KEYCLOAK_CLIENT_SECRET` | Secreto del cliente `m3-api`. |
| `TEST_USER` / `TEST_PASSWORD` | Usuario de servicio u operador que usa el listado de conductores (`GET /conductores`). No es el login del conductor. |

## Modo mock (`USE_MOCK=true`)

Permite recorrer las pantallas sin backend ni Keycloak. En `.env.local`:

```env
USE_MOCK=true
```

Luego iniciá el servidor de desarrollo:

```bash
npm run dev
```

Abrí `http://localhost:3000` y navegá con la barra superior. En este modo:

- El listado de `/` usa `src/mocks/conductores.mock.ts`.
- `/estado`, `/solicitudes` y `/viaje` usan `src/mocks/conductor.mock.ts` y no exigen sesión.
- Los cambios son simulados y no se guardan en ninguna API.
- La pantalla `/login` sigue apuntando a Keycloak, así que para el recorrido mock entrá directamente a las pantallas del conductor.

> `USE_MOCK=true` es solo para desarrollo y pruebas. No lo uses en producción.

## Modo real (`USE_MOCK=false`)

Requiere la API de M3 y Keycloak disponibles. La forma más simple es levantar el stack completo desde la raíz del repositorio:

```bash
cp .env.example .env
# Completar las variables del .env
docker compose up --build
```

Después configurá `.env.local` para apuntar a esos servicios:

```env
USE_MOCK=false
API_URL=http://localhost:8080/api/v1
KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_REALM=m3
KEYCLOAK_CLIENT_ID=m3-api
KEYCLOAK_CLIENT_SECRET=<mismo valor que KEYCLOAK_M3_CLIENT_SECRET>
TEST_USER=operador.m3
TEST_PASSWORD=<mismo valor que M3_OPERADOR_PASSWORD>
```

Iniciá el frontend:

```bash
npm run dev
```

Abrí `http://localhost:3000/login` e ingresá con el conductor de prueba (`conductor.m3` y la clave `M3_CONDUCTOR_PASSWORD` del `.env` de la raíz). El formulario envía las credenciales al route handler `/api/sesion`; ese handler pide el token a Keycloak y lo guarda en una cookie `httpOnly`. El navegador nunca recibe el token ni el secreto del cliente.

El modo real necesita que la API exponga las operaciones del contrato 1.2.0 que consume la app: `GET` y `PATCH /conductores/{id}/estado`, `GET /conductores/{id}/ubicacion`, `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`. Si todavía no están disponibles en tu entorno, usá el modo mock.

## Recorrido de pantallas

| Ruta | Pantalla | Qué hace |
|---|---|---|
| `/` | Listado de conductores | Vista de operador y servicio. Muestra los conductores con su habilitación y los estados de carga, error y lista vacía. El conductor no puede usar esta pantalla (la API le responde 403). |
| `/login` | Iniciar sesión | Pide usuario y contraseña, muestra el error ante credenciales inválidas y redirige a `/estado` al autenticarse. Sin sesión, las pantallas del conductor redirigen acá. |
| `/estado` | Ponerse en línea | Muestra el estado operativo actual y permite pedir `DESCONECTADO`, `CONECTADO` o `DISPONIBLE`. `OCUPADO` no se ofrece. Si falta habilitación o vehículo activo, muestra el error `CONDUCTOR_NO_HABILITADO` (422). |
| `/solicitudes` | Pedidos entrantes | Lista las solicitudes con su estado. Solo las `PENDIENTE` muestran cuenta regresiva y botones de aceptar o rechazar; al vencer se deshabilitan. Muestra «No hay solicitudes», «oferta vencida» (410) y conflictos (409). |
| `/viaje` | Viaje en curso | Muestra la solicitud aceptada. «Pasajero subió» avanza el paso y habilita «Finalizar viaje», que pide el estado `DISPONIBLE` y vuelve a `/solicitudes`. Sin viaje muestra «Sin viaje en curso». |

La lógica de ubicación simulada está en `src/lib/simuladorUbicacion.ts`: genera puntos de un recorrido y, mientras el conductor está `OCUPADO`, envía `latitud` y `longitud` juntas cada 5 segundos a través de `/api/ubicacion`, y se detiene al terminar. El componente `UbicacionActual` muestra la última coordenada y su fecha; si los tres campos vienen en `null`, se muestra «Ubicación desconocida». No hay mapa.

Recorrido sugerido en modo real:

1. Iniciar sesión en `/login`.
2. Pasar a `DISPONIBLE` en `/estado`.
3. Revisar y aceptar una solicitud pendiente en `/solicitudes`.
4. Abrir `/viaje`, tocar «Pasajero subió» y luego «Finalizar viaje».
5. Verificar que el conductor vuelve a `/solicitudes` y queda `DISPONIBLE`.

## Scripts disponibles

```bash
npm run dev     # Servidor de desarrollo en http://localhost:3000
npm run build   # Compilación de producción
npm run lint    # ESLint
npm run test    # Pruebas unitarias con Vitest
```

## Pruebas

La suite usa Vitest con jsdom y Testing Library. Las pruebas cubren cliente de API, sesión, mocks, simulador de ubicación, estados de pantalla, navegación y las pantallas del conductor. Para ejecutarla:

```bash
npm run test
```

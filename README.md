# M3 - Conductores y Vehículos
**Grupo 15.**

Módulo **M3** de la plataforma distribuida de movilidad. 

| **ID** | **Módulo** | **Responsabilidad** | **Integraciones clave** |
|---|---|---|---|
| **M3** | **Conductores y Vehículos** | Perfil, habilitación, vehículos, documentación y estado operativo. | M1, M4, M5, M6. |

> Este README es la documentación del módulo y se va completando a medida que avanza el trabajo. Todo lo que figura acá sale del contrato [`openapi.yaml`](./docs/contract/openapi.yaml) y del documento de planificación de la Iteración 1. Lo que todavía no está definido está marcado como **Pendiente**.

---

## De qué trata este módulo

**M3 es el servicio de la plataforma de movilidad que gestiona a los conductores y sus vehículos.**

- Registra conductores y vehículos (autos y motos) y guarda la licencia del conductor.
- Un operador puede aprobar, observar, suspender o rechazar a un conductor o a un vehículo, siempre con un motivo y con historial.
- Un conductor solo se aprueba si tiene la licencia vigente.
- Expone una API REST de 16 endpoints ([ver contrato](#contrato-de-la-api)); 10 de ellos se construyen en la Iteración 1 ([ver alcance](#alcance-de-la-iteración-1)).
- Cada pedido se autentica con un token JWT emitido por Keycloak, con roles de operador y de conductor ([ver autenticación](#autenticación-y-roles)).
- Tiene su propia base de datos PostgreSQL y no consulta datos de otros módulos ([ver base de datos](#base-de-datos)).
- Una pantalla web muestra el listado de conductores ([ver frontend](#frontend)).
- Todo se levanta con Docker Compose ([ver arranque rápido](#arranque-rápido)), y cada cambio pasa por un CI antes de integrarse.
- Se integra con los módulos M1, M4, M5 y M6 ([ver integración](#integración-con-otros-módulos)).

---

## Índice

1. [Alcance de la Iteración 1](#alcance-de-la-iteración-1)
2. [Arquitectura y estructura del repositorio](#arquitectura-y-estructura-del-repositorio)
3. [Contrato de la API](#contrato-de-la-api)
4. [Integración con otros módulos](#integración-con-otros-módulos)
5. [Reglas de negocio](#reglas-de-negocio)
6. [Errores](#errores)
7. [Autenticación y roles](#autenticación-y-roles)
8. [Base de datos](#base-de-datos)
9. [Entorno con Docker Compose](#entorno-con-docker-compose)
   - [Arranque rápido](#arranque-rápido)
   - [Verificación pendiente con Docker](#verificación-pendiente-con-docker)
10. [Testing](#testing)
11. [Frontend](#frontend)

---

## Alcance de la Iteración 1

La API de M3 tiene **16 endpoints propios**. En la Iteración 1 se cubren **10**.

Los 10 endpoints de la Iteración 1:

- `POST /conductores`, `GET /conductores` y `GET /conductores/{id_conductor}`
- `GET` y `POST /conductores/{id_conductor}/habilitacion`
- `POST /conductores/{id_conductor}/documentacion` (la licencia)
- `POST` y `GET /conductores/{id_conductor}/vehiculos`, y `GET /conductores/{id_conductor}/vehiculos/{id_vehiculo}`
- `POST /conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion`

---

## Arquitectura y estructura del repositorio

M3 tiene una **API en FastAPI**, su **propia base PostgreSQL**, **Keycloak** para los tokens y un **frontend en Next.js**. Todo se levanta con Docker Compose.

El backend se divide en dos mitades que se comunican por interfaces (puertos) definidas en `specs/iteracion1/contracts/casos-de-uso.md`:

- **Lógica:** reglas del negocio, casos de uso y repositorios.
- **Servidor:** la API FastAPI. Llama a los casos de uso, valida el token y devuelve los errores en el formato del contrato.

### Tecnologías

| Parte | Tecnología |
|---|---|
| API | Python 3.12, FastAPI, Uvicorn, pydantic-settings, PyJWT |
| Gestor de dependencias | uv |
| Base de datos | PostgreSQL, SQLAlchemy, Alembic, psycopg |
| Identidad | Keycloak 26.8.1 |
| Frontend | Next.js 16.4, React 19.3, TypeScript 5.9, Node 24 LTS |
| Tests | pytest, pytest-cov, Testcontainers, openapi-core, httpx, Vitest con Testing Library |
| Calidad de código | ruff |
| Contenedores | Docker y Docker Compose |
| CI | GitHub Actions |


### Estructura de carpetas

```
.
├── backend/
│   ├── app/
│   │   ├── dominio/                     # Entidades y reglas del negocio
│   │   ├── aplicacion/
│   │   │   ├── casos_de_uso/            # Un caso de uso por operación
│   │   │   └── puertos/                 # Interfaces (repositorios, unidad de trabajo, reloj)
│   │   ├── infraestructura/
│   │   │   ├── repositorios/            # Repositorios SQL
│   │   │   └── db/                      # Modelos SQLAlchemy y sesión
│   │   └── api/
│   │       ├── routers/                 # Endpoints FastAPI
│   │       └── esquemas/                # Esquemas de entrada y salida
│   ├── tests/
│   │   ├── unitarios/
│   │   ├── integracion/                 # Repositorios y concurrencia (Testcontainers)
│   │   ├── api/
│   │   ├── contrato/
│   │   └── infra/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── ruff.toml
│   └── .coveragerc
├── infra/
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── postgres/init/                   # Creación de las bases
│   ├── migraciones/                     # Alembic
│   ├── seed/                            # Datos de prueba
│   └── keycloak/realm-m3.json
├── frontend/                            # Next.js
├── docs/
│   └── contract/openapi.yaml            # Contrato de la API
└── .github/                             # Workflows de CI y scripts
```

---

## Contrato de la API

- Especificación: [`docs/contract/openapi.yaml`](./docs/contract/openapi.yaml) (OpenAPI 3.0.3), versión 1.0.0.
- **El contrato dirige:** no se implementa ningún endpoint que no esté en el `openapi.yaml`.
- URL base en desarrollo local: `http://localhost:8080/api/v1`
- Formato: JSON.
- Seguridad: Bearer JWT (`bearerAuth`) en todos los endpoints.

### Endpoints propios de M3

| Método | Ruta | Descripción | Iter. |
|---|---|---|---|
| `POST` | `/conductores` | Crear conductor. Queda `PENDIENTE`, desconectado y no disponible. | 1 |
| `GET` | `/conductores` | Listar conductores. Filtros: `disponible`, `habilitado`, `tipo_vehiculo`, `tipo_servicio`, `latitud`, `longitud`. | 1 |
| `GET` | `/conductores/{id_conductor}` | Obtener conductor con documentos, vehículos y habilitación. | 1 |
| `GET` | `/conductores/{id_conductor}/habilitacion` | Estado e historial de habilitación. | 1 |
| `POST` | `/conductores/{id_conductor}/habilitacion` | Aprobar, observar, suspender o rechazar conductor. Solo operadores. | 1 |
| `POST` | `/conductores/{id_conductor}/documentacion` | Registrar la licencia del conductor. | 1 |
| `POST` | `/conductores/{id_conductor}/vehiculos` | Registrar vehículo. | 1 |
| `GET` | `/conductores/{id_conductor}/vehiculos` | Listar vehículos del conductor. Filtros: `tipo`, `habilitacion`. | 1 |
| `GET` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}` | Obtener vehículo. | 1 |
| `POST` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion` | Aprobar, observar, suspender o rechazar vehículo. Solo operadores. | 1 |
| `GET` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` | Tipos de servicio del vehículo y su habilitación. | 2 |
| `POST` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | Registrar documentación del vehículo (`SEGURO`, `CEDULA_VERDE`, `VTV`). | 2 |
| `PATCH` | `/conductores/{id_conductor}/estado` | Actualizar conexión, disponibilidad y ubicación. | 2 |
| `GET` | `/conductores/{id_conductor}/solicitudes` | Listar solicitudes del conductor. | 2 |
| `POST` | `/solicitudes/{id_solicitud}` | Aceptar o rechazar una solicitud. | 2 |
| `POST` | `/viajes/{id_viaje}/calificacion-cliente` | Calificar al cliente. | 2 |

### Detalle de los endpoints de la Iteración 1

**Conductores**

- `POST /conductores` responde `201` con el encabezado `Location` y el conductor creado. Campos: `dni`, `nombre`, `apellido`, `telefono`, `email`.
- `GET /conductores` filtra por `habilitado` (`true` solo con habilitación `APROBADA`), `disponible` y `tipo_vehiculo`.
- `GET /conductores/{id_conductor}` devuelve el conductor con sus documentos (con el estado calculado) y sus vehículos resumidos.

> ⚠️ **En la Iteración 1 los parámetros `latitud` y `longitud` de `GET /conductores` se aceptan pero se ignoran:** no filtran ni ordenan. Esa funcionalidad queda para la Iteración 2.

**Habilitación**

- `GET .../habilitacion` devuelve el estado actual y el historial en orden cronológico.
- `POST .../habilitacion` recibe `accion` (`APROBAR`, `OBSERVAR`, `SUSPENDER`, `RECHAZAR`) y `motivo` (obligatorio). Responde con el estado y los eventos. El `id_operador` se toma del token.
- Solo puede usarlo un usuario con rol **operador**.

**Licencia del conductor**

- `POST .../documentacion` registra la licencia (`tipo` = `LICENCIA`) con `numero`, `categoria` (opcional), `fecha_emision`, `fecha_vencimiento` y `url_archivo`.
- Responde `201` con el estado calculado: `VIGENTE` o `VENCIDO`.

**Vehículos**

- `POST .../vehiculos` registra un vehículo (`AUTO` o `MOTO`) con `patente`, `marca`, `modelo`, `anio` y `tipos_serv` (al menos uno, sin repetidos).
- `GET .../vehiculos` lista los vehículos del conductor. Filtros: `tipo` y `habilitacion`.
- `GET .../vehiculos/{id_vehiculo}` devuelve el vehículo. Si es de otro conductor, responde `404`.
- `POST .../vehiculos/{id_vehiculo}/habilitacion` funciona igual que la del conductor, pero sobre el vehículo.

### Endpoints de M6 que consumimos

Están en el contrato bajo el tag **Externo (M6)**: _implementado por M6, solo consumido por M3_. No forman parte del alcance de la Iteración 1.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/viajes/{id_viaje}` | Consultar estado y resumen del viaje. |
| `POST` | `/viajes/{id_viaje}/finalizar` | Finalizar un viaje en curso. Body: `tiempo` (minutos), `distancia` (km), `cierre`. |
| `POST` | `/viajes/{id_viaje}/cancelar` | Cancelar un viaje. Motivos: `OTRO`, `DEFECTO MECANICO`, `PASAJERO NO VINO`. |

---

## Integración con otros módulos

Según la consigna, las integraciones clave de M3 son **M1, M4, M5 y M6**. Esta tabla muestra qué aparece hoy en el contrato.

| Módulo | Qué aparece en el contrato | Qué recibimos / qué entregamos |
|---|---|---|
| **M1 - Identidad y Acceso** | Todos los endpoints usan seguridad `bearerAuth` (JWT). | ⚠️ *Por definir.* |
| **M4 - Ubicación y Disponibilidad** | La ubicación (`latitud`, `longitud`, `fecha_act_ubic`) aparece en `GET /conductores`, `GET /conductores/{id}` y `PATCH /conductores/{id}/estado`. | ⚠️ *Por definir.* |
| **M5 - Solicitud y Despacho** | El contrato define `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`, con el esquema `Solicitud`. |⚠️ *Por definir.* |
| **M6 - Viajes y Ciclo de Vida** | Consumimos de M6: `GET /viajes/{id}`, `POST /viajes/{id}/finalizar` y `POST /viajes/{id}/cancelar`. | Consumimos esos tres endpoints. Lo demás, ⚠️ *Por definir.* |

Los endpoints relacionados con M4, M5 y M6 (solicitudes, estado y ubicación, viajes) corresponden a la **Iteración 2**.

---

## Reglas de negocio

**Conductores**

- Un conductor nuevo queda con habilitación `PENDIENTE`, `conectado` en falso y `disponible` en falso.
- El DNI debe tener 7 u 8 dígitos (`^[0-9]{7,8}$`). `nombre`, `apellido` y `telefono` son obligatorios, y el email debe tener formato válido.
- No puede haber dos conductores con el mismo DNI.

**Habilitación (conductor y vehículo)**

- Cada acción exige un `motivo` no vacío y queda registrada como un evento con estado anterior, estado nuevo, motivo, `id_operador` y fecha. El historial es de solo escritura (no se modifica ni se borra).
- Al crear un conductor o un vehículo se genera un evento `ALTA` generado por el sistema (sin estado anterior ni operador).
- Transiciones válidas del conductor:

| Estado actual | Puede pasar a |
|---|---|
| `PENDIENTE` | `APROBADA`, `OBSERVADA`, `RECHAZADA` |
| `OBSERVADA` | `APROBADA`, `RECHAZADA` |
| `APROBADA` | `SUSPENDIDA` |
| `SUSPENDIDA` | `APROBADA`, `RECHAZADA` |
| `RECHAZADA` | _(estado final)_ |

- Cualquier otra transición se rechaza con `TRANSICION_INVALIDA`.
- **Para aprobar a un conductor tiene que tener una licencia `VIGENTE`.** Sin licencia, o con licencia `VENCIDO`, se rechaza con `LICENCIA_VIGENTE_REQUERIDA` y el estado no cambia.
- La aprobación de un vehículo no tiene la regla de la licencia. Además, un vehículo de otro conductor se trata como inexistente.
- Para registrar una habilitación, la unidad de trabajo bloquea la fila (`SELECT ... FOR UPDATE`) y el estado y el evento se guardan en la misma transacción.

**Documentación**

- El estado es `VIGENTE` si `fecha_vencimiento` es igual o posterior a hoy, y `VENCIDO` si es anterior.
- `fecha_vencimiento` debe ser posterior a `fecha_emision`, y `url_archivo` debe ser una URI válida.

**Vehículos**

- El tipo es `AUTO` o `MOTO`. Tiene que tener al menos un tipo de servicio (`PASAJEROS` o `ENVIOS`), sin repetidos.
- Un vehículo nuevo queda `PENDIENTE` y todos sus tipos de servicio quedan sin habilitar.
- No puede haber dos vehículos con la misma patente.

**Concurrencia**

- Si dos pedidos llegan a la vez con el mismo DNI o la misma patente, gana uno y el otro recibe `409`.
- Si dos acciones de habilitación llegan a la vez sobre el mismo conductor, una se aplica y la otra recibe `409`.

---

## Errores

Todos los errores usan el mismo formato:

```json
{
  "codigo": "string",
  "mensaje": "string"
}
```

| HTTP | Código | Cuándo |
|---|---|---|
| `400` | `SOLICITUD_INVALIDA` | La forma del pedido no cumple el contrato (DNI inválido, motivo vacío, sin tipos de servicio, etc.). |
| `401` | _(por definir)_ | Token ausente, malformado, con firma inválida, vencido o de otro emisor. |
| `403` | _(por definir)_ | Sin permisos: acción de habilitación sin rol operador, o token de operador sin `id_operador` numérico. |
| `404` | `NO_ENCONTRADO` | El recurso no existe. |
| `409` | `DNI_DUPLICADO` | Ya existe un conductor con ese DNI. |
| `409` | `PATENTE_DUPLICADA` | Ya existe un vehículo con esa patente. |
| `409` | `TRANSICION_INVALIDA` | La transición de habilitación no está permitida. |
| `410` | _(por definir)_ | La oferta de una solicitud venció (`POST /solicitudes/{id_solicitud}`, Iteración 2). |
| `422` | `LICENCIA_VIGENTE_REQUERIDA` | Se intenta aprobar un conductor sin licencia vigente. |
| `422` | `DATOS_INVALIDOS` | Se incumple una regla de negocio (por ejemplo, vencimiento anterior a la emisión). |
| `500` | `ERROR_INTERNO` | Error inesperado. No expone detalles internos. |


---

## Autenticación y roles

- Todos los endpoints requieren `Authorization: Bearer <JWT>`.
- Los tokens los emite **Keycloak** y la API los valida localmente con PyJWT y el JWKS (con caché).
- Roles: **`operador`** y **`conductor`**.
- Las acciones de habilitación solo pueden hacerlas usuarios con rol `operador`.
- El usuario operador tiene un atributo numérico `id_operador`, que Keycloak incluye en el token como un claim entero. La API lo usa para registrar quién hizo cada acción.

**Realm de Keycloak** (`infra/keycloak/realm-m3.json`):

- Realm: `m3`.
- Roles `operador` y `conductor`, con usuarios de prueba.
- Cliente confidencial con concesión de contraseña habilitada.
- No contiene secretos ni contraseñas literales: se sustituyen por variables de entorno (`${VARIABLE}`).

---

## Base de datos

M3 tiene su **propia base de datos** y nunca consulta tablas de otro módulo (RNF-05).

- Hay dos bases separadas en la misma instancia de PostgreSQL: `m3` y `keycloak`, con usuarios distintos. El usuario de `m3` no puede conectarse a la base de `keycloak`.
- El esquema cambia **solo con migraciones de Alembic**.

**Tablas**

| Tabla | Contenido |
|---|---|
| `conductor` | Datos del conductor. `dni` único. Habilitación inicial `PENDIENTE`; `conectado` y `disponible` en falso por defecto. |
| `vehiculo` | Datos del vehículo. `patente` única. |
| `vehiculo_tipo_servicio` | Tipos de servicio de cada vehículo y si están habilitados. |
| `documento_conductor` | Licencia del conductor. |
| `habilitacion_evento_conductor` | Historial de habilitación del conductor. |
| `habilitacion_evento_vehiculo` | Historial de habilitación del vehículo. |

Hay restricciones `CHECK` en los estados de habilitación, el tipo de vehículo (`AUTO`/`MOTO`), los tipos de servicio (`PASAJEROS`/`ENVIOS`) y la acción. También hay claves foráneas.

**Comandos**

```bash
alembic upgrade head     # crea el esquema
alembic downgrade base   # lo elimina
```

Las migraciones están en `infra/migraciones/` (`alembic.ini`, `env.py` y `versions/0001_esquema_inicial.py`).

**Datos de prueba (seed)**

`infra/seed/cargar_datos.py` carga datos de forma determinista e idempotente (correrlo dos veces no duplica nada). Incluye:

- Conductores en distintos estados de habilitación.
- Al menos uno con licencia `VIGENTE` y otro con licencia `VENCIDO`.
- Al menos uno con `conectado` y `disponible` verdaderos.
- Al menos un vehículo.
- Un evento `ALTA` por cada entidad.

---

## Entorno con Docker Compose

Un único comando levanta API, PostgreSQL y Keycloak.

| Servicio | Descripción |
|---|---|
| `postgres` | PostgreSQL con versión fija. Crea las bases `m3` y `keycloak`. |
| `keycloak` | Keycloak 26.8.1, importa el realm `m3`. |
| `migraciones` y `seed` | Se ejecutan una sola vez: aplican las migraciones y cargan los datos de prueba. |
| `api` | La API de M3, construida con `backend/Dockerfile`. |

Puertos: PostgreSQL `5432`, Keycloak `8081` y API `8080`.

- Los servicios tienen chequeos de salud y `depends_on` con condición.
- Las imágenes tienen versión fija, **nunca `latest`**.
- Las contraseñas y claves se configuran **por variables de entorno**, nunca en el repo. `infra/.env.example` lista todas las variables sin valores reales.
- El `Dockerfile` usa una imagen `python:3.12` de versión fija, corre con un usuario sin privilegios e inicia la API con `uvicorn app.api.main:app --host 0.0.0.0 --port 8080`.

### Arranque rápido

El stack completo de M3 (PostgreSQL, Keycloak, migraciones, seed y API) se levanta con Docker Compose.

1. Copiar el archivo de variables y completar **todos** los valores vacíos. No commitear `infra/.env`.

   ```bash
   cd infra
   cp .env.example .env
   ```

   Generar claves con `openssl rand -hex 32`. Se recomienda hexadecimal para que las contraseñas puedan usarse sin URL-encoding dentro de `DATABASE_URL` (el compose la compone a partir de `M3_DB_PASSWORD`).

2. Levantar el stack (la primera vez compila la imagen de la API):

   ```bash
   docker compose --env-file .env -f docker-compose.yml up --build
   ```

   El orden está garantizado por healthchecks: PostgreSQL → Keycloak y migraciones → seed → API. El seed es idempotente y puede volver a ejecutarse sin duplicar datos.

3. Verificar los servicios:

   | Servicio | URL / puerto |
   |---|---|
   | API (salud) | http://localhost:8080/salud |
   | Keycloak | http://localhost:8081 (realm `m3`) |
   | PostgreSQL | localhost:5432 |

   Obtener un token de prueba del operador (cliente confidencial con password grant). Cargar primero las variables en la shell:

   ```bash
   set -a
   . ./.env
   set +a
   curl -s -X POST http://localhost:8081/realms/m3/protocol/openid-connect/token \
     -d grant_type=password \
     -d client_id=m3-api \
     -d client_secret="$KEYCLOAK_M3_CLIENT_SECRET" \
     -d username=operador.m3 \
     -d password="$M3_OPERADOR_PASSWORD"
   ```

4. Ejecutar las pruebas de infraestructura (requieren Docker para las marcadas como `integration`). Desde `infra`:

   ```bash
   cd ../backend
   uv sync --all-groups
   uv run pytest tests/infra
   ```

5. Detener el stack. Volver a `infra`:

   ```bash
   cd ../infra
   docker compose --env-file .env -f docker-compose.yml down
   ```

   Si además querés eliminar el volumen de PostgreSQL y forzar la re-inicialización de las bases, agregá `-v` al final: `docker compose --env-file .env -f docker-compose.yml down -v`.

Para ejecutar migraciones o el seed manualmente contra una base existente, desde la raíz del repositorio:

```bash
cd backend
export DATABASE_URL="postgresql+psycopg://m3:CLAVE@localhost:5432/m3"
uv run alembic -c ../infra/migraciones/alembic.ini upgrade head
uv run python ../infra/seed/cargar_datos.py
```

### Verificación pendiente con Docker

El código, el esquema, las migraciones (DDL offline), el seed (simulación) y las pruebas estáticas ya fueron validados. En el entorno de desarrollo usado para preparar esta entrega **no había un daemon de Docker operativo**, por lo que quedan pendientes de ejecutar:

- `docker compose --env-file .env -f docker-compose.yml config` para comprobar la interpolación de variables.
- El build de `backend/Dockerfile` y del tag temporal `m3-backend:local`.
- La inicialización de PostgreSQL y el script `infra/postgres/init/01-crear-bases.sh` (creación de roles, bases y revocación de `CONNECT`).
- `alembic upgrade head` y `alembic downgrade base` contra PostgreSQL real.
- La ejecución real del seed y su segunda ejecución para confirmar la idempotencia en PostgreSQL.
- La importación de `realm-m3.json` en Keycloak, la sustitución de `${...}` y la obtención de un token con `operador.m3`.
- Los healthchecks de Keycloak (puerto de administración 9000) y de la API, y el orden `postgres → keycloak/migraciones → seed → API`.
- Los 15 tests marcados como `integration` (Testcontainers), omitidos automáticamente al no detectar Docker.

---

## Testing

Se trabaja con **TDD**: primero un test que falla, después el código mínimo para que pase y, si hace falta, un refactor. Una tarea sin test no está terminada.

### Tipos de test

| Tipo | Carpeta | Qué verifica |
|---|---|---|
| Unitarios | `backend/tests/unitarios/` | Dominio y casos de uso, con repositorios en memoria. |
| API | `backend/tests/api/` | Endpoints, seguridad y errores, con casos de uso simulados y tokens de prueba. |
| Integración | `backend/tests/integracion/` | Repositorios SQL contra PostgreSQL real (Testcontainers). |
| Infraestructura | `backend/tests/infra/` | Bases, esquema, migraciones, seed y realm de Keycloak. |
| Contrato | `backend/tests/contrato/` | Las respuestas cumplen el `openapi.yaml`. |
| Concurrencia | `backend/tests/integracion/concurrencia/` | 20 solicitudes simultáneas con el mismo DNI dan exactamente un `201` y 19 `409`. Lo mismo con la patente. Dos acciones de habilitación simultáneas: una se aplica y la otra recibe `409`. |
| Humo | `.github/scripts/humo.sh` | Levanta el Compose, pide un token de operador a Keycloak y verifica que `GET /api/v1/conductores` dé `200` con al menos un conductor y `401` sin token. |

### Comandos

```bash
cd backend
uv sync --group dev                                     # instalar dependencias
uv run pytest tests/unitarios --cov=app                 # tests unitarios con cobertura
uv run pytest --cov --cov-fail-under=65                 # toda la suite con cobertura mínima
```

**Cobertura:** mínimo **65%** en la API (`fail_under = 65` en `backend/.coveragerc`). El objetivo es estar entre 65% y 70% o más sobre lo implementado.

Los tests de infraestructura se ejecutan con el entorno descrito en [Arranque rápido](#arranque-rápido).

---

## Frontend

Una sola pantalla que muestra el **listado de conductores** consumiendo la API.

- Stack: Next.js 16.4, React y React DOM 19.3, TypeScript 5.9, Node 24 (`.nvmrc`). Tests con Vitest y Testing Library.
- La pantalla (`frontend/src/app/page.tsx`) es un **componente de servidor**: el servidor de Next pide el token a Keycloak y llama a la API, así que las credenciales nunca llegan al navegador.
- El token se pide a `/realms/m3/protocol/openid-connect/token` con concesión de contraseña y se reutiliza hasta su vencimiento.
- Muestra nombre, apellido, DNI y habilitación de cada conductor. Tiene un estado vacío ("No hay conductores") y un estado de error con un mensaje claro.

Para tener la API y Keycloak corriendo, ver [Arranque rápido](#arranque-rápido).

**Variables de entorno** (`frontend/.env.example`): `API_URL`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `TEST_USER`, `TEST_PASSWORD`.

**Scripts**

```bash
npm run dev     # correr la pantalla
npm run build
npm run lint
npm run test
```

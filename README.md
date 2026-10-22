# M3 - Conductores y Vehículos

Módulo **M3** de la plataforma distribuida de movilidad urbana bajo demanda (Desarrollo de Software - 2026).

| **ID** | **Módulo** | **Responsabilidad** | **Integraciones clave** |
|---|---|---|---|
| **M3** | **Conductores y Vehículos** | Perfil, habilitación, vehículos, documentación y estado operativo. | M1, M4, M5, M6. |

> Grupo: 15 · Integrantes: Araujo Sabrina, Balbuena Yusva Mario, Barbagallo Lucas, Dellamea Santiago, Escobar Gonzalo, Fernandez Oriana, Fuentes Victor, Sanchez Brisa, Saravia Agustina 

---

## Índice

1. [Contrato de la API](#contrato-de-la-api)
2. [Endpoints principales](#endpoints-principales)
3. [Reglas que define el contrato](#reglas-que-define-el-contrato)
4. [Integración con otros módulos](#integración-con-otros-módulos)
5. [Autenticación y errores](#autenticación-y-errores)
6. [Pendientes marcados en el contrato](#pendientes-marcados-en-el-contrato)
7. [Arranque rápido](#arranque-rápido-m3)

---

## Contrato de la API

- Especificación: [`openapi.yaml`](./openapi.yaml) (OpenAPI 3.0.3), versión 1.0.0
- URL base en desarrollo local: `http://localhost:8080/api/v1`
- Formato: JSON
- Seguridad: Bearer JWT (`bearerAuth`), aplicado a todos los endpoints

---

## Endpoints principales

### Conductores

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/conductores` | Crear conductor. Queda con habilitación `PENDIENTE`, desconectado y no disponible. |
| `GET` | `/conductores` | Listar conductores. Filtros opcionales: `latitud`, `longitud`, `disponible`, `habilitado`, `tipo_vehiculo`, `tipo_servicio`. Con latitud y longitud ordena por cercanía y excluye ubicaciones vencidas. `habilitado=true` es solo con habilitación `APROBADA`. |
| `GET` | `/conductores/{id_conductor}` | Obtener conductor (incluye documentos, vehículos, habilitación, estado de conexión/disponibilidad y ubicación). |

### Vehículos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/conductores/{id_conductor}/vehiculos` | Registrar vehículo. Los tipos de servicio quedan sin habilitar hasta su aprobación. |
| `GET` | `/conductores/{id_conductor}/vehiculos` | Listar vehículos del conductor. Filtros: `tipo`, `habilitacion`. |
| `GET` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}` | Obtener vehículo. |
| `GET` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/tipos-servicio` | Tipos de servicio del vehículo y su habilitación. |

### Documentación

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/conductores/{id_conductor}/documentacion` | Registrar documentación del conductor (tipo `LICENCIA`). |
| `POST` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/documentacion` | Registrar documentación del vehículo (tipos `SEGURO`, `CEDULA_VERDE`, `VTV`). |

Campos de los documentos: tipo, número, fecha de emisión, fecha de vencimiento y URL del archivo. El conductor suma `categoria` y el vehículo suma `entidad_emisora`, ambos opcionales. El estado del documento (`VIGENTE` / `VENCIDO`) es según `fecha_vencimiento`.

### Habilitación

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/conductores/{id_conductor}/habilitacion` | Consultar habilitación del conductor (estado e historial). |
| `POST` | `/conductores/{id_conductor}/habilitacion` | Aprobar, observar, suspender o rechazar conductor. Solo operadores autorizados. Registra un evento con motivo, operador y fecha. |
| `POST` | `/conductores/{id_conductor}/vehiculos/{id_vehiculo}/habilitacion` | Aprobar, observar, suspender o rechazar vehículo. Solo operadores autorizados. |

Acciones posibles: `APROBAR`, `OBSERVAR`, `SUSPENDER`, `RECHAZAR` (el `motivo` es obligatorio).
Estados posibles: `PENDIENTE`, `OBSERVADA`, `APROBADA`, `SUSPENDIDA`, `RECHAZADA`.

### Disponibilidad

| Método | Ruta | Descripción |
|---|---|---|
| `PATCH` | `/conductores/{id_conductor}/estado` | Actualizar conexión y disponibilidad. Requiere conductor y vehículo activo habilitados. Opcionalmente actualiza la ubicación. |

Campos del body (al menos uno): `conectado`, `disponible`, `id_vehiculo_activo`, `latitud`, `longitud` (cada coordenada requiere la otra).

### Solicitudes

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/conductores/{id_conductor}/solicitudes` | Listar solicitudes del conductor. Filtro: `estado` (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`). |
| `POST` | `/solicitudes/{id_solicitud}` | Aceptar o rechazar una solicitud. Solo mientras la oferta esté vigente; vencida devuelve `410`. |

### Calificación

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/viajes/{id_viaje}/calificacion-cliente` | Calificar al cliente. Solo viajes completados, una calificación por viaje. Puntaje de 1 a 5 y comentario opcional (máx. 500 caracteres). |

### Endpoints de M6 que consumimos

Están en el contrato bajo el tag **Externo (M6)**: _implementado por M6, solo consumido por M3_.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/viajes/{id_viaje}` | Consultar estado y resumen del viaje. |
| `POST` | `/viajes/{id_viaje}/finalizar` | Finalizar un viaje en curso. Permite al conductor finalizar el viaje registrando los datos necesarios de tiempo y distancia. Body: `tiempo` (minutos), `distancia` (km), `cierre`. |
| `POST` | `/viajes/{id_viaje}/cancelar` | Cancelar un viaje. Permite al conductor cancelar el viaje registrando motivo. Motivos: `OTRO`, `DEFECTO MECANICO`, `PASAJERO NO VINO`. |

---

## Reglas que define el contrato

- Un conductor nuevo queda con habilitación `PENDIENTE`, desconectado y no disponible.
- Los tipos de servicio de un vehículo (`PASAJEROS`, `ENVIOS`) quedan sin habilitar hasta su aprobación. Al registrar un vehículo hay que indicar al menos un tipo de servicio.
- Los vehículos pueden ser `AUTO` o `MOTO`.
- `PATCH /estado` requiere conductor y vehículo activo habilitados.
- Habilitar, observar, suspender o rechazar requiere motivo, y solo lo pueden hacer operadores autorizados.
- Responder una solicitud vencida devuelve `410`.
- Calificar al cliente: solo viajes completados y una calificación por viaje.
- DNI del conductor: 7 u 8 dígitos.

---

## Integración con otros módulos

Las integraciones clave de M3 son **M1, M4, M5 y M6**. 

| Módulo | Qué aparece en el contrato | Qué recibimos / qué entregamos |
|---|---|---|
| **M1 - Identidad y Acceso** | Todos los endpoints usan seguridad `bearerAuth` (JWT). | ⚠️ ***DEFINIR*** Por definir. |
| **M4 - Ubicación y Disponibilidad** | La ubicación (`latitud`, `longitud`, `fecha_act_ubic`) aparece en `GET /conductores`, `GET /conductores/{id}` y `PATCH /conductores/{id}/estado`. | Por definir. ⚠️ ***DEFINIR*** El contrato tiene pendiente confirmar con M4 cómo se reporta la ubicación. |
| **M5 - Solicitud y Despacho** | El contrato define `GET /conductores/{id}/solicitudes` y `POST /solicitudes/{id}`, con el esquema `Solicitud` y sus estados. | Por definir. ⚠️ ***DEFINIR*** El contrato tiene pendiente confirmar con M5 los estados y campos de `Solicitud`. |
| **M6 - Viajes y Ciclo de Vida** | Consumimos de M6: `GET /viajes/{id}`, `POST /viajes/{id}/finalizar` y `POST /viajes/{id}/cancelar`. | Consumimos esos tres endpoints. Lo que M6 recibe de nosotros además de eso queda por definir. ⚠️ ***DEFINIR*** El contrato tiene pendiente confirmar con M6 los estados y campos de `Viaje`. |

---

## Autenticación y errores

- Esquema de seguridad: `bearerAuth` (HTTP Bearer, formato JWT).
- Todos los errores usan el mismo formato:

```json
{
  "codigo": "string",
  "mensaje": "string"
}
```

| Código | Significado |
|---|---|
| `400` | Solicitud mal formada |
| `401` | Token ausente o inválido |
| `403` | Sin permisos |
| `404` | Recurso inexistente |
| `409` | Duplicado o transición inválida |
| `410` | Oferta vencida |
| `422` | Incumple una regla de negocio |
| `500` | Error interno |

---

## Arranque rápido (M3)

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

5. Detener el stack. `-v` elimina también el volumen de PostgreSQL y fuerza la re-inicialización de las bases. Volver a `infra`:

   ```bash
   cd ../infra
   docker compose --env-file .env -f docker-compose.yml down
   ```

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

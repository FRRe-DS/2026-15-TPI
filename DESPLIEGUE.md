# Levantar M3 de punta a punta

Guía de ejecución local en Windows con PowerShell. Se omite la instalación de requisitos previos.

PostgreSQL, Keycloak, la API y el frontend Next.js se ejecutan juntos con un único `docker-compose.yml` en la raíz del repositorio.

## 1. Iniciar Docker y entrar al proyecto

Abrí Docker Desktop y esperá a que el motor termine de iniciar. En PowerShell:

```powershell
cd C:\ruta\2026-15-TPI
docker info
```

`cd` entra en el proyecto: reemplazá la ruta por la ubicación real. `docker info` comprueba que el motor de Docker responda.

## 2. Configurar las variables

Desde la raíz:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
notepad .env
```

Crea el archivo local si no existe y lo abre para editar. Conservá los valores existentes si ya funciona.

Completá todos los campos vacíos:

| Variable | Valor que debés definir |
|---|---|
| `POSTGRES_PASSWORD` | Contraseña del administrador de PostgreSQL. |
| `M3_DB_PASSWORD` | Contraseña de la base de M3. |
| `KEYCLOAK_DB_PASSWORD` | Contraseña de la base de Keycloak. |
| `KEYCLOAK_ADMIN` | Usuario administrador de Keycloak, por ejemplo `admin`. |
| `KEYCLOAK_ADMIN_PASSWORD` | Contraseña del administrador de Keycloak. |
| `KEYCLOAK_M3_CLIENT_SECRET` | Secreto del cliente `m3-api`. |
| `M3_OPERADOR_PASSWORD` | Contraseña del usuario `operador.m3`. |
| `M3_CONDUCTOR_PASSWORD` | Contraseña del usuario `conductor.m3`. |
| `REDIS_PASSWORD` | Contraseña obligatoria de Redis. Generá un valor aleatorio y no lo subas al repositorio. |
| `RATE_LIMIT_HMAC_SECRET` | Clave aleatoria obligatoria para anonimizar las identidades de cuota; usá un secreto distinto de `REDIS_PASSWORD` y no lo versionés. |

Para generar un valor aleatorio hexadecimal:

```powershell
[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
```

Genera 64 caracteres. Repetilo para cada contraseña o secreto. Usar hexadecimal evita problemas con caracteres especiales en la URL de PostgreSQL.

Conservá los nombres del ejemplo: bases `m3` y `keycloak`, realm `m3`, cliente `m3-api`, usuarios `operador.m3` y `conductor.m3`. Los nombres de los usuarios y del cliente importados están definidos en `infra/keycloak/realm-m3.json`.

Redis es interno al stack y no publica un puerto al host. `REDIS_PASSWORD` debe tener un valor antes de ejecutar `docker compose config` o levantar los servicios. Podés usar el comando de GUID concatenados de arriba para generar una contraseña hexadecimal. No versionés `.env`.
`RATE_LIMIT_HMAC_SECRET` debe tener al menos 32 caracteres y el mismo valor en todas las instancias de API. Generá un valor independiente con el comando de GUID concatenados y guardalo solo en `.env` o en el gestor de secretos del entorno.

Esta guía usa los puertos del ejemplo: PostgreSQL `5432`, API `8080`, Keycloak `8081` y frontend `3000`. Guardá el archivo sin subir las credenciales al repositorio.

## 3. Levantar todo el stack

Desde la raíz:

```powershell
docker compose config --quiet
```

Valida la configuración sin iniciar los servicios ni imprimir las credenciales. Revisá también las advertencias sobre variables faltantes.

```powershell
docker compose up --build -d
```

Descarga imágenes, construye el backend y el frontend y levanta el entorno:

1. PostgreSQL inicia y crea las bases en el primer arranque del volumen.
2. Keycloak inicia e importa el realm; las migraciones crean o actualizan las tablas de M3.
3. El seed carga datos de prueba después de las migraciones.
4. La API inicia cuando Keycloak está saludable y migraciones y seed terminaron correctamente.
5. El frontend inicia cuando la API está saludable.

Las opciones significan:

- `up`: crea e inicia los servicios.
- `--build`: construye las imágenes locales.
- `-d`: deja los servicios en segundo plano.

La primera ejecución tarda más por las descargas. No necesitás iniciar Python ni instalar las dependencias del backend en tu computadora: se ejecuta dentro de Docker.

## 4. Comprobar el backend

```powershell
docker compose ps -a
```

Muestra los contenedores. Esperá que `postgres`, `keycloak`, `api` y `frontend` estén iniciados y saludables. `migraciones` y `seed` deben terminar con `Exited (0)`: son tareas de ejecución única.

```powershell
docker compose logs --tail 100 migraciones seed api keycloak
```

Muestra los últimos mensajes del arranque. Para seguir todos los mensajes en vivo:

```powershell
docker compose logs -f
```

`Ctrl+C` deja de seguir los mensajes sin detener los contenedores.

```powershell
Invoke-RestMethod http://localhost:8080/salud
```

Consulta la sonda de la API, que debe devolver `estado` con valor `ok`. Esta sonda verifica que el proceso responda; la consulta autenticada del paso 6 comprueba el recorrido de la aplicación.

| Servicio | Dirección |
|---|---|
| Salud de la API | http://localhost:8080/salud |
| Swagger | http://localhost:8080/docs |
| API de negocio | http://localhost:8080/api/v1 |
| Keycloak | http://localhost:8081 |
| PostgreSQL | `localhost:5432` |
| Frontend | http://localhost:3000 |

La consola de administración de Keycloak usa `KEYCLOAK_ADMIN` y `KEYCLOAK_ADMIN_PASSWORD`. El realm de la aplicación es `m3`.

## 5. Abrir el frontend

El frontend ya corre como contenedor y recibe su configuración de `.env`. Entrá a http://localhost:3000: la página debe mostrar los conductores del seed. Esto comprueba el recorrido navegador → Next.js → Keycloak y API → PostgreSQL.

Para desarrollar con recarga en caliente, detené solo el contenedor y levantá Next.js local:

```powershell
docker compose stop frontend
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Completá `.env.local` con `API_URL=http://localhost:8080/api/v1`, `KEYCLOAK_URL=http://localhost:8081`, `KEYCLOAK_REALM=m3`, `KEYCLOAK_CLIENT_ID=m3-api` y los valores de `KEYCLOAK_M3_CLIENT_SECRET` y `M3_OPERADOR_PASSWORD` de `.env` en `KEYCLOAK_CLIENT_SECRET` y `TEST_PASSWORD` (`TEST_USER=operador.m3`). No agregues `NEXT_PUBLIC_` a estas variables.

## 6. Probar la API con un token real (opcional)

En otra PowerShell, pedí un token del operador. Las credenciales se solicitan de forma interactiva para evitar escribirlas literalmente en el historial:

```powershell
$clientSecret = Read-Host 'KEYCLOAK_M3_CLIENT_SECRET' -AsSecureString
$operatorPassword = Read-Host 'M3_OPERADOR_PASSWORD' -AsSecureString
$tokenBody = @{
    grant_type = 'password'
    client_id = 'm3-api'
    client_secret = [System.Net.NetworkCredential]::new('', $clientSecret).Password
    username = 'operador.m3'
    password = [System.Net.NetworkCredential]::new('', $operatorPassword).Password
}
$tokenResponse = Invoke-RestMethod -Method Post `
    -Uri 'http://localhost:8081/realms/m3/protocol/openid-connect/token' `
    -ContentType 'application/x-www-form-urlencoded' `
    -Body $tokenBody
$tokenBody.Clear()
```

Obtiene un token de Keycloak y lo guarda en memoria sin imprimirlo. Para consultar los conductores:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8080/api/v1/conductores' `
    -Headers @{ Authorization = "Bearer $($tokenResponse.access_token)" }
```

Envía el token a la API. Si vence, repetí la solicitud del token. También podés usar un JWT en el botón **Authorize** de Swagger.

## 7. Arranques siguientes y cambios de código

Abrí Docker Desktop y, desde la raíz:

```powershell
docker compose up -d
```

Inicia los servicios usando las imágenes existentes y conserva los datos del volumen. Si cambió código del backend o del frontend, agregá `--build`: las imágenes no recargan los archivos locales.

Este recorrido es local: el Compose utiliza Keycloak en modo `start-dev`, usuarios de prueba y URLs `localhost`. Publicar en un servidor requiere adaptar dominios, HTTPS y autenticación.

## 8. Cuando el puerto 5432 u otro ya está ocupado

Definí otro valor en `.env` (`POSTGRES_PORT`, `API_PORT`, `KEYCLOAK_PORT` o `FRONTEND_PORT`) y volvé a ejecutar `docker compose up -d`.

## 9. Detener la aplicación

Desde la raíz:

```powershell
docker compose down
```

Detiene y elimina los contenedores y la red del proyecto, conservando los datos de PostgreSQL.

## 10. Borrar los datos y empezar de cero

**Solo para datos descartables:** este comando elimina los datos de M3 y de Keycloak.

```powershell
docker compose down -v
docker compose up --build -d
```

`down -v` elimina también el volumen. El siguiente arranque crea las bases, importa el realm, aplica migraciones y carga el seed nuevamente.

## Problemas frecuentes

| Problema | Qué revisar |
|---|---|
| Docker no conecta | Abrir Docker Desktop y verificar con `docker info`. |
| Puerto ocupado | Liberarlo o cambiar el puerto en `.env` (paso 8). |
| API no inicia | Consultar `ps -a` y los logs de migraciones, seed, Keycloak y API. |
| Frontend no obtiene token | Comparar el secreto, usuario y contraseña con los del realm y comprobar que Keycloak funcione. |
| Frontend no muestra conductores | Revisar `docker compose logs frontend` y que `api` esté saludable. |
| API devuelve `401` | Obtener un token nuevo y verificar que corresponda al realm `m3` local. |
| Seed y migraciones detenidos | Si terminaron con código `0`, es normal. |
| Cambié contraseñas y ahora falla | Las bases existentes y el realm importado conservan sus credenciales. Editar `.env` no las actualiza. Restaurar los valores originales o modificarlas en los servicios; para datos descartables, usar el borrado del paso 10. |

## Comandos rápidos para uso diario

Con las variables ya configuradas, desde la raíz:

```powershell
docker compose up -d
```

Abrí http://localhost:3000.

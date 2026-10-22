# Levantar M3 de punta a punta

Guía de ejecución local en Windows con PowerShell. Se omite la instalación de requisitos previos.

PostgreSQL, Keycloak y la API se ejecutan con Docker Compose. El frontend Next.js se inicia por separado con npm.

## 1. Iniciar Docker y entrar al proyecto

Abrí Docker Desktop y esperá a que el motor termine de iniciar. En PowerShell:

```powershell
cd C:\ruta\2026-15-TPI
docker info
```

`cd` entra en el proyecto: reemplazá la ruta por la ubicación real. `docker info` comprueba que el motor de Docker responda.

## 2. Configurar el backend

Desde la raíz:

```powershell
if (-not (Test-Path infra/.env)) {
    Copy-Item infra/.env.example infra/.env
}
notepad infra/.env
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

Para generar un valor aleatorio hexadecimal:

```powershell
[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
```

Genera 64 caracteres. Repetilo para cada contraseña o secreto. Usar hexadecimal evita problemas con caracteres especiales en la URL de PostgreSQL.

Conservá los nombres del ejemplo: bases `m3` y `keycloak`, realm `m3`, cliente `m3-api`, usuarios `operador.m3` y `conductor.m3`. Los nombres de los usuarios y del cliente importados están definidos en `infra/keycloak/realm-m3.json`.

Esta guía usa los puertos del ejemplo: PostgreSQL `5432`, API `8080` y Keycloak `8081`. Guardá el archivo sin subir las credenciales al repositorio.

## 3. Levantar los servicios Docker

Desde la raíz:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml config --quiet
```

Valida la configuración sin iniciar los servicios ni imprimir las credenciales. Revisá también las advertencias sobre variables faltantes.

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
```

Descarga imágenes, construye el backend y levanta el entorno:

1. PostgreSQL inicia y crea las bases en el primer arranque del volumen.
2. Keycloak inicia e importa el realm; las migraciones crean o actualizan las tablas de M3.
3. El seed carga datos de prueba después de las migraciones.
4. La API inicia cuando Keycloak está saludable y migraciones y seed terminaron correctamente.

Las opciones significan:

- `--env-file`: selecciona las variables locales.
- `-f`: selecciona el archivo Compose.
- `up`: crea e inicia los servicios.
- `--build`: construye las imágenes locales.
- `-d`: deja los servicios en segundo plano.

La primera ejecución tarda más por las descargas. No necesitás iniciar Python ni instalar las dependencias del backend en tu computadora: se ejecuta dentro de Docker.

## 4. Comprobar el backend

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml ps -a
```

Muestra los contenedores. Esperá que `postgres`, `keycloak` y `api` estén iniciados y saludables. `migraciones` y `seed` deben terminar con `Exited (0)`: son tareas de ejecución única.

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml logs --tail 100 migraciones seed api keycloak
```

Muestra los últimos mensajes del arranque. Para seguir todos los mensajes en vivo:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml logs -f
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

La consola de administración de Keycloak usa `KEYCLOAK_ADMIN` y `KEYCLOAK_ADMIN_PASSWORD`. El realm de la aplicación es `m3`.

## 5. Configurar y levantar el frontend

Abrí otra terminal PowerShell:

```powershell
cd C:\ruta\2026-15-TPI\frontend
npm ci
```

Entra al frontend e instala las versiones exactas de `package-lock.json`. Si existe `node_modules`, `npm ci` la reemplaza. Ejecutalo la primera vez y cuando cambien las dependencias.

```powershell
if (-not (Test-Path .env.local)) {
    Copy-Item .env.example .env.local
}
notepad .env.local
```

Crea la configuración local si falta y la abre. Completala así:

```dotenv
API_URL=http://localhost:8080/api/v1
KEYCLOAK_URL=http://localhost:8081
KEYCLOAK_REALM=m3
KEYCLOAK_CLIENT_ID=m3-api
KEYCLOAK_CLIENT_SECRET=PEGAR_EL_VALOR_DE_KEYCLOAK_M3_CLIENT_SECRET
TEST_USER=conductor.m3
TEST_PASSWORD=PEGAR_EL_VALOR_DE_M3_CONDUCTOR_PASSWORD
```

Reemplazá los dos valores indicados por los valores reales de `infra/.env` y guardá el archivo. Next.js pide el token a Keycloak y consulta la API desde el servidor. No hay que pegar un token en la web. No agregues `NEXT_PUBLIC_` a estas variables.

```powershell
npm run dev
```

Inicia el frontend en desarrollo. Dejá la terminal abierta y entrá a http://localhost:3000. Si ese puerto está ocupado, usá la dirección alternativa que informa Next.js.

La página debe mostrar los conductores del seed. Esto comprueba el recorrido navegador → Next.js → Keycloak y API → PostgreSQL.

Si cambiás `.env.local`, detené Next.js con `Ctrl+C` y volvé a ejecutar `npm run dev`.

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
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

Inicia los servicios usando las imágenes existentes y conserva los datos del volumen.

Si cambió código del backend:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
```

Reconstruye la imagen para incluir los cambios. El backend en Docker no recarga automáticamente los archivos locales.

En otra terminal, desde `frontend`, ejecutá `npm run dev`. Repetí `npm ci` si cambiaron las dependencias. No vuelvas a copiar los archivos de variables si ya están configurados.

## 8. Servir el frontend compilado (opcional)

Desde `frontend`, detené el servidor de desarrollo con `Ctrl+C`:

```powershell
npm run build
npx --no-install next start -p 3000
```

El primer comando compila el frontend optimizado. El segundo sirve esa compilación usando Next.js ya instalado. Actualmente `package.json` no define `npm start`.

Configurá `.env.local` y mantené el backend funcionando antes de compilar e iniciar.

Este recorrido es local: el Compose utiliza Keycloak en modo `start-dev`, usuarios de prueba y URLs `localhost`. Publicar en un servidor requiere adaptar dominios, HTTPS y autenticación.

## 9. Detener la aplicación

Presioná `Ctrl+C` en la terminal del frontend. Desde la raíz:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

Detiene y elimina los contenedores y la red del proyecto, conservando los datos de PostgreSQL.

## 10. Borrar los datos y empezar de cero

**Solo para datos descartables:** este comando elimina los datos de M3 y de Keycloak.

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml down -v
docker compose --env-file infra/.env -f infra/docker-compose.yml up --build -d
```

`down -v` elimina también el volumen. El siguiente arranque crea las bases, importa el realm, aplica migraciones y carga el seed nuevamente.

## Problemas frecuentes

| Problema | Qué revisar |
|---|---|
| Docker no conecta | Abrir Docker Desktop y verificar con `docker info`. |
| Puerto ocupado | Liberarlo o cambiar el puerto en `infra/.env`. Si cambia API o Keycloak, actualizar también las URLs del frontend y reiniciar los servicios. |
| API no inicia | Consultar `ps -a` y los logs de migraciones, seed, Keycloak y API. |
| Frontend no obtiene token | Comparar el secreto, usuario y contraseña con los del realm y comprobar que Keycloak funcione. |
| Frontend no muestra conductores | Revisar `API_URL`, incluido `/api/v1`, y los mensajes de la terminal de Next.js. |
| API devuelve `401` | Obtener un token nuevo y verificar que corresponda al realm `m3` local. |
| Seed y migraciones detenidos | Si terminaron con código `0`, es normal. |
| Cambié contraseñas y ahora falla | Las bases existentes y el realm importado conservan sus credenciales. Editar `.env` no las actualiza. Restaurar los valores originales o modificarlas en los servicios; para datos descartables, usar el borrado del paso 10. |

## Comandos rápidos para uso diario

Con las variables ya configuradas, en una terminal desde la raíz:

```powershell
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

En otra terminal desde la raíz:

```powershell
cd frontend
npm run dev
```

Abrí http://localhost:3000.

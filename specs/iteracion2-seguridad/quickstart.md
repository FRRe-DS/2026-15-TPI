# Validación rápida: Iteración 2 — Seguridad y plataforma

Esta guía valida los entregables planificados de Datos y seguridad, Redis y publicación de la imagen de API. Requiere Docker Compose; para el smoke test también se necesita el realm de Keycloak y las variables locales de `.env`.

## Preparar el entorno local

1. Copiar `.env.example` a `.env` y completar credenciales locales como indica [DESPLIEGUE.md](../../DESPLIEGUE.md). No reutilizar credenciales reales ni añadir `.env` al repositorio.
2. Generar `REDIS_PASSWORD` y `RATE_LIMIT_HMAC_SECRET` como valores aleatorios distintos (por ejemplo, `openssl rand -hex 32`) y completarlos en `.env`; configurar `REDIS_URL=redis://redis:6379/0`, `RATE_LIMIT_ANON_REQUESTS=60`, `RATE_LIMIT_PREAUTH_REQUESTS=1000`, `RATE_LIMIT_AUTH_REQUESTS=120` y `RATE_LIMIT_WINDOW_SECONDS=60` (o los valores que se quieran probar). El secreto HMAC debe ser el mismo en todas las instancias de API. La cuota preliminar limita por IP los bearer tokens antes de consultar JWKS o verificar la firma; la cuota autenticada se mantiene por `(iss, sub)`. La contraseña Redis se pasa por separado y no se incluye en la URL. No versionar el `.env`.
3. Validar la configuración y levantar el stack:

   ```sh
   docker compose config
   docker compose up --build -d
   docker compose ps
   ```

   Redis debe figurar saludable para la validación normal del stack. La API puede arrancar si Redis no responde, pero las rutas sujetas al limitador deben devolver 503 hasta recuperarlo. No debe existir un puerto Redis publicado al host por defecto.

## Validar respuestas y cuotas

- Salud: `curl -i http://localhost:${API_PORT:-8080}/salud` responde `200`; esta ruta no consume cuota.
- Sin JWT válido: hacer solicitudes a un endpoint protegido desde una IP de prueba. Hasta el límite configurado siguen el flujo normal de autenticación (sin token, `401`); la siguiente solicitud dentro de la ventana responde `429`, cuerpo `LIMITE_DE_SOLICITUDES` y encabezado `Retry-After`.
- JWT válido: usar los tests de API para confirmar 120/min por `(iss, sub)`, separación entre usuarios, expiración de ventana y que un claim no verificado nunca controla la identidad de cuota. Los fixtures deben incluir una identidad `sub`.
- Redis no disponible: con el stack levantado, `docker compose stop redis`; las rutas protegidas deben responder `503` fail-closed mientras `/salud` permanece disponible. Restaurar con `docker compose start redis`.
- La suite automatizada debe cubrir concurrencia con Redis real para verificar atomicidad, más errores de conexión/timeout mediante fake. Las pruebas API ejecutan lifespan y las pruebas de migración, esquema y realm mantienen las validaciones del plan principal.

## Smoke test

`.github/scripts/humo.sh` levanta el stack y verifica el flujo de operador, el healthcheck de Redis, el `429` con `Retry-After`, el `503` al detener Redis y la disponibilidad de `/salud` durante esa falla. En CI el job `entorno` ejecuta `humo.sh --preparar` antes de los e2e y el smoke completo después de ellos: la ráfaga anónima agota el cupo de la IP y detener Redis deja el stack en 503, por eso esas comprobaciones van al final.

## Límites en CI

Los jobs `test` y `entorno` fijan `RATE_LIMIT_AUTH_REQUESTS=1000`, `RATE_LIMIT_PREAUTH_REQUESTS=1000` y dejan `RATE_LIMIT_ANON_REQUESTS=60`. Los e2e y las pruebas de concurrencia de Testing usan JWT (cuota por `(iss, sub)`) y las pocas llamadas anónimas no alcanzan 60. Bajar esos valores en CI rompe a Testing.

## Validar publicación Docker Hub

La publicación automatizada se valida en GitHub Actions, no desde un pull request:

1. Configurar `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` como secretos del repositorio y `DOCKERHUB_IMAGE` como variable del repositorio.
2. Confirmar que el job de publicación depende de CI verde y solo se ejecuta en `push` a `dev` o `main`.
3. Tras un push aceptado, comprobar que existe la etiqueta basada en SHA y la etiqueta de rama (`dev` o `main`).
4. Para probar una etiqueta publicada localmente, configurar `M3_API_IMAGE` con su referencia y ejecutar `docker compose pull` y `docker compose up -d`. El valor predeterminado local conserva `m3-backend:local` y el build desde `backend/Dockerfile`.

La imagen propia publicada es solo la API/Backend M3, que también contiene las migraciones y el seed para el Compose existente. Redis, PostgreSQL, Keycloak y frontend usan sus imágenes respectivas y no se suben a Docker Hub desde este job.

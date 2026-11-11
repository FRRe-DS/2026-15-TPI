# Investigación: Iteración 2 — Seguridad y plataforma

## Contexto técnico

- **API**: Python 3.12 y FastAPI. La validación JWT existente usa PyJWT/JWKS dentro de una dependencia síncrona.
- **Entorno**: Docker Compose en la raíz; PostgreSQL, Keycloak, migraciones, seed, API y frontend. La imagen `backend/Dockerfile` ya ejecuta como usuario no privilegiado y se comparte entre API, migraciones y seed.
- **CI**: `.github/workflows/ci.yml` corre en pull requests y pushes a `dev`/`main`. El job `ci` agrega los resultados de lint, contrato, pruebas, smoke test y frontend.
- **Contrato**: `docs/contract/openapi.yaml` 1.2.0; errores JSON existentes con `codigo` y `mensaje`.
- `.specify/` no existe en este checkout; la planificación sigue la estructura de `specs/iteracion1/` y de las otras áreas de Iteración 2.

## Decisiones de diseño

### 1. Redis como almacén compartido de cuotas

- **Decisión**: agregar el cliente oficial `redis` de Python al grupo de dependencias de API y usar un cliente síncrono con pool de conexiones, consistente con la dependencia síncrona de autenticación actual. Crear y cerrar el cliente en el ciclo de vida de FastAPI; inyectar la interfaz de acceso para que los tests puedan usar un fake.
- **Motivo**: todas las réplicas de la API deben observar el mismo contador; Redis permite operaciones atómicas y evita el límite incorrecto por proceso. El cliente síncrono evita convertir la validación JWT y sus dependencias en asíncronas solo por esta capacidad.
- **Alternativas**: contador en memoria (no coordina réplicas ni sobrevive reinicios del proceso); framework de rate limiting adicional (menos código propio, pero añade integración y semántica que no necesita este servicio).

### 2. Ventana deslizante implementada atómicamente

- **Decisión**: guardar timestamps de solicitudes en un sorted set por cliente y ejecutar en un script Lua una única operación que consulte la hora de Redis, retire entradas anteriores a la ventana, compruebe el límite, agregue la solicitud permitida y actualice el TTL. Una solicitud rechazada no extiende la ventana. `Retry-After` se calcula con el evento permitido más antiguo que todavía consume cuota.
- **Motivo**: serializa solicitudes concurrentes entre procesos y evita la ráfaga de hasta el doble del límite que permite un contador de ventana fija en el borde entre minutos. La hora se obtiene de Redis para evitar diferencias de reloj entre réplicas.
- **Alternativas**: contador fijo por minuto con `INCR`/`EXPIRE` (más simple, pero permite ráfagas en el cambio de ventana); token bucket (controla la tasa media, pero la política no coincide con los límites por ventana acordados).

### 3. Clasificación de identidad y límites

- **Decisión**: 60 solicitudes en 60 segundos para requests sin JWT válido, usando `request.client.host`; 120 por 60 segundos para JWT verificado, usando el par `(iss, sub)` del payload validado. `sub` debe ser texto no vacío; si falta o no es válido, el token se rechaza como no autenticado tras aplicar la cuota por IP. No usar claims antes de verificar firma, issuer y expiración.
- **Motivo**: `sub` identifica de forma estable al principal autenticado, mientras que la dirección de conexión es la única identidad disponible antes de autenticar. Se evita confiar en `X-Forwarded-For` enviado directamente por el cliente.
- **Proxy**: solo aceptar una IP reenviada si la conexión proviene de un proxy configurado como confiable; el despliegue actual no declara un proxy, así que usa el peer de ASGI.
- **Configuración**: `REDIS_URL`, `REDIS_PASSWORD`, `RATE_LIMIT_HMAC_SECRET`, `RATE_LIMIT_ANON_REQUESTS=60`, `RATE_LIMIT_PREAUTH_REQUESTS=1000`, `RATE_LIMIT_AUTH_REQUESTS=120` y `RATE_LIMIT_WINDOW_SECONDS=60`. El secreto HMAC es dedicado, compartido por instancias API y de al menos 32 caracteres; permite derivar claves Redis sin exponer identidades de baja entropía ante una copia del almacén. Los valores de límite/ventana deben ser enteros positivos. Redis requiere contraseña, está en la red privada de Compose y no publica puerto al host por defecto. Ambos secretos se generan fuera del repositorio y no se registran.

### 4. Respuestas y disponibilidad

- **Decisión**: exceder el límite genera HTTP 429, `Retry-After` y el formato uniforme de error de M3 con código `LIMITE_DE_SOLICITUDES`; no cachear la respuesta. Un timeout o error de conexión de Redis genera HTTP 503 con código `SERVICIO_TEMPORALMENTE_NO_DISPONIBLE` (fail-closed). `/salud` queda fuera del limitador.
- **Motivo**: las solicitudes no pueden evadir el control cuando el almacén falla; los clientes reciben un tiempo de reintento y el diagnóstico no expone detalles internos. El healthcheck no debe consumir cuota ni quedar limitado.
- **Alternativa**: fail-open conserva disponibilidad, pero ignora el control durante una falla de Redis; se descartó por decisión explícita del usuario.
- **Contrato**: Testing debe agregar las respuestas transversales 429 y 503 al OpenAPI para las operaciones autenticadas, manteniendo rutas y permisos existentes.
- **Arranque**: crear el cliente Redis sin hacer `PING` obligatorio en startup; así la API puede iniciar y responder 503 en rutas limitadas si Redis está caído, en vez de no aceptar conexiones. El healthcheck de Redis y el smoke test validan la disponibilidad normal del stack.

### 5. Publicación de la imagen

- **Decisión**: publicar solo la imagen del backend M3, reutilizable por `api`, `migraciones` y `seed`. GitHub Actions construye y publica solo en `push` a `dev`/`main`, después del job agregado `ci` exitoso. No se publica en `pull_request`.
- **Autenticación/configuración**: `DOCKER_USERNAME` y `DOCKER_PASSWORD` son secretos de GitHub para iniciar sesión; el segundo almacena un access token de Docker Hub. El secreto `DOCKER_IMAGE` contiene el destino `usuario/repositorio` (sin tag). La referencia de imagen para Compose se parametriza como `M3_API_IMAGE`, con `m3-backend:local` como valor local predeterminado.
- **Etiquetas**: etiqueta inmutable con el SHA completo y etiqueta de rama (`dev` o `main`). El tag de rama es mutable; los despliegues reproducibles usan el tag SHA.
- **Seguridad de workflow**: permisos mínimos (`contents: read` para checkout), publicar solo tras CI, no elevar permisos del `GITHUB_TOKEN` para Docker Hub, no revelar secretos y fijar las acciones externas por SHA completo.
- **Alternativas**: publicar frontend o imágenes de dependencias (fuera de alcance); publicación desde cada PR (riesgo de publicar cambios no aceptados); usar tags mutables como única referencia (no reproducible).

## Ajustes requeridos por el estado actual del código

- `backend/app/api/seguridad.py` valida firma RS256, issuer y expiración, pero no requiere actualmente `sub`. El diseño lo requiere para crear una cuota autenticada estable; un JWT firmado sin `sub` válido se rechaza como no autenticado después de contar por IP.
- Los fixtures JWT de `backend/tests/api/conftest.py` actualmente no incluyen `sub`; se actualizan para representar tokens emitidos por Keycloak.
- Crear el cliente Redis en el lifespan de FastAPI y cerrarlo al finalizar. No hacer `PING` requerido en startup; los errores Redis durante una solicitud deben poder traducirse a 503.
- Probar la atomicidad con Redis real en integración, además de fakes para las pruebas unitarias/API. El `TestClient` se ejecuta en contexto para activar el lifespan.
- El nombre de usuario/repositorio Docker Hub lo proporciona el secreto `DOCKER_IMAGE`; debe coincidir con la cuenta del secreto `DOCKER_USERNAME`.

## Fuentes consultadas

- Redis, cliente Python: <https://redis.io/docs/latest/develop/clients/redis-py/>
- Redis, scripts Lua/EVAL: <https://redis.io/docs/latest/develop/programmability/eval-intro/>
- Redis, comando `TIME`: <https://redis.io/docs/latest/commands/time/>
- Redis, patrones de rate limiting: <https://redis.io/docs/latest/develop/use/patterns/rate-limiting/>
- FastAPI, concurrencia síncrona/asíncrona: <https://fastapi.tiangolo.com/async/>
- FastAPI, ciclo de vida: <https://fastapi.tiangolo.com/advanced/events/>
- FastAPI, proxies confiables: <https://fastapi.tiangolo.com/advanced/behind-a-proxy/>
- RFC 6585, HTTP 429: <https://www.rfc-editor.org/rfc/rfc6585#section-4>
- GitHub Actions, permisos de `GITHUB_TOKEN`: <https://docs.github.com/actions/security-for-github-actions/security-guides/automatic-token-authentication>
- GitHub Actions, uso seguro de acciones de terceros: <https://docs.github.com/en/actions/reference/security/secure-use>
- Docker, login action: <https://github.com/docker/login-action>
- Docker, build-push action: <https://github.com/docker/build-push-action>
- Docker, metadata action para tags: <https://github.com/docker/metadata-action>
- Docker Hub access tokens: <https://docs.docker.com/security/access-tokens/personal-access-tokens/>

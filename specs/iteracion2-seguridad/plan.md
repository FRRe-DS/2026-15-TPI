# Plan de Implementación: Iteración 2 — Plataforma y Seguridad

**Rama**: `juampa1503-iteracion-2-plataforma-seguridad` | **Contrato**: [OpenAPI 1.2.0](../../docs/contract/openapi.yaml)

**Entrada**: alcance de datos y seguridad solicitado para la Iteración 2, coordinado con el plan del [Backend](../iteracion2-backend/plan.md), el modelo de datos y el contrato vigente.

## Resumen

Preparar la persistencia, la identidad y la plataforma de M3 para las 17 operaciones del contrato 1.2.0. El cambio central es una migración Alembic reversible que unifica el estado del conductor, agrega los datos de Iteración 2 y crea las tablas de solicitudes y documentos de vehículos. También se actualizarán los modelos SQLAlchemy, el seed, Keycloak y Compose. Redis se usará como almacén distribuido de rate limiting y la imagen de la API se publicará en Docker Hub desde CI, sin publicar en eventos de pull request.

Este plan cubre la plataforma y el grupo de Datos y seguridad. La lógica y los endpoints corresponden al plan de Backend; las pruebas de contrato y la integración continua se coordinan con Testing.

## Alcance e integración entre módulos

- **M4** solo consulta conductores, estado y ubicación con el rol `servicio`. M3 no expone escrituras para M4.
- **M5** es el origen de las solicitudes; M3 las consulta y permite que el conductor las acepte o rechace. El backend no crea solicitudes.
- **M6** no se consume ni se integra en esta iteración. No se implementan viajes ni calificación de clientes. `suma_puntajes` y `cantidad_calificaciones` se cargan en el seed y se exponen como datos de solo lectura.
- Las 17 operaciones del contrato OpenAPI 1.2.0 son la fuente de verdad. No agregar rutas retiradas de integración M4/M6.

## Plan de trabajo

| Área | Trabajo | Entregables | Criterio de cierre |
|---|---|---|---|
| Migración y persistencia | Crear Alembic `0002`, actualizar modelos y los mínimos consumidores existentes | Migración reversible, modelos SQLAlchemy, ajustes acotados a `sql_conductores.py` y `infra/seed/cargar_datos.py` | `upgrade` y `downgrade` funcionan sobre la revisión anterior y las pruebas de esquema pasan |
| Datos de prueba | Extender el seed de forma determinista e idempotente | Escenarios de conductor, solicitudes, vehículos, documentos y usuario conductor descritos abajo | Seed ejecutable más de una vez y cubre los escenarios del contrato |
| Keycloak y entorno | Agregar el rol técnico de solo lectura y su cuenta M4, parametrizada | Realm, variables en `.env.example`, Compose y pruebas del realm | El realm importa con variables de entorno; el token de M4 tiene `servicio` y no obtiene permisos de escritura |
| Redis y rate limiting | Agregar Redis interno y límites compartidos por identidad o IP | Servicio Compose, configuración, integración de API, errores 429/503 y pruebas | Cuotas distribuidas y atómicas; fail-closed ante una falla de Redis |
| Imagen y registry | Publicar solo la imagen de la API M3 desde GitHub Actions | Job de build/push a Docker Hub, tags rastreables y documentación de configuración | Publicación solo en pushes a `dev`/`main` después de CI verde; no publicar en PR |
| Integración de equipos | Ordenar la migración/modelos respecto de los repositorios SQL | Dependencia explícita para las PR L9 y L10 de Backend | L9 espera migración/modelos; L10 sigue a L9 y también requiere las tablas del modelo |

### Migración Alembic `0002`

La migración parte del esquema de Iteración 1 y debe incluir `downgrade` funcional.

- Reemplazar `conectado` y `disponible` por `estado`, migrando los datos existentes: `conectado=false` pasa a `DESCONECTADO`; `conectado=true, disponible=true` a `DISPONIBLE`; y `conectado=true, disponible=false` a `CONECTADO`. Después, quitar ambas columnas y el índice antiguo y crear el índice de `estado`.
- Agregar a `conductor`: `id_vehiculo_activo`, `fecha_ultimo_cambio_estado`, `suma_puntajes` y `cantidad_calificaciones`, con sus claves foráneas, valores por defecto y restricciones según el [modelo de datos](../iteracion2-backend/data-model.md).
- Crear las tablas `solicitud` y `vehiculo_documento`, con claves, restricciones e índices definidos en el modelo de datos.
- El `downgrade` recrea las columnas antiguas y su índice antes de retirar los campos/tablas nuevos. Reconstruye sus booleanos desde `estado`: `DESCONECTADO` → `false/false`, `DISPONIBLE` → `true/true`, y `CONECTADO` u `OCUPADO` → `true/false`. Las dos últimas situaciones no se pueden distinguir en el esquema anterior.

Los modelos SQLAlchemy deben representar el esquema migrado. Como `0002` elimina columnas consultadas actualmente, el mismo cambio coordinado incluye la adaptación mínima de `backend/app/infraestructura/repositorios/sql_conductores.py` y del seed para que `dev` siga levantando y cargando datos entre la migración y la integración de Backend.

### Datos de prueba requeridos

El seed debe ser determinista e idempotente e incluir:

- Conductores en los cuatro estados: `DESCONECTADO`, `CONECTADO`, `DISPONIBLE` y `OCUPADO`.
- Un conductor sin ubicación registrada y otro sin vehículo activo.
- Un conductor con calificaciones y otro sin ninguna; `suma_puntajes` y `cantidad_calificaciones` se almacenan y `puntaje_promedio` se calcula al leer. No se agrega una escritura funcional de calificación.
- Solicitudes en los cuatro estados (`PENDIENTE`, `ACEPTADO`, `RECHAZADO`, `VENCIDA`), con una solicitud pendiente vencida y otra vigente.
- Documentos de vehículo vigentes y vencidos.
- Un usuario conductor cuyo claim entero `id_conductor` coincida con un conductor del seed.

### Keycloak y autorización de servicio

- Agregar el rol `servicio` al realm. La cuenta técnica de M4 obtiene ese rol y credenciales configuradas por variables de entorno, nunca valores secretos versionados.
- Exponer las variables necesarias en `.env.example` (raíz), pasarlas al servicio `keycloak` en `docker-compose.yml` (raíz) y actualizar `backend/tests/infra/test_realm.py`. Las mismas variables se generan en el paso «Preparar variables de entorno» del job `entorno` de `.github/workflows/ci.yml`; si faltan allí, el humo de Compose falla.
- Agregar el mapeador de usuario para emitir `id_conductor` como entero en el token, igual que el claim `id_operador`; el usuario de prueba debe apuntar al conductor sembrado.
- La cuenta `servicio` es de solo lectura: puede consultar conductores, vehículos, estado y ubicación; no puede actualizar estados, responder solicitudes ni ejecutar acciones de operador.
- Mantener la validación JWT con firma/JWKS, issuer, audiencia y expiración, y no guardar secretos en el repositorio.

### Redis y rate limiting distribuido

- Agregar un servicio Redis con versión fijada, contraseña y healthcheck, accesible solo por la red interna de Compose. No publicar el puerto Redis al host por defecto ni agregar persistencia: las cuotas son estado efímero con vencimiento.
- Configurar la autenticación de Redis con `REDIS_PASSWORD`; el healthcheck pasa la credencial mediante `REDISCLI_AUTH`, sin incluirla en argumentos visibles ni logs. `.env.example` deja el valor vacío y CI lo genera aleatoriamente para el humo.
- Configurar `RATE_LIMIT_HMAC_SECRET` como secreto dedicado, obligatorio, de al menos 32 caracteres y compartido entre instancias de API; se usa para derivar claves Redis con HMAC-SHA-256 y no se almacena en Redis.
- La API conecta con `REDIS_URL`; el servicio Redis requiere `REDIS_PASSWORD`. Los límites y la ventana se configuran con `RATE_LIMIT_ANON_REQUESTS=60`, `RATE_LIMIT_AUTH_REQUESTS=120` y `RATE_LIMIT_WINDOW_SECONDS=60`; los valores son positivos y validados al iniciar.
- Aplicar una ventana deslizante de 60 segundos de manera atómica en Redis. Los requests sin JWT válido usan la IP del cliente (60/min); un JWT verificado usa el par `(iss, sub)` (120/min). Requerir `sub` no vacío para la identidad autenticada; si falta, rechazar el token y aplicar el límite por IP. Nunca usar claims de un token sin validar. Solo confiar en `X-Forwarded-For` cuando el request proviene de un proxy configurado como confiable; inicialmente se usa la dirección que entrega ASGI.
- Cuando se excede el límite, responder `429` con el formato común `{"codigo": "LIMITE_DE_SOLICITUDES", "mensaje": "..."}` y `Retry-After` en segundos. Si Redis está inaccesible o agota el timeout, responder `503` con `SERVICIO_TEMPORALMENTE_NO_DISPONIBLE` (fail-closed); no convertir errores de conexión en respuestas exitosas.
- Agregar ambos códigos estables al catálogo y manejadores de errores de API, actualizar las pruebas de contrato y documentar las respuestas para las operaciones protegidas en OpenAPI; no almacenar en caché la respuesta 429.
- Excluir `/salud` del rate limiting para que Compose y CI puedan observar la aplicación. La salud de Redis se valida por el healthcheck de su propio servicio y por el smoke test del stack.
- Documentar las respuestas transversales 429/503 en el contrato interno de este grupo y coordinarlas con Testing para que el OpenAPI y las pruebas de contrato reflejen la nueva superficie de respuesta; no se agregan rutas ni cambian los permisos existentes.

### Imagen de API y publicación en Docker Hub

- Mantener el Dockerfile actual de Backend, que ejecuta como usuario no privilegiado. La imagen publicada es la misma imagen de Backend que Compose usa para `api`, `migraciones` y `seed`; no se publican imágenes de Redis, PostgreSQL, Keycloak ni frontend.
- Permitir seleccionar la etiqueta con `M3_API_IMAGE`; el valor local predeterminado conserva el flujo de desarrollo con build de Compose. `M3_API_IMAGE` puede documentarse en `.env.example`; las credenciales del registry no se agregan allí.
- Añadir a CI un job de publicación dependiente del resultado verde de los jobs actuales. Solo corre para eventos `push` en `dev` o `main`, nunca en `pull_request`. Usa `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` como secretos y `DOCKERHUB_IMAGE` como variable del repositorio.
- Publicar una etiqueta inmutable derivada del commit y una etiqueta de rama (`dev` o `main`). Mantener permisos mínimos del `GITHUB_TOKEN`, fijar las acciones externas por SHA completo y no imprimir credenciales.
- Actualizar `DESPLIEGUE.md` y [quickstart.md](./quickstart.md) con build local, pull de una etiqueta publicada y requisitos de configuración del registry.

## Orden y dependencias

La migración y los modelos de Datos y seguridad deben integrarse antes de los repositorios SQL de Backend:

1. Datos y seguridad entrega `0002`, los modelos, la adaptación mínima de `sql_conductores.py` y el seed compatible.
2. Backend implementa L9 (repositorio SQL de conductores y unidad de trabajo) sobre esos modelos y columnas.
3. Backend implementa L10 (repositorios de solicitudes y documentos de vehículos) después de L9 y con las tablas de `0002` disponibles.

Las tareas de Backend que usan repositorios en memoria pueden avanzar en paralelo; L9 y L10 no deben integrarse contra el esquema anterior. El orden de despliegue y las pruebas de migración se coordinan entre los responsables de Datos y seguridad, Backend y Testing.

## Acuerdos de integración con Backend y Testing

- **Carpeta y tareas**: este plan vive en `specs/iteracion2-seguridad/`. Las tareas están en [tasks.md](./tasks.md) con los IDs **T501–T599** (Backend usa T301–T401, Testing T601+ y Frontend T701+).
- **Quién toca `sql_conductores.py`**: Datos y seguridad entra primero con `0002`, los modelos y una adaptación mínima que lee y escribe la columna `estado` a partir de los booleanos del dominio vigente. Cuando Backend integra L1 (dominio con `estado`), esa adaptación se reemplaza por el mapeo directo; L1 no agrega otra adaptación transitoria. Los campos nuevos (`id_vehiculo_activo`, fecha, puntajes) y el filtro por `tipo_servicio` los mapea Backend en L9.
- **Helper de token `servicio`**: lo crea Backend en V1 (`backend/tests/api/conftest.py`). Datos y seguridad no agrega helpers de token de API; sus pruebas de realm usan el realm importado.
- **Variables de entorno nuevas**: `REDIS_URL`, `REDIS_PASSWORD`, los límites y `M3_API_IMAGE` se documentan en `.env.example` según corresponda; Compose y el paso «Preparar variables de entorno» de `.github/workflows/ci.yml` reciben las variables necesarias. El smoke test verifica que Redis esté saludable y las respuestas de límite. Los secretos de Docker Hub viven solo en la configuración de GitHub Actions.
- **Guía de despliegue**: `DESPLIEGUE.md` describe el Compose unificado de la raíz (frontend incluido); si cambian variables o puertos, se actualiza en la misma PR.
- **Contrato de respuestas**: el contrato **se mantiene en 1.2.0**; las respuestas 429/503 son transversales. Testing mantiene OpenAPI y pruebas de contrato (T617); Datos y seguridad entrega los códigos y encabezados requeridos para 429/503 sin modificar las 17 rutas.

## Criterios de aceptación

- La migración `0002` lleva una base de Iteración 1 al esquema 1.2.0, conserva correctamente los estados derivados de los booleanos previos y puede revertirse con `downgrade`.
- Los modelos SQLAlchemy, el repositorio SQL existente y el seed funcionan con el nuevo esquema sin referencias a las columnas retiradas.
- El seed es repetible y cubre los cuatro estados, ubicación y vehículo activos opcionales, calificaciones, solicitudes y documentos requeridos.
- Keycloak emite tokens de operador, conductor y servicio; `id_conductor` es un entero coincidente con el seed y la cuenta de servicio no puede escribir. `puntaje_promedio` y `cantidad_calificaciones` se exponen solo para lectura.
- `.env.example` documenta las variables nuevas sin incluir credenciales reales; Compose y las pruebas del realm reflejan el rol y la cuenta técnica.
- Las pruebas de migración, esquema y realm pasan, y el contrato/documentación conserva las 17 operaciones vigentes sin las integraciones M4/M6 retiradas.
- Compose levanta Redis de forma interna y supervisa su healthcheck; la API puede iniciar aunque Redis esté caído y responde 503 en rutas limitadas hasta su recuperación. El smoke test espera Redis saludable antes de validar cuotas.
- Las cuotas de 60/min por IP anónima y 120/min por identidad autenticada se comparten entre instancias, expiran en la ventana configurada y responden 429 con `Retry-After`; Redis no disponible produce 503 en rutas limitadas y no afecta `/salud`.
- JWT autenticado requiere `iss` y `sub` válidos para elegir la cuota de usuario; los fixtures de API reflejan claims realistas y no se usan claims sin verificar.
- El pipeline publica solo la imagen de API a Docker Hub después de CI verde en pushes a `dev`/`main`, con tags rastreables y secretos fuera del repositorio; no publica en PR.

## Riesgos y coordinación

- **Pérdida de distinción al hacer downgrade**: los estados `CONECTADO` y `OCUPADO` se reducen ambos a `conectado=true, disponible=false`; el comportamiento queda documentado.
- **Orden de integración**: quitar columnas antes de adaptar sus consumidores rompe el seed y el repositorio SQL. La migración, el cambio mínimo de esos consumidores y los modelos se entregan coordinados antes de L9/L10.
- **Desalineación del contrato**: cambios de rutas o permisos se resuelven contra `docs/contract/openapi.yaml`; esta iteración no agrega escrituras para M4/M6 ni operaciones de viajes/calificación.
- **Disponibilidad de Redis**: fail-closed hace que la API responda 503 en rutas limitadas si el almacén no está disponible. Compose, el healthcheck y el smoke test verifican Redis; la respuesta no se degrada silenciosamente a fail-open.
- **Credenciales de Docker Hub**: la publicación requiere secretos y variable configurados en GitHub. Si faltan, el job debe fallar explícitamente y no simular una publicación correcta.

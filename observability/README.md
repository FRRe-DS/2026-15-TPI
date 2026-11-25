# Observabilidad M3 — Grupo 15

Implementación en `devops/observabilidad`, separada del Grupo 02. No modifica
workflows de GHCR, CI ni CodeQL. Los cambios de dominio no son necesarios.

Documentos de cierre:

- [Resultados y evidencias](EVIDENCIAS.md).
- [Entrada de bitácora del 23/11/2026](BITACORA-2026-11-23.md).
- [Errores de Keycloak/Testcontainers y reproducción](KEYCLOAK-TESTCONTAINERS.md).
- [Retomar el entorno y preparar k6](RETOMAR-K6.md).

## Arquitectura

FastAPI → SDK OpenTelemetry Python → OTLP HTTP/protobuf → Collector Contrib
0.140.0 → Grafana Cloud (Metrics y Tempo). Psycopg genera spans de PostgreSQL;
el Collector consulta una vista agregada cada 60 s. Exportación del SDK cada 30 s.
Servicio `m3-conductores-grupo15`, namespace `utn-frre` y job
`utn-frre/m3-conductores-grupo15`, distintos del Grupo 02. SDK 1.45.2 e
instrumentadores 0.66b2, fijados junto con sus dependencias en `backend/uv.lock`.
La instrumentación se habilita sólo con `M3_OTEL_ENABLED=true`.

El instrumentador SQLAlchemy 0.66b2 excluye SQLAlchemy 2.1.6 en su rango de soporte.
Por eso se instrumenta psycopg, sin degradar el ORM ni omitir comprobaciones de
compatibilidad. Se capturan también las consultas que SQLAlchemy envía al driver.

No se capturan cuerpos HTTP, tokens ni parámetros SQL como etiquetas de negocio.
Los histogramas sólo tienen `outcome=success|error`; nunca IDs, DNI ni emails.
El endpoint HTTP automático utiliza plantillas de ruta.

## Tres métricas de la bitácora

| Métrica | Nombre OpenTelemetry / unidad | Fuente y condiciones |
|---|---|---|
| Conductores disponibles y habilitados | `m3.drivers.available` / `{driver}` | Gauge de PostgreSQL: conductor `DISPONIBLE`, habilitación `APROBADA`, vehículo activo **propio** y `APROBADA`. |
| Tiempo de alta | `m3.driver.registration.duration` / `s` | POST `/api/v1/conductores`: desde recepción ASGI hasta retorno de `CrearConductor.ejecutar`, después del commit. |
| Tiempo de actualización operativa | `m3.driver.operational_state.update.duration` / `s` | PATCH `/api/v1/conductores/{id}/estado` con estado o vehículo activo; también aceptación de solicitud que pasa a `OCUPADO`. Hasta retorno del caso después del commit. |

Las duraciones incluyen autenticación y dependencias, pero no serialización/envío
de la respuesta. Los rechazos anteriores al caso de uso se observan en HTTP y no
en los histogramas de negocio. Las excepciones del caso se registran como error y
se propagan sin alterar la respuesta. Ubicación sola y rechazo de solicitud no
cuentan como actualización operativa. Una petición de estado que no cambie el valor
puede contar: mide procesamiento de solicitudes, no cantidad de transiciones.

La vista refleja aprobaciones persistidas: no recalcula vencimientos documentales.
El código de habilitación controla requisitos al aprobar. Un cero significa que
ningún registro cumple el predicado; ausencia de serie no equivale a cero.
No sumar el Gauge por réplicas. El receiver SQL es alpha: versión fija y pruebas
de permisos/consulta antes de producción. El rol sólo lee la vista agregada y usa
timeout 5 s; no recibe acceso a tablas ni a Keycloak.

En este repositorio no existe la intención `APPLIED` del Grupo 02. El Gauge informa
estado local persistido de M3; no acredita que M4 haya asignado o realizado un viaje.

## Levantar en Windows / Docker Desktop

Desde la raíz del Grupo 15, PowerShell:

```powershell
python observability/setup-local.py
$compose = @('--env-file', '.env.observability.local', '-p', 'm3-grupo15', '-f', 'docker-compose.yml', '-f', 'compose.observability.yaml')
docker compose @compose up -d --build api
python observability/setup-local.py --sql
docker compose @compose ps -a
Invoke-RestMethod http://localhost:18080/salud
```

El script crea `.env.observability.local` una sola vez, con secretos aleatorios;
no reemplaza archivos existentes. Este entorno de pruebas usa una base/volumen
propios con seed sintético. Puertos: API 18080, PostgreSQL 15432, Keycloak 18081,
frontend opcional 13000 y Prometheus local 127.0.0.1:19464. No ocupa los del Grupo 02.
Redis se levanta como dependencia del overlay, accesible sólo en loopback 16379
para pruebas de integración; conserva su contraseña.
Frontend opcional: `docker compose @compose up -d --build frontend`.

La primera consulta SQL puede fallar hasta ejecutar `--sql` después de migraciones;
el Collector vuelve a intentarla. No cambiar contraseñas del archivo sin actualizar
los servicios y roles existentes. No usar este bootstrap sobre datos reales.

## Grafana Cloud y dashboard separado

Guardar endpoint y autenticación **sólo** en `.env.grafana.local` ignorado:

```dotenv
GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-prod-sa-east-1.grafana.net/otlp
GRAFANA_OTLP_AUTH=Basic REEMPLAZAR_POR_BASE64_DEL_USUARIO_Y_TOKEN
```

El valor Basic se obtiene codificando `1936646:TOKEN_PRIVADO` en Base64 (no es
cifrado). No pegarlo en chats ni incluirlo en evidencias. Se puede reutilizar
privadamente el archivo del Grupo 02 porque ambos exportan al mismo stack.

```powershell
$cloud = @('--env-file', '.env.observability.local', '--env-file', '.env.grafana.local', '-p', 'm3-grupo15', '-f', 'docker-compose.yml', '-f', 'compose.observability.yaml', '-f', 'compose.grafana.yaml')
docker compose @cloud run --rm --no-deps otel-collector validate --config=/etc/otelcol/config.yaml --config=/etc/otelcol/sql.yaml --config=/etc/otelcol/grafana.yaml
docker compose @cloud up -d otel-collector
```

En `https://giantbarracuda2583.grafana.net`, Dashboards → New → Import:
seleccionar `observability/grafana-dashboard.json`, elegir la fuente Metrics del
stack y confirmar. UID propio `m3-grupo15-observabilidad`: no reemplaza el Grupo 02.
Esperar al menos dos intervalos para consultas `rate`.

## Validación sintética y consultas

`python observability/smoke-business.py` obtiene un token del operador local en
memoria, crea un conductor nuevo con DNI aleatorio y email `.invalid`, cambia su
estado y guarda resultados y trace IDs bajo `.local/`. No modifica conductores
existentes. Los registros sintéticos permanecen en el volumen de prueba.

Prometheus local: `http://127.0.0.1:19464/metrics`.
En Explore / Metrics:

```promql
max(m3_drivers_available{job="utn-frre/m3-conductores-grupo15"})
sum(m3_driver_registration_duration_seconds_count{job="utn-frre/m3-conductores-grupo15",outcome="success"})
sum(m3_driver_operational_state_update_duration_seconds_count{job="utn-frre/m3-conductores-grupo15",outcome="success"})
histogram_quantile(0.95, sum by (le) (rate(m3_driver_registration_duration_seconds_bucket{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m])))
sum(rate(m3_driver_registration_duration_seconds_sum{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m])) / sum(rate(m3_driver_registration_duration_seconds_count{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m]))
sum(rate(http_server_request_duration_seconds_count{job="utn-frre/m3-conductores-grupo15"}[5m]))
```

Para actualización, sustituir `registration` por `operational_state_update`.
Los contadores son acumulados por proceso y se reinician al reiniciar la API;
no son un inventario de conductores. Sin tráfico, promedio y percentiles pueden
no mostrar datos. P95 es estimación por buckets, especialmente limitada con pocas
observaciones. CPU normalizada por CPUs visibles y memoria RSS corresponden al
proceso Python, no a todos los recursos del contenedor.

En Explore seleccionar Tempo y ejecutar TraceQL:
`{ resource.service.name = "m3-conductores-grupo15" }`.
Buscar los trace IDs del smoke y verificar span servidor POST 201 / PATCH 200,
spans SQL y ausencia de datos sensibles. Recepción local del Collector y exportación
sin errores no reemplazan la comprobación de consulta remota en Tempo.

## k6 y cierre

Pendiente: carga gradual con usuarios sintéticos propios, métricas antes/después,
throughput, 4xx/5xx, errores de negocio, p50/p95/p99 y CPU/RSS; comparar con k6.
Renovar JWT y respetar rate limiting; distinguir 429 de fallo de persistencia.
No desactivar límites ni cambiar reglas de negocio sólo para mejorar resultados.
Para Gauge, preparar conductor y vehículo con documentación aprobada mediante los
casos reales; comprobar inclusión/exclusión y retorno al valor inicial. Correlacionar
latencias con trazas SQL. Registrar fecha, revisión Git, escenario, duración y captura.
M4 y su prueba de integración no bloquean medir el estado local del Grupo 15.

Detener: `docker compose @cloud stop` (o `@compose` sin Cloud).
Reanudar: `docker compose @cloud up -d api`; verificar salud y series.
`down` conserva el volumen; **no usar `down -v`** si se quieren conservar resultados.
No versionar `.env*` privados, `.local/`, JWT ni capturas privadas.

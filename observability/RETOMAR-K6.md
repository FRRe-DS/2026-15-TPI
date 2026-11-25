# Retomar Grupo 15 para las pruebas de k6

## Recuperar el entorno

Usar `devops/observabilidad`, Docker Desktop en modo Linux y los archivos privados
`.env.observability.local` y `.env.grafana.local`. Conservar sus valores junto con
el volumen `m3-grupo15_postgres_data`: regenerar contraseñas mientras se reutiliza
el volumen puede impedir la conexión. Ninguno de esos archivos se guarda en Git.
Si faltan, seguir el bootstrap del [README](README.md) y reconfigurar Cloud de forma
privada; no copiar secretos a documentación ni a scripts de k6.

Desde la raíz del repositorio, PowerShell:

```powershell
$cloud = @('--env-file', '.env.observability.local', '--env-file', '.env.grafana.local', '-p', 'm3-grupo15', '-f', 'docker-compose.yml', '-f', 'compose.observability.yaml', '-f', 'compose.grafana.yaml')
docker compose @cloud config --quiet
docker compose @cloud up -d --build api
docker compose @cloud ps -a
Invoke-RestMethod http://localhost:18080/salud
```

Usar **siempre los tres Compose** al retomar Cloud; usar sólo el overlay local
puede recrear el Collector sin el exportador de Grafana. La salud HTTP no prueba
por sí sola el acceso a DB, Redis o autenticación. Verificar también servicios
saludables, migraciones/seed finalizados y una operación sintética autenticada.
En una base nueva, después de migraciones, configurar la vista/rol con
`python observability/setup-local.py --sql`; no hace falta recrearlos en cada carga.

```powershell
docker compose @cloud run --rm --no-deps otel-collector validate --config=/etc/otelcol/config.yaml --config=/etc/otelcol/sql.yaml --config=/etc/otelcol/grafana.yaml
python observability/smoke-business.py
```

El smoke agrega un conductor propio de prueba y hace dos actualizaciones; no es
una carga k6. Esperar dos intervalos del SDK (30 s) y al menos un intervalo SQL
(60 s). Comprobar el [dashboard](https://giantbarracuda2583.grafana.net/d/m3-grupo15-observabilidad/)
y Tempo con los nuevos trace IDs guardados bajo `.local/`.
Los números **1 / 1 / 2** registrados en el cierre son históricos de las pruebas
del 23/11/2026; no deben exigirse como valores actuales al retomar.

## Preparar y medir k6 (pendiente de implementación)

1. Registrar commit probado, fecha/hora con zona, versiones, recursos asignados a
   Docker Desktop, escenario, usuarios virtuales, duración, rampas y límites de
   aceptación. Definirlos antes de ejecutar, sin inventar umbrales a posteriori.
2. Crear datos sintéticos y cuentas de prueba propias. Definir autenticación y
   renovación de JWT sin guardar tokens en Git. No modificar conductores reales
   ni reutilizar indiscriminadamente los del seed para escrituras concurrentes.
3. Hacer calentamiento y tomar una línea base antes de la ventana de carga.
   Mantener la API sin reinicios dentro de la ventana: los histogramas son por
   proceso. Registrar reinicios o cambios de versión si ocurren.
4. Ejecutar carga gradual sobre altas y cambios operativos, incluyendo aceptación
   de solicitud cuando el escenario lo requiera. Para disponibilidad, preparar
   documentación, conductor y vehículo aprobados mediante los casos de uso reales.
   Separar la prueba SQL con rollback de una validación funcional completa por API.
5. Comparar k6 con HTTP y negocio en Grafana: throughput, latencia p50/p95/p99,
   errores de negocio, 4xx, 5xx, timeouts y 429. Respetar rate limiting; no confundir
   rechazos por cuota con errores de persistencia ni desactivar límites para mejorar
   resultados. Registrar CPU/RSS y limitaciones de recursos del entorno.
6. Correlacionar latencias con trazas HTTP/SQL en Tempo y comprobar recuperación
   tras la carga. Guardar configuración sin secretos, resultados y capturas con
   rango temporal y trazas de ejemplo; las evidencias privadas permanecen en `.local/`.

Consultas para una ventana de ejemplo de 5 minutos (ajustarla al ensayo):

```promql
max(m3_drivers_available{job="utn-frre/m3-conductores-grupo15"})
sum(increase(m3_driver_registration_duration_seconds_count{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m]))
sum(increase(m3_driver_operational_state_update_duration_seconds_count{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m]))
histogram_quantile(0.95, sum by (le) (rate(m3_driver_registration_duration_seconds_bucket{job="utn-frre/m3-conductores-grupo15",outcome="success"}[5m])))
sum(rate(http_server_request_duration_seconds_count{job="utn-frre/m3-conductores-grupo15"}[5m]))
```

Sustituir `registration` por `operational_state_update` para la otra duración y
0.95 por 0.50/0.99 para los otros percentiles. `increase` es una estimación y puede
dar valores fraccionarios; no es el inventario persistido ni reemplaza los resultados
del generador. Con pocas muestras los percentiles son poco representativos.
No sumar el Gauge por réplica; representa una consulta global a PostgreSQL.
Las aprobaciones y el estado local no equivalen a confirmación de un viaje por M4.

## Detener y conservar el trabajo

```powershell
docker compose @cloud stop
# En una sesión posterior, volver a definir $cloud y ejecutar:
docker compose @cloud up -d api
```

`down` conserva el volumen; evitar `down -v` para mantener datos y resultados.
No detener el proyecto del Grupo 02 ni otros contenedores para operar este entorno.
Antes de afirmar validación completa, resolver los dos errores de infraestructura
de [Keycloak/Testcontainers](KEYCLOAK-TESTCONTAINERS.md) y ejecutar E2E. Esto no
impide preparar y medir los escenarios de M3, dejando los límites explícitos.

# Validación inicial — 23/11/2026 (Argentina)

Rama: `devops/observabilidad`, basada en `d8396dc1cef7d63875cbbe826b5c8c1846f0df2b`.
Este documento registra las pruebas previas al commit de cierre de observabilidad.
Entorno de prueba `m3-grupo15`, datos sintéticos,
PostgreSQL y Keycloak propios. Grupo 02 siguió saludable y sin cambios.
Los nombres de archivos bajo `.local/` usan UTC: por eso llevan fecha 24/11.

## Resultados realmente observados

- Docker construyó la imagen con `uv sync --frozen`; API, PostgreSQL, Redis y
  Keycloak saludables. Migraciones y seed finalizaron correctamente.
- Collector validó las tres configuraciones local/SQL/Cloud con código de salida 0.
- Grafana Cloud recibió series del job `utn-frre/m3-conductores-grupo15`.
  Se importó el [dashboard del Grupo 15](https://giantbarracuda2583.grafana.net/d/m3-grupo15-observabilidad/).
  Se observaron Gauge **1**, curvas de promedio y p95 de ambas duraciones y tráfico HTTP.
  No se reemplazó el dashboard del Grupo 02.
- En el último proceso de la API: **1 observación de alta exitosa** y
  **2 de actualización operativa exitosa**. El smoke produjo POST **201**,
  PATCH a `CONECTADO` **200** y PATCH a `DESCONECTADO` **200**.
- Se ejecutaron cuatro smokes exitosos durante las iteraciones. No sumar los
  contadores de distintas revisiones como si pertenecieran al mismo proceso:
  hubo reconstrucciones/reinicios y se reiniciaron los histogramas.
- Gauge **1**: corresponde al estado aprobado/disponible del seed sintético,
  no a los conductores nuevos, que quedaron pendientes y desconectados.
- `verify-gauge.sql` verificó inclusión de conductor aprobado/disponible y
  exclusión de ocupado, conductor pendiente, vehículo pendiente y vehículo ajeno.
  Verificó ausencia de SELECT sobre tablas y de INSERT sobre la vista para `m3_otel`.
  Todo se revirtió con rollback; el valor volvió a **1**. Esta prueba valida el
  predicado SQL, no reemplaza un flujo de aprobación documental por la API.
- CPU y RSS del proceso Python presentes en Prometheus local. Los nombres reales
  son `process_cpu_utilization_ratio` y `process_memory_usage_bytes`.
- Tempo mostró el alta final **201**, 14 spans, con `INSERT`, `SAVEPOINT` y `RELEASE`;
  también actualización **200**, 8 spans, con `SELECT` y `UPDATE`.

Trace IDs finales consultados en Tempo:

| Operación | Trace ID |
|---|---|
| Alta 201 | `2abbea106bd75d916f0327414c3cf545` |
| Actualización 200 | `5cf326c84556051643f622989370f180` |
| Desconexión 200 generada por smoke | `ff1b2be2b5132eb2bc0da5b11d2c8409` |

Los dos primeros se consultaron directamente en Explore. El tercero está guardado
por el smoke, sin afirmar aquí que se haya abierto individualmente en Tempo.
Seleccionar fuente `grafanacloud-giantbarracuda2583-traces`, tipo Trace ID, o usar
`{ resource.service.name = "m3-conductores-grupo15" }` para buscar el servicio.
La retención del stack limita cuánto tiempo se podrán consultar estas trazas.

## Dependencias y decisión técnica

No se actualizaron paquetes existentes salvo `opentelemetry-api` 1.45.1 → 1.45.2.
Se agregaron dependencias del SDK/exportador/instrumentadores, fijadas en uv.lock.
SQLAlchemy 2.1.6 queda intacto. El instrumentador SQLAlchemy 0.66b2 no lo soporta
(`sqlalchemy < 2.1.0`) y no generaba spans; se reemplazó por el instrumentador
psycopg, cuyo rango incluye psycopg 3.3.6. La validación posterior en Tempo confirmó
los spans SQL. No se desactivó ninguna comprobación de compatibilidad.

## Pruebas y límites de la validación

- Ruff: lint y formato correctos. `git diff --check`: sin errores de whitespace.
- Cuatro pruebas nuevas: registro de éxito después del retorno, propagación de
  error, exclusión de ubicación sola y desactivación por defecto.
- Primera suite completa (antes de sustituir el instrumentador SQL):
  **1396 passed**, cobertura **96,31 %**.
- Suite completa final con psycopg: **1394 passed, 2 errors**, cobertura **96,31 %**.
  No hubo omisiones; E2E quedó excluido explícitamente como en la suite principal de CI.
  Los dos errores son setup de `tests/infra/test_keycloak_claim.py`, antes de ejecutar
  sus asserts: Testcontainers no obtuvo el puerto efímero 8080 de Keycloak.
- Repetición aislada de esos dos tests: mismo error. Diagnóstico con un contenedor
  equivalente confirmó proceso `running`, sin OOM, y puerto publicado visible al
  consultar inmediatamente después de la excepción. La causa probable es una carrera
  de descubrimiento del puerto en Docker Desktop/Testcontainers, sin confirmación
  definitiva de la causa raíz. No se modificó la fixture ni se
  rebajaron sus verificaciones. Queda pendiente resolver o verificar en Linux/CI.
- Warning existente: importación deprecada de `testcontainers.postgres` en las
  fixtures de infraestructura. No se modificó por ser ajeno a observabilidad.

No afirmar suite final completamente verde. La autenticación del Keycloak del
Compose sí quedó verificada con tokens reales en los smokes; no equivale a dar por
aprobados los dos tests de infraestructura que no llegaron a ejecutar sus asserts.

## Evidencias privadas locales (no versionar)

- `.local/smoke-20261124T010952.json`: primera validación local, previa a Cloud.
- `.local/smoke-20261124T011258.json`: validación HTTP en Cloud.
- `.local/smoke-20261124T011643.json`: iteración con SQLAlchemy aún sin spans SQL.
- `.local/smoke-20261124T012009.json`: versión final con spans de psycopg.
- `.local/metrics-final.prom`: métricas finales del Collector.
- `.local/pytest-full.log`: primera suite completa.
- `.local/pytest-full-final.log`: suite final con dos errores de setup.
- `.local/pytest-keycloak-retry.log`: repetición aislada.
- `.local/build-final.log`: última construcción.

El dashboard y Tempo también se observaron en el navegador; no se afirma haber
guardado capturas de pantalla en el repositorio. Se conservaron los archivos
textuales y los trace IDs anteriores para repetir las consultas y tomar capturas.
Los `.env` privados y `.local/` están ignorados por Git y excluidos del contexto de
build. La revisión de archivos versionados y nuevos no encontró valores de los
secretos locales. Ningún workflow tiene cambios.

## Pendientes

Pruebas de carga k6, percentiles con volumen suficiente, errores y throughput,
CPU/RSS bajo carga, recuperación/reinicio, E2E completa y prueba de aprobación de
conductor/vehículo con documentación sintética mediante la API. Comprobar también
aceptación de solicitud bajo carga y sus observaciones de actualización operativa.
La disponibilidad aquí es estado local de M3; no acredita confirmación ni viaje de M4.
Resolver el descubrimiento de puerto de Keycloak en la suite local antes de afirmar
que toda la suite final pasó. No se hizo merge a main ni se modificaron workflows.
El procedimiento de reproducción está en [KEYCLOAK-TESTCONTAINERS.md](KEYCLOAK-TESTCONTAINERS.md)
y la reanudación para carga en [RETOMAR-K6.md](RETOMAR-K6.md).

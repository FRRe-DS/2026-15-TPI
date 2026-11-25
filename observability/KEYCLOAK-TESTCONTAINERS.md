# Dos errores pendientes de Keycloak/Testcontainers

## Pruebas afectadas y resultado

Archivo sin modificaciones: `backend/tests/infra/test_keycloak_claim.py`.

- `test_el_token_real_trae_los_ids_como_enteros`.
- `test_el_token_de_servicio_solo_trae_el_rol_de_lectura`.

En la suite final del 23/11/2026 hubo **1394 passed, 2 errors**, cobertura **96,31 %**.
Ambas pruebas fallaron en el **setup de la misma fixture de Keycloak**, antes de
validar sus asserts. La repetición aislada dio **2 errors**. No son pruebas
aprobadas, omitidas ni fallos de las assertions sobre claims.

## Entorno y error observado

Windows, Docker Desktop con contenedores Linux, Python 3.12.15,
Testcontainers 4.15.0 y Keycloak `quay.io/keycloak/keycloak:26.8.1`.
La fixture crea un Keycloak efímero con `start-dev --import-realm`, importa un
realm de prueba y publica el puerto interno 8080 en un puerto aleatorio del host.
No usa el Keycloak del Compose ni debe ocupar deliberadamente el 8080 del host.

La excepción ocurre en `contenedor.start()`, al preparar la espera HTTP sobre
`/realms/m3`, antes de solicitar tokens:

```text
HttpWaitStrategy.wait_until_ready → _build_url
→ get_exposed_port(8080) → DockerClient.port
ConnectionError: Port mapping for container <id-efimero> and port 8080 is not available
```

Un contenedor equivalente de diagnóstico estaba `running`, con exit code 0 y
`OOMKilled=False`; una consulta inmediatamente posterior mostró un puerto host
asignado al `8080/tcp`. **Causa probable:** carrera entre el inicio del contenedor
y la lectura de su publicación de puertos en Docker Desktop/Testcontainers.
La causa raíz definitiva queda pendiente. No atribuirlo a credenciales inválidas,
al Collector ni a un conflicto estático con los puertos del Grupo 02 sin evidencia.

## Reproducción aislada

Desde la raíz del Grupo 15, con Docker Desktop disponible. Usar las dependencias
fijadas del repositorio y ejecutar fuera de un sandbox que bloquee Docker o sockets:

```powershell
Set-Location backend
# Si todavía no existe el entorno Python 3.12:
uv sync --frozen --all-groups --python 3.12
New-Item -ItemType Directory -Force ../.local | Out-Null
& ./.venv/Scripts/python.exe -m pytest tests/infra/test_keycloak_claim.py -vv -ra *> ../.local/pytest-keycloak-repro.log
$testExit = $LASTEXITCODE
Get-Content ../.local/pytest-keycloak-repro.log -Tail 60
Write-Output "Exit code: $testExit"
Set-Location ..
```

Si ya existe `.venv`, no es necesario ejecutar `uv sync` nuevamente. `uv` debe
estar instalado; en la máquina de implementación también se dispone de la copia
privada `.local/tooling/bin/uv.exe` en la raíz del repositorio.
Una ejecución puede tener un resultado distinto por el carácter temporal del
problema; registrar el resultado real, versiones, fecha y logs de cada intento.
Si Docker no está disponible y las pruebas se omiten, eso no reproduce el error
ni constituye una validación exitosa.

Para inspeccionar un contenedor efímero que aún exista, obtener su ID del log:

```powershell
docker inspect --format '{{json .State}}' ID_EFIMERO
docker port ID_EFIMERO 8080/tcp
docker logs --tail 40 ID_EFIMERO
```

El reaper puede haberlo eliminado al terminar pytest. No usar IDs de los servicios
de Compose ni modificar puertos/credenciales de esos servicios para este ensayo.
Guardar la salida sólo bajo `.local/` y revisar cualquier log antes de compartirlo.

## Próximo diagnóstico

Repetir el archivo en Linux/CI con el lock actual; observar si el puerto existe en
el instante del fallo y cómo evoluciona. Si se confirma la carrera, evaluar en una
tarea separada una espera acotada de publicación del puerto o una versión compatible
de Testcontainers, conservando todas las assertions de seguridad. No modificar
workflows, bajar validaciones ni usar `xfail`/`skip` para cerrar observabilidad.

La autenticación real del Keycloak del Compose fue comprobada por los smokes, pero
no sustituye las verificaciones de tipos de claims y rol de servicio de estos tests.
Logs históricos privados: `.local/pytest-full-final.log` y
`.local/pytest-keycloak-retry.log`. La primera suite completa dio 1396 aprobadas;
no reemplaza el resultado final con errores documentado arriba.

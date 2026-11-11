#!/usr/bin/env bash
# Prueba de humo del entorno Compose (T107).
#
# Levanta el stack, espera a Keycloak y a la API, obtiene un token de operador
# con password grant y verifica:
#   - GET /api/v1/conductores con token responde 200 y trae al menos un conductor;
#   - GET /api/v1/conductores sin token responde 401 con el formato de error.
#
# Uso:
#   .github/scripts/humo.sh
#   .github/scripts/humo.sh --preparar
#
# Variables opcionales:
#   COMPOSE_ENV_FILE       archivo .env (por defecto .env)
#   COMPOSE_FILE           archivo Compose (por defecto docker-compose.yml)
#   CONSERVAR_ENTORNO=1    no ejecuta `docker compose down` al terminar
#   BORRAR_VOLUMENES=1     elimina tambien los volumenes al bajar el stack

set -euo pipefail

MODO="${1:-}"
if [[ -n "$MODO" && "$MODO" != "--preparar" ]]; then
    echo "Uso: $0 [--preparar]" >&2
    exit 2
fi

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCHIVO_ENV="${COMPOSE_ENV_FILE:-$RAIZ/.env}"
ARCHIVO_COMPOSE="${COMPOSE_FILE:-$RAIZ/docker-compose.yml}"
umask 077
ARCHIVO_RESPUESTA="$(mktemp)"
ARCHIVO_CABECERAS="$(mktemp)"
ARCHIVO_FORMULARIO="$(mktemp)"
ARCHIVO_AUTORIZACION="$(mktemp)"

COMPOSE=(docker compose --env-file "$ARCHIVO_ENV" -f "$ARCHIVO_COMPOSE")

limpiar() {
    local estado=$?
    trap - EXIT

    if [[ "$estado" -ne 0 ]]; then
        echo "--- Estado de los servicios ---" >&2
        "${COMPOSE[@]}" ps >&2 || true
        echo "--- Ultimos logs ---" >&2
        "${COMPOSE[@]}" logs --tail=200 >&2 || true
    fi

    rm -f "$ARCHIVO_RESPUESTA"
    rm -f "$ARCHIVO_CABECERAS"
    rm -f "$ARCHIVO_FORMULARIO"
    rm -f "$ARCHIVO_AUTORIZACION"

    if [[ "${CONSERVAR_ENTORNO:-0}" != "1" ]]; then
        local argumentos=(down --remove-orphans)
        if [[ "${BORRAR_VOLUMENES:-0}" == "1" ]]; then
            argumentos+=(--volumes)
        fi
        "${COMPOSE[@]}" "${argumentos[@]}" >/dev/null 2>&1 || true
    fi

    exit "$estado"
}
trap limpiar EXIT

for comando in docker curl python3 chmod; do
    if ! command -v "$comando" >/dev/null 2>&1; then
        echo "ERROR: falta el comando '$comando'." >&2
        exit 1
    fi
done

if [[ ! -f "$ARCHIVO_ENV" ]]; then
    echo "ERROR: no existe $ARCHIVO_ENV. Copia .env.example y completalo." >&2
    exit 1
fi
if [[ ! -f "$ARCHIVO_COMPOSE" ]]; then
    echo "ERROR: no existe $ARCHIVO_COMPOSE." >&2
    exit 1
fi

set +a
# shellcheck source=/dev/null
. "$ARCHIVO_ENV"
# A previous export from the caller remains attached to a sourced assignment.
# Keep secrets available only to this shell; Compose reads its own env file.
export -n \
    POSTGRES_PASSWORD \
    M3_DB_PASSWORD \
    KEYCLOAK_DB_PASSWORD \
    KEYCLOAK_ADMIN_PASSWORD \
    KEYCLOAK_M3_CLIENT_SECRET \
    RATE_LIMIT_HMAC_SECRET \
    M3_OPERADOR_PASSWORD \
    M3_CONDUCTOR_PASSWORD \
    M3_SERVICIO_PASSWORD \
    REDIS_PASSWORD \
    DATABASE_URL \
    TOKEN 2>/dev/null || true
chmod 600 "$ARCHIVO_RESPUESTA" "$ARCHIVO_CABECERAS" \
    "$ARCHIVO_FORMULARIO" "$ARCHIVO_AUTORIZACION"

: "${KEYCLOAK_M3_CLIENT_SECRET:?Falta KEYCLOAK_M3_CLIENT_SECRET en el .env}"
: "${M3_OPERADOR_USERNAME:?Falta M3_OPERADOR_USERNAME en el .env}"
: "${M3_OPERADOR_PASSWORD:?Falta M3_OPERADOR_PASSWORD en el .env}"
: "${REDIS_PASSWORD:?Falta REDIS_PASSWORD en el .env}"

API_BASE="${API_URL:-http://localhost:${API_PORT:-8080}}"
KEYCLOAK_BASE="${KEYCLOAK_PUBLIC_URL:-http://localhost:${KEYCLOAK_PORT:-8081}}"
FRONTEND_BASE="http://localhost:${FRONTEND_PORT:-3000}"
API_BASE="${API_BASE%/}"
KEYCLOAK_BASE="${KEYCLOAK_BASE%/}"
REALM="${KEYCLOAK_REALM:-m3}"
CLIENT_ID="${KEYCLOAK_M3_CLIENT_ID:-m3-api}"

esperar_http() {
    local url="$1"
    local nombre="$2"
    local intentos="${3:-150}"

    for ((intento = 1; intento <= intentos; intento++)); do
        if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
            echo "OK: $nombre disponible"
            return 0
        fi
        sleep 2
    done

    echo "ERROR: $nombre no respondio a tiempo ($url)." >&2
    return 1
}

esperar_redis_saludable() {
    local intentos="${1:-30}"
    local contenedor
    local estado

    for ((intento = 1; intento <= intentos; intento++)); do
        contenedor="$("${COMPOSE[@]}" ps -q redis)"
        if [[ -n "$contenedor" ]]; then
            estado="$(docker inspect --format '{{.State.Health.Status}}' "$contenedor" 2>/dev/null || true)"
            if [[ "$estado" == "healthy" ]]; then
                echo "OK: Redis saludable"
                return 0
            fi
        fi
        sleep 2
    done

    echo "ERROR: Redis no alcanzó el estado saludable." >&2
    return 1
}

obtener_token() {
    printf '%s\0' \
        "grant_type" "password" \
        "client_id" "$CLIENT_ID" \
        "client_secret" "$KEYCLOAK_M3_CLIENT_SECRET" \
        "username" "$M3_OPERADOR_USERNAME" \
        "password" "$M3_OPERADOR_PASSWORD" |
        python3 -c '
import sys
from urllib.parse import urlencode

campos = sys.stdin.buffer.read().split(b"\0")
if campos[-1] == b"":
    campos.pop()
if len(campos) % 2:
    raise SystemExit("ERROR: formulario OAuth incompleto.")
pares = zip(campos[::2], campos[1::2])
sys.stdout.write(urlencode([(k.decode(), v.decode()) for k, v in pares]))
' > "$ARCHIVO_FORMULARIO"

    curl -fsS --max-time 10 \
        -X POST "$KEYCLOAK_BASE/realms/$REALM/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        --data-binary "@$ARCHIVO_FORMULARIO" |
        python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])'
}

comprobar_listado() {
    local codigo
    codigo="$(
        curl -sS --max-time 10 \
            -o "$ARCHIVO_RESPUESTA" \
            -w '%{http_code}' \
            -H "@$ARCHIVO_AUTORIZACION" \
            "$API_BASE/api/v1/conductores"
    )"

    if [[ "$codigo" != "200" ]]; then
        echo "ERROR: GET /api/v1/conductores con token respondio $codigo (se esperaba 200)." >&2
        cat "$ARCHIVO_RESPUESTA" >&2
        return 1
    fi

    python3 - "$ARCHIVO_RESPUESTA" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as archivo:
    conductores = json.load(archivo)

if not isinstance(conductores, list) or not conductores:
    raise SystemExit("ERROR: el listado no contiene conductores.")

print(f"OK: {len(conductores)} conductores en el listado")
PY
}

comprobar_sin_token() {
    local codigo
    codigo="$(
        curl -sS --max-time 10 \
            -o "$ARCHIVO_RESPUESTA" \
            -w '%{http_code}' \
            "$API_BASE/api/v1/conductores"
    )"

    if [[ "$codigo" != "401" ]]; then
        echo "ERROR: GET /api/v1/conductores sin token respondio $codigo (se esperaba 401)." >&2
        cat "$ARCHIVO_RESPUESTA" >&2
        return 1
    fi

    python3 - "$ARCHIVO_RESPUESTA" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as archivo:
    cuerpo = json.load(archivo)

if cuerpo.get("codigo") != "NO_AUTENTICADO":
    raise SystemExit(f"ERROR: codigo de error inesperado: {cuerpo!r}")

print("OK: sin token responde 401 NO_AUTENTICADO")
PY
}

comprobar_limite_anonimo() {
    local limite="${RATE_LIMIT_ANON_REQUESTS:-60}"
    local codigo
    local rechazado=0

    echo "==> Verificando rate limit anónimo"
    for ((intento = 1; intento <= limite + 1; intento++)); do
        codigo="$(
            curl -sS --max-time 10 \
                -D "$ARCHIVO_CABECERAS" \
                -o "$ARCHIVO_RESPUESTA" \
                -w '%{http_code}' \
                "$API_BASE/api/v1/conductores"
        )"
        if [[ "$codigo" == "429" ]]; then
            rechazado=1
            break
        fi
        if [[ "$codigo" != "401" ]]; then
            echo "ERROR: solicitud anonima respondio $codigo (se esperaba 401 o 429)." >&2
            cat "$ARCHIVO_RESPUESTA" >&2
            return 1
        fi
    done

    if [[ "$rechazado" -ne 1 ]]; then
        echo "ERROR: no se alcanzo el limite anonimo de $limite solicitudes." >&2
        return 1
    fi
    if ! grep -qiE '^Retry-After: [1-9][0-9]*' "$ARCHIVO_CABECERAS"; then
        echo "ERROR: 429 no incluyo un Retry-After positivo." >&2
        cat "$ARCHIVO_CABECERAS" >&2
        return 1
    fi
    python3 - "$ARCHIVO_RESPUESTA" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as archivo:
    cuerpo = json.load(archivo)

if cuerpo.get("codigo") != "LIMITE_DE_SOLICITUDES":
    raise SystemExit(f"ERROR: codigo de rate limit inesperado: {cuerpo!r}")

print("OK: 429 LIMITE_DE_SOLICITUDES con Retry-After")
PY
}

comprobar_falla_redis() {
    local codigo

    echo "==> Verificando fail-closed con Redis detenido"
    "${COMPOSE[@]}" stop redis
    codigo="$(
        curl -sS --max-time 10 \
            -o "$ARCHIVO_RESPUESTA" \
            -w '%{http_code}' \
            -H "@$ARCHIVO_AUTORIZACION" \
            "$API_BASE/api/v1/conductores"
    )"
    if [[ "$codigo" != "503" ]]; then
        echo "ERROR: con Redis detenido la API respondio $codigo (se esperaba 503)." >&2
        cat "$ARCHIVO_RESPUESTA" >&2
        return 1
    fi
    python3 - "$ARCHIVO_RESPUESTA" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as archivo:
    cuerpo = json.load(archivo)

if cuerpo.get("codigo") != "SERVICIO_TEMPORALMENTE_NO_DISPONIBLE":
    raise SystemExit(f"ERROR: codigo de Redis inesperado: {cuerpo!r}")

print("OK: Redis detenido responde 503 fail-closed")
PY

    codigo="$(
        curl -sS --max-time 10 \
            -o "$ARCHIVO_RESPUESTA" \
            -w '%{http_code}' \
            "$API_BASE/salud"
    )"
    if [[ "$codigo" != "200" ]]; then
        echo "ERROR: /salud respondio $codigo con Redis detenido (se esperaba 200)." >&2
        cat "$ARCHIVO_RESPUESTA" >&2
        return 1
    fi
    echo "OK: /salud permanece disponible con Redis detenido"
}

echo "==> Levantando el entorno Compose"
"${COMPOSE[@]}" up --build -d

esperar_redis_saludable
esperar_http \
    "$KEYCLOAK_BASE/realms/$REALM/.well-known/openid-configuration" \
    "Keycloak"
esperar_http "$API_BASE/salud" "API"
esperar_http "$FRONTEND_BASE" "Frontend"

if [[ "$MODO" == "--preparar" ]]; then
    echo "OK: entorno Compose preparado"
    exit 0
fi

echo "==> Solicitando token de operador"
TOKEN="$(obtener_token)"
export -n TOKEN 2>/dev/null || true
if [[ -z "$TOKEN" ]]; then
    echo "ERROR: Keycloak no devolvio un access_token." >&2
    exit 1
fi
printf 'Authorization: Bearer %s\n' "$TOKEN" > "$ARCHIVO_AUTORIZACION"
unset TOKEN
echo "OK: token de operador obtenido"

echo "==> Verificando el listado de conductores"
comprobar_listado
comprobar_sin_token

comprobar_limite_anonimo
comprobar_falla_redis

echo "OK: prueba de humo completada"

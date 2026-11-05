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
#
# Variables opcionales:
#   COMPOSE_ENV_FILE       archivo .env (por defecto infra/.env)
#   COMPOSE_FILE           archivo Compose (por defecto infra/docker-compose.yml)
#   CONSERVAR_ENTORNO=1    no ejecuta `docker compose down` al terminar
#   BORRAR_VOLUMENES=1     elimina tambien los volumenes al bajar el stack

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCHIVO_ENV="${COMPOSE_ENV_FILE:-$RAIZ/infra/.env}"
ARCHIVO_COMPOSE="${COMPOSE_FILE:-$RAIZ/infra/docker-compose.yml}"
ARCHIVO_RESPUESTA="$(mktemp)"

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

for comando in docker curl python3; do
    if ! command -v "$comando" >/dev/null 2>&1; then
        echo "ERROR: falta el comando '$comando'." >&2
        exit 1
    fi
done

if [[ ! -f "$ARCHIVO_ENV" ]]; then
    echo "ERROR: no existe $ARCHIVO_ENV. Copia infra/.env.example y completalo." >&2
    exit 1
fi
if [[ ! -f "$ARCHIVO_COMPOSE" ]]; then
    echo "ERROR: no existe $ARCHIVO_COMPOSE." >&2
    exit 1
fi

set -a
# shellcheck source=/dev/null
. "$ARCHIVO_ENV"
set +a

: "${KEYCLOAK_M3_CLIENT_SECRET:?Falta KEYCLOAK_M3_CLIENT_SECRET en el .env}"
: "${M3_OPERADOR_USERNAME:?Falta M3_OPERADOR_USERNAME en el .env}"
: "${M3_OPERADOR_PASSWORD:?Falta M3_OPERADOR_PASSWORD en el .env}"

API_BASE="${API_URL:-http://localhost:${API_PORT:-8080}}"
KEYCLOAK_BASE="${KEYCLOAK_PUBLIC_URL:-http://localhost:${KEYCLOAK_PORT:-8081}}"
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

obtener_token() {
    local respuesta
    respuesta="$(
        curl -fsS --max-time 10 \
            -X POST "$KEYCLOAK_BASE/realms/$REALM/protocol/openid-connect/token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            --data-urlencode "grant_type=password" \
            --data-urlencode "client_id=$CLIENT_ID" \
            --data-urlencode "client_secret=$KEYCLOAK_M3_CLIENT_SECRET" \
            --data-urlencode "username=$M3_OPERADOR_USERNAME" \
            --data-urlencode "password=$M3_OPERADOR_PASSWORD"
    )"

    printf '%s' "$respuesta" | python3 -c \
        'import json, sys; print(json.load(sys.stdin)["access_token"])'
}

comprobar_listado() {
    local codigo
    codigo="$(
        curl -sS --max-time 10 \
            -o "$ARCHIVO_RESPUESTA" \
            -w '%{http_code}' \
            -H "Authorization: Bearer $TOKEN" \
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

echo "==> Levantando el entorno Compose"
"${COMPOSE[@]}" up --build -d

esperar_http \
    "$KEYCLOAK_BASE/realms/$REALM/.well-known/openid-configuration" \
    "Keycloak"
esperar_http "$API_BASE/salud" "API"

echo "==> Solicitando token de operador"
TOKEN="$(obtener_token)"
if [[ -z "$TOKEN" ]]; then
    echo "ERROR: Keycloak no devolvio un access_token." >&2
    exit 1
fi
echo "OK: token de operador obtenido"

echo "==> Verificando el listado de conductores"
comprobar_listado
comprobar_sin_token

echo "OK: prueba de humo completada"

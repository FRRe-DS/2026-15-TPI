#!/usr/bin/env bash
# Ciclo de vida del stack de Compose para las pruebas E2E.
#
# No reemplaza a .github/scripts/humo.sh: ese script verifica el entorno con
# curl y este prepara el stack para Playwright. Ambos usan el mismo Compose.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARCHIVO_ENV="${COMPOSE_ENV_FILE:-$RAIZ/infra/.env}"
ARCHIVO_COMPOSE="${COMPOSE_FILE:-$RAIZ/infra/docker-compose.yml}"
COMPOSE=(docker compose --env-file "$ARCHIVO_ENV" -f "$ARCHIVO_COMPOSE")

uso() {
    cat <<'TXT'
Uso: stack.sh <comando>

  generar-env    Crea infra/.env desde .env.example con secretos aleatorios (si no existe)
  frontend-env   Escribe frontend/.env.local a partir de infra/.env
  up             Levanta el stack y espera a Keycloak y a la API
  wait           Espera a Keycloak y a la API sin levantar nada
  down           Baja el stack; con --volumes borra el volumen de PostgreSQL
  logs           Muestra los últimos 100 logs de cada servicio
TXT
}

clave() {
    openssl rand -hex "${1:-16}"
}

requerir_env() {
    if [[ ! -f "$ARCHIVO_ENV" ]]; then
        echo "ERROR: falta $ARCHIVO_ENV. Corré 'stack.sh generar-env'." >&2
        exit 1
    fi
}

cargar_env() {
    requerir_env
    set -a
    # Se descarta el CR para que el archivo funcione también con checkout de Windows.
    # shellcheck disable=SC1090
    . <(sed -e 's/\r$//' "$ARCHIVO_ENV")
    set +a
}

generar_env() {
    if [[ -f "$ARCHIVO_ENV" ]]; then
        echo "OK: ya existe $ARCHIVO_ENV (no se modifica)."
        return 0
    fi

    cp "$RAIZ/infra/.env.example" "$ARCHIVO_ENV"
    sed -i \
        -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(clave)|" \
        -e "s|^M3_DB_PASSWORD=.*|M3_DB_PASSWORD=$(clave)|" \
        -e "s|^KEYCLOAK_DB_PASSWORD=.*|KEYCLOAK_DB_PASSWORD=$(clave)|" \
        -e "s|^KEYCLOAK_ADMIN=.*|KEYCLOAK_ADMIN=admin|" \
        -e "s|^KEYCLOAK_ADMIN_PASSWORD=.*|KEYCLOAK_ADMIN_PASSWORD=$(clave)|" \
        -e "s|^KEYCLOAK_M3_CLIENT_SECRET=.*|KEYCLOAK_M3_CLIENT_SECRET=$(clave 32)|" \
        -e "s|^M3_OPERADOR_PASSWORD=.*|M3_OPERADOR_PASSWORD=$(clave)|" \
        -e "s|^M3_CONDUCTOR_PASSWORD=.*|M3_CONDUCTOR_PASSWORD=$(clave)|" \
        "$ARCHIVO_ENV"

    # El .env.example puede venir con CRLF según el checkout; bash y Compose
    # esperan LF.
    sed -i 's/\r$//' "$ARCHIVO_ENV"

    echo "OK: generado $ARCHIVO_ENV con secretos aleatorios."
}

frontend_env() {
    cargar_env
    local destino="$RAIZ/frontend/.env.local"

    cat > "$destino" <<EOF
API_URL=http://localhost:${API_PORT:-8080}/api/v1
KEYCLOAK_URL=${KEYCLOAK_PUBLIC_URL:-http://localhost:8081}
KEYCLOAK_REALM=${KEYCLOAK_REALM:-m3}
KEYCLOAK_CLIENT_ID=${KEYCLOAK_M3_CLIENT_ID:-m3-api}
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_M3_CLIENT_SECRET}
TEST_USER=${M3_OPERADOR_USERNAME:-operador.m3}
TEST_PASSWORD=${M3_OPERADOR_PASSWORD}
EOF

    echo "OK: escrito $destino."
}

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

    echo "ERROR: $nombre no respondió a tiempo ($url)." >&2
    return 1
}

wait_stack() {
    cargar_env
    esperar_http \
        "${KEYCLOAK_PUBLIC_URL:-http://localhost:${KEYCLOAK_PORT:-8081}}/realms/${KEYCLOAK_REALM:-m3}/.well-known/openid-configuration" \
        "Keycloak"
    esperar_http "http://localhost:${API_PORT:-8080}/salud" "API"
}

up() {
    requerir_env
    echo "==> Levantando Compose"
    "${COMPOSE[@]}" up --build -d
    wait_stack
}

down() {
    requerir_env
    local argumentos=(down --remove-orphans)
    if [[ "${1:-}" == "--volumes" ]]; then
        argumentos+=(--volumes)
    fi
    "${COMPOSE[@]}" "${argumentos[@]}"
}

case "${1:-}" in
    generar-env) generar_env ;;
    frontend-env) frontend_env ;;
    up) up ;;
    wait) wait_stack ;;
    down) shift; down "${1:-}" ;;
    logs) requerir_env; "${COMPOSE[@]}" logs --tail=100 ;;
    *) uso; exit 1 ;;
esac

#!/usr/bin/env bash
# Crea las bases y los roles de M3 y Keycloak con credenciales tomadas del
# entorno. Se ejecuta una sola vez, cuando el volumen de PostgreSQL está vacío.
#
# RNF-05: cada base pertenece a un usuario distinto y se revoca CONNECT a
# PUBLIC para que el usuario de M3 no pueda abrir la base de Keycloak.
# RNF-06: no hay contraseñas literales en este archivo.

set -euo pipefail

: "${POSTGRES_USER:?Falta POSTGRES_USER}"
: "${POSTGRES_DB:?Falta POSTGRES_DB}"
: "${M3_DB_NAME:?Falta M3_DB_NAME}"
: "${M3_DB_USER:?Falta M3_DB_USER}"
: "${M3_DB_PASSWORD:?Falta M3_DB_PASSWORD}"
: "${KEYCLOAK_DB_NAME:?Falta KEYCLOAK_DB_NAME}"
: "${KEYCLOAK_DB_USER:?Falta KEYCLOAK_DB_USER}"
: "${KEYCLOAK_DB_PASSWORD:?Falta KEYCLOAK_DB_PASSWORD}"

if [[ "$M3_DB_USER" == "$KEYCLOAK_DB_USER" ]]; then
    echo "ERROR: M3_DB_USER y KEYCLOAK_DB_USER deben ser distintos (RNF-05)." >&2
    exit 1
fi

if [[ "$M3_DB_NAME" == "$KEYCLOAK_DB_NAME" ]]; then
    echo "ERROR: M3_DB_NAME y KEYCLOAK_DB_NAME deben ser distintos (RNF-05)." >&2
    exit 1
fi

PSQL=(psql --no-password --set=ON_ERROR_STOP=1
    --set=m3_db="$M3_DB_NAME"
    --set=m3_user="$M3_DB_USER"
    --set=m3_password="$M3_DB_PASSWORD"
    --set=keycloak_db="$KEYCLOAK_DB_NAME"
    --set=keycloak_user="$KEYCLOAK_DB_USER"
    --set=keycloak_password="$KEYCLOAK_DB_PASSWORD")

# psql no hereda variables locales; se pasan explícitamente por --set.
crear_rol_con_variables() {
    local usuario="$1"
    local clave="$2"
    "${PSQL[@]}" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        --set=usuario="$usuario" --set=clave="$clave" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'usuario')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'usuario') \gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'usuario', :'clave') \gexec
SQL
}

crear_base() {
    local base="$1"
    local duenio="$2"
    "${PSQL[@]}" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        --set=base="$base" --set=duenio="$duenio" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'base', :'duenio')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'base') \gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'base', :'duenio') \gexec
SQL
}

crear_rol_con_variables "$M3_DB_USER" "$M3_DB_PASSWORD"
crear_rol_con_variables "$KEYCLOAK_DB_USER" "$KEYCLOAK_DB_PASSWORD"

crear_base "$M3_DB_NAME" "$M3_DB_USER"
crear_base "$KEYCLOAK_DB_NAME" "$KEYCLOAK_DB_USER"

# Aislamiento: nadie accede por el pseudo-rol PUBLIC. Sólo el dueño recibe
# CONNECT. El usuario m3 no tiene ningún privilegio sobre la base keycloak.
"${PSQL[@]}" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=m3_db="$M3_DB_NAME" --set=keycloak_db="$KEYCLOAK_DB_NAME" \
    --set=m3_user="$M3_DB_USER" --set=keycloak_user="$KEYCLOAK_DB_USER" <<'SQL'
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'m3_db') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', :'keycloak_db') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM %I', :'keycloak_db', :'m3_user') \gexec
SELECT format('REVOKE ALL ON DATABASE %I FROM %I', :'m3_db', :'keycloak_user') \gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'m3_db', :'m3_user') \gexec
SELECT format('GRANT CONNECT, TEMP ON DATABASE %I TO %I', :'keycloak_db', :'keycloak_user') \gexec
SQL

# Cada dueño administra el esquema public de su propia base.
"${PSQL[@]}" --username "$POSTGRES_USER" --dbname "$M3_DB_NAME" \
    --set=duenio="$M3_DB_USER" <<'SQL'
SELECT format('ALTER SCHEMA public OWNER TO %I', :'duenio') \gexec
SELECT format('GRANT ALL ON SCHEMA public TO %I', :'duenio') \gexec
SQL

"${PSQL[@]}" --username "$POSTGRES_USER" --dbname "$KEYCLOAK_DB_NAME" \
    --set=duenio="$KEYCLOAK_DB_USER" <<'SQL'
SELECT format('ALTER SCHEMA public OWNER TO %I', :'duenio') \gexec
SELECT format('GRANT ALL ON SCHEMA public TO %I', :'duenio') \gexec
SQL

echo "Bases '$M3_DB_NAME' y '$KEYCLOAK_DB_NAME' creadas con usuarios aislados."

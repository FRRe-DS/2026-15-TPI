"""Genera secretos locales y configura la vista agregada sin imprimir credenciales."""

import argparse
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env.observability.local"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", action="store_true")
    args = parser.parse_args()
    if not ENV.exists():
        values = {}
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value or secrets.token_hex(24)
        values.update(
            {
                "COMPOSE_PROJECT_NAME": "m3-grupo15",
                "POSTGRES_PORT": "15432",
                "API_PORT": "18080",
                "KEYCLOAK_PORT": "18081",
                "FRONTEND_PORT": "13000",
                "M3_API_IMAGE": "m3-grupo15-backend:observability",
                "KEYCLOAK_PUBLIC_URL": "http://localhost:18081",
                "KEYCLOAK_ADMIN": "admin",
                "OTEL_SQL_PASSWORD": secrets.token_hex(24),
            }
        )
        ENV.write_text(
            "\n".join(f"{k}={v}" for k, v in values.items()) + "\n", encoding="utf-8"
        )
        print("Creado .env.observability.local; conservar privado.")
    if args.sql:
        values = dict(
            line.split("=", 1) for line in ENV.read_text().splitlines() if "=" in line
        )
        password = values["OTEL_SQL_PASSWORD"]
        if not password.isalnum():
            raise ValueError("La contraseña SQL local debe ser alfanumérica")
        sql = (ROOT / "observability/available-drivers.sql").read_text(encoding="utf-8")
        sql += f"\nALTER ROLE m3_otel PASSWORD '{password}';\n"
        subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ENV),
                "-p",
                "m3-grupo15",
                "-f",
                "docker-compose.yml",
                "exec",
                "-T",
                "postgres",
                "psql",
                "-X",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "postgres",
                "-d",
                "m3",
            ],
            input=sql,
            text=True,
            check=True,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
        )
        print("Vista agregada y rol de lectura configurados.")


if __name__ == "__main__":
    main()

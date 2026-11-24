"""Operaciones sintéticas exclusivamente contra el entorno local aislado."""

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    values = dict(
        line.split("=", 1)
        for line in (ROOT / ".env.observability.local").read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    if values["COMPOSE_PROJECT_NAME"] != "m3-grupo15":
        raise ValueError("Sólo se permite el proyecto de prueba m3-grupo15")
    token_url = f"http://localhost:{values['KEYCLOAK_PORT']}/realms/m3/protocol/openid-connect/token"
    form = urlencode(
        {
            "grant_type": "password",
            "client_id": values["KEYCLOAK_M3_CLIENT_ID"],
            "client_secret": values["KEYCLOAK_M3_CLIENT_SECRET"],
            "username": values["M3_OPERADOR_USERNAME"],
            "password": values["M3_OPERADOR_PASSWORD"],
        }
    ).encode()
    with urlopen(Request(token_url, data=form), timeout=20) as response:
        token = json.load(response)["access_token"]
    evidence = {"date": datetime.now(UTC).isoformat(), "operations": []}
    base = f"http://localhost:{values['API_PORT']}/api/v1"

    def operation(method, path, body):
        trace_id = secrets.token_hex(16)
        request = Request(
            base + path,
            data=json.dumps(body).encode(),
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "traceparent": f"00-{trace_id}-{secrets.token_hex(8)}-01",
            },
        )
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
            evidence["operations"].append(
                {"method": method, "status": response.status, "trace_id": trace_id}
            )
        return result

    dni = str(80000000 + secrets.randbelow(19999999))
    result = operation(
        "POST",
        "/conductores",
        {
            "dni": dni,
            "nombre": "Sintetico",
            "apellido": "Observabilidad",
            "telefono": "0000000000",
            "email": f"m3-otel-{dni}@example.invalid",
        },
    )
    conductor_id = result["id"]
    for state in ("CONECTADO", "DESCONECTADO"):
        operation("PATCH", f"/conductores/{conductor_id}/estado", {"estado": state})
    target = ROOT / ".local" / f"smoke-{datetime.now(UTC):%Y%m%dT%H%M%S}.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    print(f"Evidencia privada: {target}")


if __name__ == "__main__":
    main()

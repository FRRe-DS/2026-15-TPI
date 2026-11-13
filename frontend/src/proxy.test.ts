// @vitest-environment node
import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "./proxy";
import { NOMBRE_COOKIE_SESION } from "./lib/sesion";

function crearToken(payload: Record<string, unknown>): string {
  const parte = (objeto: unknown) =>
    Buffer.from(JSON.stringify(objeto)).toString("base64url");
  return `${parte({ alg: "none", typ: "JWT" })}.${parte(payload)}.firma`;
}

const segundosAhora = () => Math.floor(Date.now() / 1000);

const tokenVigente = () =>
  crearToken({ id_conductor: 1, exp: segundosAhora() + 300 });

const tokenVencido = () =>
  crearToken({ id_conductor: 1, exp: segundosAhora() - 1 });

function pedido(pathname: string, token?: string): NextRequest {
  return new NextRequest(`http://localhost${pathname}`, {
    headers: token ? { cookie: `${NOMBRE_COOKIE_SESION}=${token}` } : undefined,
  });
}

function destinoDe(respuesta: Response): string | null {
  return respuesta.headers.get("location");
}

describe("proxy de sesión del conductor", () => {
  it.each(["/estado", "/solicitudes", "/viaje", "/ubicacion"])(
    "sin sesión, %s redirige al login",
    (ruta) => {
      const respuesta = proxy(pedido(ruta));

      expect(respuesta.status).toBe(307);
      expect(destinoDe(respuesta)).toBe("http://localhost/login");
    }
  );

  it.each([
    ["vencida", tokenVencido()],
    ["mal formada", "no-es-un-jwt"],
  ])("con una sesión %s también redirige al login", (_caso, token) => {
    const respuesta = proxy(pedido("/estado", token));

    expect(respuesta.status).toBe(307);
    expect(destinoDe(respuesta)).toBe("http://localhost/login");
  });

  it("con una sesión vigente deja pasar a la pantalla protegida", () => {
    const respuesta = proxy(pedido("/estado", tokenVigente()));

    expect(respuesta.headers.get("x-middleware-next")).toBe("1");
    expect(destinoDe(respuesta)).toBeNull();
  });

  it.each(["/login", "/", "/api/sesion"])(
    "sin sesión, %s sigue siendo accesible",
    (ruta) => {
      const respuesta = proxy(pedido(ruta));

      expect(respuesta.headers.get("x-middleware-next")).toBe("1");
      expect(destinoDe(respuesta)).toBeNull();
    }
  );
});

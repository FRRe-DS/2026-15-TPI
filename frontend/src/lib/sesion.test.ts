import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DELETE, GET, POST } from "../app/api/sesion/route";
import { crearCookieSesion, leerSesion } from "./sesion";

function crearToken(idConductor: number, exp: number): string {
  const payload = Buffer.from(JSON.stringify({ id_conductor: idConductor, exp })).toString("base64url");
  return `header.${payload}.signature`;
}

describe("sesión del conductor", () => {
  const envOriginal = process.env;

  beforeEach(() => {
    process.env = {
      ...envOriginal,
      NODE_ENV: "production",
      KEYCLOAK_URL: "https://keycloak.test",
      KEYCLOAK_REALM: "m3",
      KEYCLOAK_CLIENT_ID: "m3-api",
      KEYCLOAK_CLIENT_SECRET: "client-secret",
    };
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    process.env = envOriginal;
    vi.unstubAllGlobals();
  });

  it("guarda el token en una cookie HttpOnly, SameSite=Lax y Secure fuera de desarrollo", () => {
    const cookie = crearCookieSesion("access-token", 300);

    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("Path=/");
    expect(cookie).toContain("Max-Age=300");
  });

  it("lee id_conductor del claim y rechaza tokens ausentes o vencidos", () => {
    const ahora = 1_800_000_000;

    expect(leerSesion(crearToken(42, ahora + 60), ahora)).toEqual({
      id_conductor: 42,
      token: crearToken(42, ahora + 60),
    });
    expect(leerSesion(null, ahora)).toBeNull();
    expect(leerSesion(crearToken(42, ahora), ahora)).toBeNull();
  });

  it("el login no devuelve credenciales ni tokens al cliente", async () => {
    const accessToken = crearToken(42, Math.floor(Date.now() / 1000) + 300);
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: accessToken,
          refresh_token: "refresh-secret",
          expires_in: 300,
          token_type: "Bearer",
        }),
        { status: 200 }
      )
    );

    const response = await POST(
      new Request("http://localhost/api/sesion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "conductor", password: "password-secret" }),
      })
    );
    const responseText = await response.text();

    expect(response.status).toBe(200);
    expect(responseText).toBe(JSON.stringify({ id_conductor: 42 }));
    expect(responseText).not.toContain("password-secret");
    expect(responseText).not.toContain("client-secret");
    expect(responseText).not.toContain(accessToken);
    expect(responseText).not.toContain("refresh-secret");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("trata la sesión ausente o vencida como no autenticada y permite cerrar sesión", async () => {
    const sinCookie = await GET(new Request("http://localhost/api/sesion"));
    const tokenVencido = crearToken(42, Math.floor(Date.now() / 1000) - 1);
    const vencida = await GET(
      new Request("http://localhost/api/sesion", {
        headers: { Cookie: `sesion_conductor=${tokenVencido}` },
      })
    );
    const cierre = await DELETE();

    expect(sinCookie.status).toBe(401);
    expect(vencida.status).toBe(401);
    expect(cierre.status).toBe(204);
    expect(cierre.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(cierre.headers.get("set-cookie")).toContain("HttpOnly");
  });
});

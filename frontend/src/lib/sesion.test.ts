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

  it("guarda el token en una cookie segura HttpOnly", () => {
    const cookie = crearCookieSesion("access-token", 300);
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("Max-Age=300");
  });

  it("obtiene id_conductor del token y rechaza tokens ausentes o vencidos", () => {
    const ahora = 1_800_000_000;
    const token = crearToken(42, ahora + 60);
    expect(leerSesion(token, ahora)).toEqual({ id_conductor: 42, token });
    expect(leerSesion(null, ahora)).toBeNull();
    expect(leerSesion(crearToken(42, ahora), ahora)).toBeNull();
  });

  it("procesa credenciales en el servidor y no devuelve el token al cliente", async () => {
    const accessToken = crearToken(42, Math.floor(Date.now() / 1000) + 300);
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
      access_token: accessToken,
      refresh_token: "refresh-secret",
      expires_in: 300,
    })));

    const response = await POST(new Request("http://localhost/api/sesion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "conductor", password: "password-secret" }),
    }));
    const body = await response.text();

    expect(response.status).toBe(200);
    expect(body).toBe(JSON.stringify({ id_conductor: 42 }));
    expect(body).not.toContain("password-secret");
    expect(body).not.toContain("client-secret");
    expect(body).not.toContain(accessToken);
    expect(body).not.toContain("refresh-secret");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("acepta el formulario nativo y redirige sin exponer credenciales", async () => {
    const token = crearToken(42, Math.floor(Date.now() / 1000) + 300);
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
      access_token: token,
      expires_in: 300,
    })));

    const response = await POST(new Request("http://localhost/api/sesion", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ usuario: "conductor", contrasena: "password-secret" }),
    }));

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("http://localhost/estado");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(vi.mocked(fetch).mock.calls[0][1]?.body).toContain("password-secret");
  });

  it("redirige los errores de credenciales y permite cerrar sesión", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 401 }));
    const login = await POST(new Request("http://localhost/api/sesion", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ usuario: "conductor", contrasena: "incorrecta" }),
    }));
    const cierre = await DELETE();

    expect(login.status).toBe(303);
    expect(login.headers.get("location")).toBe("http://localhost/login?error=credenciales");
    expect(cierre.status).toBe(204);
    expect(cierre.headers.get("set-cookie")).toContain("Max-Age=0");
    expect(cierre.headers.get("set-cookie")).toContain("HttpOnly");
  });

  it("rechaza sesiones ausentes o vencidas", async () => {
    const sinCookie = await GET(new Request("http://localhost/api/sesion"));
    const vencida = await GET(new Request("http://localhost/api/sesion", {
      headers: { Cookie: `sesion_conductor=${crearToken(42, Math.floor(Date.now() / 1000) - 1)}` },
    }));
    expect(sinCookie.status).toBe(401);
    expect(vencida.status).toBe(401);
  });
});

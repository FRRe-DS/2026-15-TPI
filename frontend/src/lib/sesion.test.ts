import { describe, it, expect, vi, afterEach } from "vitest";
import { ErrorAutenticacion } from "./token";
import {
  iniciarSesion,
  leerIdConductor,
  leerSesion,
  opcionesCookieSesion,
} from "./sesion";

const AHORA = 1_700_000_000_000; // milisegundos
const enSegundos = (ms: number) => Math.floor(ms / 1000);

function crearToken(payload: Record<string, unknown>): string {
  const parte = (objeto: unknown) =>
    Buffer.from(JSON.stringify(objeto)).toString("base64url");
  return `${parte({ alg: "none", typ: "JWT" })}.${parte(payload)}.firma`;
}

const tokenValido = () =>
  crearToken({ id_conductor: 1, exp: enSegundos(AHORA) + 300 });

describe("leerIdConductor", () => {
  it("devuelve el id_conductor del claim", () => {
    expect(leerIdConductor(tokenValido())).toBe(1);
  });

  it.each(["", "no-es-un-jwt", "a.b.c"])(
    "devuelve null si el token está mal formado (%s)",
    (token) => {
      expect(leerIdConductor(token)).toBeNull();
    }
  );

  it("devuelve null si el token no trae el claim", () => {
    expect(leerIdConductor(crearToken({ exp: enSegundos(AHORA) + 300 }))).toBeNull();
  });

  it.each(["1", 0, -3, 1.5])("ignora el id_conductor inválido %s", (valor) => {
    expect(leerIdConductor(crearToken({ id_conductor: valor }))).toBeNull();
  });
});

describe("leerSesion", () => {
  it("con un token vigente devuelve el id del conductor", () => {
    expect(leerSesion(tokenValido(), AHORA)).toEqual({ idConductor: 1 });
  });

  it.each([undefined, null, ""])("sin token (%s) no hay sesión", (token) => {
    expect(leerSesion(token, AHORA)).toBeNull();
  });

  it("un token vencido cuenta como sin sesión", () => {
    const vencido = crearToken({ id_conductor: 1, exp: enSegundos(AHORA) - 1 });

    expect(leerSesion(vencido, AHORA)).toBeNull();
  });

  it("un token que vence justo ahora cuenta como sin sesión", () => {
    const venceAhora = crearToken({ id_conductor: 1, exp: enSegundos(AHORA) });

    expect(leerSesion(venceAhora, AHORA)).toBeNull();
  });

  it("un token sin vencimiento no se acepta", () => {
    expect(leerSesion(crearToken({ id_conductor: 1 }), AHORA)).toBeNull();
  });

  it("un token vigente sin id_conductor no abre sesión", () => {
    const sinId = crearToken({ exp: enSegundos(AHORA) + 300 });

    expect(leerSesion(sinId, AHORA)).toBeNull();
  });
});

describe("opcionesCookieSesion", () => {
  it("es httpOnly, SameSite=Lax y vale para todo el sitio", () => {
    expect(opcionesCookieSesion(300, true)).toMatchObject({
      httpOnly: true,
      sameSite: "lax",
      path: "/",
    });
  });

  it("dura lo mismo que el token", () => {
    expect(opcionesCookieSesion(300, true).maxAge).toBe(300);
  });

  it("es Secure en producción y no en desarrollo", () => {
    expect(opcionesCookieSesion(300, true).secure).toBe(true);
    expect(opcionesCookieSesion(300, false).secure).toBe(false);
  });
});

describe("iniciarSesion", () => {
  const CONFIG = {
    keycloakUrl: "http://keycloak.test",
    realm: "m3",
    clientId: "m3-api",
    clientSecret: "secreto-de-prueba",
  };

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function simularKeycloak(status: number, cuerpo: unknown) {
    const fetchSimulado = vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: "",
      json: async () => cuerpo,
    });
    vi.stubGlobal("fetch", fetchSimulado);
    return fetchSimulado;
  }

  it("pide el token a Keycloak con el usuario y la contraseña recibidos", async () => {
    const fetchSimulado = simularKeycloak(200, {
      access_token: tokenValido(),
      expires_in: 300,
    });

    await iniciarSesion("conductor.m3", "clave-del-formulario", CONFIG);

    const [url, init] = fetchSimulado.mock.calls[0];
    expect(url).toBe("http://keycloak.test/realms/m3/protocol/openid-connect/token");
    expect((init as RequestInit).method).toBe("POST");
    const cuerpo = new URLSearchParams((init as RequestInit).body as string);
    expect(cuerpo.get("grant_type")).toBe("password");
    expect(cuerpo.get("client_id")).toBe("m3-api");
    expect(cuerpo.get("client_secret")).toBe("secreto-de-prueba");
    expect(cuerpo.get("username")).toBe("conductor.m3");
    expect(cuerpo.get("password")).toBe("clave-del-formulario");
  });

  it("devuelve el token, su duración y el id del conductor", async () => {
    const token = tokenValido();
    simularKeycloak(200, { access_token: token, expires_in: 300 });

    const sesion = await iniciarSesion("conductor.m3", "clave", CONFIG);

    expect(sesion).toEqual({ accessToken: token, expiresIn: 300, idConductor: 1 });
  });

  it("rechaza credenciales inválidas sin repetir la contraseña en el mensaje", async () => {
    simularKeycloak(401, {
      error: "invalid_grant",
      error_description: "Invalid user credentials",
    });

    const error = await iniciarSesion("conductor.m3", "clave-secreta-123", CONFIG).catch(
      (e: unknown) => e
    );

    expect(error).toBeInstanceOf(ErrorAutenticacion);
    expect((error as Error).message).not.toContain("clave-secreta-123");
  });

  it("falla si el token no trae id_conductor (usuario que no es conductor)", async () => {
    simularKeycloak(200, {
      access_token: crearToken({ exp: enSegundos(AHORA) + 300 }),
      expires_in: 300,
    });

    await expect(iniciarSesion("operador.m3", "clave", CONFIG)).rejects.toBeInstanceOf(
      ErrorAutenticacion
    );
  });

  it("pide un token nuevo en cada inicio de sesión y no reutiliza el de otro usuario", async () => {
    const fetchSimulado = simularKeycloak(200, {
      access_token: tokenValido(),
      expires_in: 300,
    });

    await iniciarSesion("conductor.m3", "clave", CONFIG);
    await iniciarSesion("otro.conductor", "otra-clave", CONFIG);

    expect(fetchSimulado).toHaveBeenCalledTimes(2);
  });

  it("falla con ErrorAutenticacion si no hay conexión con Keycloak", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sin red")));

    await expect(iniciarSesion("conductor.m3", "clave", CONFIG)).rejects.toBeInstanceOf(
      ErrorAutenticacion
    );
  });
});
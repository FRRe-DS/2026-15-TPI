// @vitest-environment node
import { describe, it, expect, vi, afterEach } from "vitest";
import { POST, DELETE } from "./route";
import * as sesion from "../../../lib/sesion";
import { ErrorAutenticacion } from "../../../lib/token";

vi.mock("../../../lib/sesion", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../../lib/sesion")>();
  return { ...original, iniciarSesion: vi.fn() };
});

function pedido(cuerpo: unknown) {
  return new Request("http://localhost/api/sesion", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: typeof cuerpo === "string" ? cuerpo : JSON.stringify(cuerpo),
  });
}

const SESION = { accessToken: "token-secreto", expiresIn: 300, idConductor: 1 };

afterEach(() => {
  vi.mocked(sesion.iniciarSesion).mockReset();
});

describe("POST /api/sesion", () => {
  it("con credenciales válidas responde 200 y guarda el token en una cookie httpOnly", async () => {
    vi.mocked(sesion.iniciarSesion).mockResolvedValue(SESION);

    const respuesta = await POST(pedido({ usuario: "conductor.m3", password: "clave" }));

    expect(respuesta.status).toBe(200);
    const cookie = respuesta.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("token-secreto");
    expect(cookie).toMatch(/httponly/i);
    expect(cookie).toMatch(/samesite=lax/i);
    expect(cookie).toMatch(/max-age=300/i);
  });

  it("nunca devuelve el token ni la contraseña en el cuerpo", async () => {
    vi.mocked(sesion.iniciarSesion).mockResolvedValue(SESION);

    const respuesta = await POST(pedido({ usuario: "conductor.m3", password: "clave-secreta-123" }));
    const texto = await respuesta.text();

    expect(texto).not.toContain("token-secreto");
    expect(texto).not.toContain("clave-secreta-123");
    expect(JSON.parse(texto)).toEqual({ idConductor: 1 });
  });

  it("con credenciales inválidas responde 401 y no crea la cookie", async () => {
    vi.mocked(sesion.iniciarSesion).mockRejectedValue(
      new ErrorAutenticacion("Error en autenticación (401): Invalid user credentials")
    );

    const respuesta = await POST(pedido({ usuario: "conductor.m3", password: "mala" }));

    expect(respuesta.status).toBe(401);
    expect(respuesta.headers.get("set-cookie")).toBeNull();
    expect((await respuesta.json()).codigo).toBe("CREDENCIALES_INVALIDAS");
  });

  it.each([{}, { usuario: "x" }, { usuario: "", password: "" }, "no es json"])(
    "con un cuerpo inválido responde 400 y no llama a Keycloak",
    async (cuerpo) => {
      const respuesta = await POST(pedido(cuerpo));

      expect(respuesta.status).toBe(400);
      expect(sesion.iniciarSesion).not.toHaveBeenCalled();
    }
  );
});

describe("DELETE /api/sesion", () => {
  it("borra la cookie de sesión", async () => {
    const respuesta = await DELETE();
    const cookie = respuesta.headers.get("set-cookie") ?? "";

    expect(cookie).toContain("sesion_m3=");
    expect(cookie).toMatch(/max-age=0/i);
  });
});
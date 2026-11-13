// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { POST } from "./route";
import * as api from "../../../lib/api";
import { NOMBRE_COOKIE_SESION } from "../../../lib/sesion";

vi.mock("../../../lib/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../../lib/api")>();
  return { ...original, actualizarEstado: vi.fn() };
});

const AHORA = Math.floor(Date.now() / 1000);

function crearToken(payload: Record<string, unknown>): string {
  const parte = (objeto: unknown) =>
    Buffer.from(JSON.stringify(objeto)).toString("base64url");
  return `${parte({ alg: "none", typ: "JWT" })}.${parte(
    { id_conductor: 7, exp: AHORA + 300, ...payload }
  )}.firma`;
}

function pedido(cuerpo: unknown, token: string | null = crearToken({})): Request {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Cookie = `${NOMBRE_COOKIE_SESION}=${token}`;

  return new Request("http://localhost/api/ubicacion", {
    method: "POST",
    headers,
    body: typeof cuerpo === "string" ? cuerpo : JSON.stringify(cuerpo),
  });
}

afterEach(() => {
  vi.mocked(api.actualizarEstado).mockReset();
});

describe("POST /api/ubicacion", () => {
  it("envía latitud y longitud juntas al conductor de la sesión", async () => {
    vi.mocked(api.actualizarEstado).mockResolvedValue({
      id_conductor: 7,
      estado: "OCUPADO",
      id_vehiculo_activo: 1,
      actualizado: "2026-11-10T18:50:00Z",
    });
    const token = crearToken({});

    const respuesta = await POST(pedido({ latitud: -34.6037, longitud: -58.3816 }, token));

    expect(respuesta.status).toBe(200);
    expect(api.actualizarEstado).toHaveBeenCalledWith(
      7,
      { latitud: -34.6037, longitud: -58.3816 },
      { token }
    );
  });

  it("sin sesión responde 401 y no llama a la API", async () => {
    const respuesta = await POST(
      pedido({ latitud: -34.6037, longitud: -58.3816 }, null)
    );

    expect(respuesta.status).toBe(401);
    expect((await respuesta.json()).codigo).toBe("SIN_SESION");
    expect(api.actualizarEstado).not.toHaveBeenCalled();
  });

  it.each([
    {},
    { latitud: -34.6037 },
    { longitud: -58.3816 },
    { latitud: "-34.6037", longitud: "-58.3816" },
    { latitud: -91, longitud: -58.3816 },
    { latitud: -34.6037, longitud: -181 },
    { latitud: Number.NaN, longitud: -58.3816 },
  ])("con coordenadas inválidas responde 400 y no llama a la API (%o)", async (cuerpo) => {
    const respuesta = await POST(pedido(cuerpo));

    expect(respuesta.status).toBe(400);
    expect((await respuesta.json()).codigo).toBe("SOLICITUD_INVALIDA");
    expect(api.actualizarEstado).not.toHaveBeenCalled();
  });

  it("propaga el error de la API con su estado y código", async () => {
    vi.mocked(api.actualizarEstado).mockRejectedValue(
      new api.ErrorApi(422, "El conductor no está habilitado.", "CONDUCTOR_NO_HABILITADO")
    );

    const respuesta = await POST(pedido({ latitud: -34.6037, longitud: -58.3816 }));

    expect(respuesta.status).toBe(422);
    expect(await respuesta.json()).toEqual({
      codigo: "CONDUCTOR_NO_HABILITADO",
      mensaje: "El conductor no está habilitado.",
    });
  });

  it("un error de conexión responde 502", async () => {
    vi.mocked(api.actualizarEstado).mockRejectedValue(
      new api.ErrorApi(0, "Error de conexión con la API: sin red")
    );

    const respuesta = await POST(pedido({ latitud: -34.6037, longitud: -58.3816 }));

    expect(respuesta.status).toBe(502);
    expect((await respuesta.json()).codigo).toBe("ERROR_API");
  });
});

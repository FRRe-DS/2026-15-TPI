import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listarConductores, ErrorApi } from "./api";
import * as tokenModule from "./token";
import type { ConductorConUbicacion } from "./tipos";

describe("listarConductores", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.restoreAllMocks();
    process.env = {
      ...originalEnv,
      API_URL: "http://api.test:8080/api/v1",
    };
    // Mock default token resolution
    vi.spyOn(tokenModule, "obtenerToken").mockResolvedValue("test-bearer-token");
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("envía Authorization: Bearer, llama a GET {API_URL}/conductores y devuelve el listado", async () => {
    const mockConductores: ConductorConUbicacion[] = [
      {
        id: 1,
        dni: "12345678",
        nombre: "Juan",
        apellido: "Pérez",
        telefono: "1122334455",
        email: "juan.perez@example.com",
        habilitacion: "APROBADA",
        conectado: true,
        disponible: true,
        documentos: [],
        vehiculos: [
          {
            id: 10,
            tipo: "AUTO",
            patente: "AB123CD",
            marca: "Toyota",
            modelo: "Corolla",
            anio: 2022,
            habilitacion: "APROBADA",
          },
        ],
        latitud: -27.451,
        longitud: -58.986,
        fecha_act_ubic: "2026-10-22T12:00:00Z",
      },
    ];

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockConductores,
    });
    vi.stubGlobal("fetch", mockFetch);

    const resultado = await listarConductores();

    expect(resultado).toEqual(mockConductores);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("http://api.test:8080/api/v1/conductores");
    expect(options.method).toBe("GET");
    expect(options.headers.Authorization).toBe("Bearer test-bearer-token");
  });

  it("lanza ErrorApi ante error 401", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({
        codigo: "TOKEN_INVALIDO",
        mensaje: "Token expirado o no válido",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(listarConductores()).rejects.toThrow(ErrorApi);

    try {
      await listarConductores();
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ErrorApi);
      const apiErr = err as ErrorApi;
      expect(apiErr.status).toBe(401);
      expect(apiErr.message).toMatch(/Token expirado o no válido|401/);
    }
  });

  it("lanza ErrorApi ante error 500", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({
        codigo: "ERROR_INTERNO",
        mensaje: "Error inesperado en el servidor",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(listarConductores()).rejects.toThrow(ErrorApi);

    try {
      await listarConductores();
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ErrorApi);
      const apiErr = err as ErrorApi;
      expect(apiErr.status).toBe(500);
      expect(apiErr.message).toMatch(/Error inesperado en el servidor|500/);
    }
  });
});

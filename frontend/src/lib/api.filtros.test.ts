import { describe, it, expect, vi, afterEach } from "vitest";
import { listarConductores } from "./api";

describe("listarConductores: filtros del contrato 1.2.0", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("envía el filtro estado como parámetro de consulta", async () => {
    const fetchSimulado = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchSimulado);

    await listarConductores({
      apiUrl: "http://api.test/api/v1",
      token: "token-de-prueba",
      filtros: { estado: "DISPONIBLE" },
    });

    const url = new URL(fetchSimulado.mock.calls[0][0] as string);
    expect(url.searchParams.get("estado")).toBe("DISPONIBLE");
  });
});
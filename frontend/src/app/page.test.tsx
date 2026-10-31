import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";
import * as apiModule from "../lib/api";
import type { ConductorConUbicacion } from "../lib/tipos";

describe("Page (Server Component)", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    vi.restoreAllMocks();
    process.env = { ...originalEnv };
    delete process.env.USE_MOCK;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("obtiene los datos en el servidor y renderiza el listado (modo real)", async () => {
    const mockConductores: ConductorConUbicacion[] = [
      {
        id: 1,
        dni: "12345678",
        nombre: "María",
        apellido: "González",
        telefono: "1198765432",
        email: "maria@example.com",
        habilitacion: "APROBADA",
        conectado: true,
        disponible: false,
        documentos: [],
        vehiculos: [],
      },
    ];

    vi.spyOn(apiModule, "listarConductores").mockResolvedValue(mockConductores);

    const PageComponent = await Page();
    render(PageComponent);

    expect(apiModule.listarConductores).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/María/)).toBeInTheDocument();
    expect(screen.getByText(/González/)).toBeInTheDocument();
    expect(screen.getByText("12345678")).toBeInTheDocument();
    expect(screen.getByText("APROBADA")).toBeInTheDocument();
  });

  it("si la API falla, muestra el estado de error sin romper (modo real)", async () => {
    vi.spyOn(apiModule, "listarConductores").mockRejectedValue(
      new apiModule.ErrorApi(500, "Error de prueba al conectar con la API")
    );

    const PageComponent = await Page();
    render(PageComponent);

    expect(apiModule.listarConductores).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText(/Error de prueba al conectar con la API/)
    ).toBeInTheDocument();
  });

  it("con USE_MOCK=true renderiza directamente los mocks sin llamar a la API", async () => {
    process.env.USE_MOCK = "true";
    const spy = vi.spyOn(apiModule, "listarConductores");

    const PageComponent = await Page();
    render(PageComponent);

    expect(spy).not.toHaveBeenCalled();
    // Verifica que se renderice al menos un conductor del mock
    expect(screen.getByText("María")).toBeInTheDocument();
    expect(screen.getByText("González")).toBeInTheDocument();
    expect(screen.getByText("28345678")).toBeInTheDocument();
  });
});

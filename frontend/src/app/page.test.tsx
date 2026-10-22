import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";
import * as apiModule from "../lib/api";
import type { ConductorConUbicacion } from "../lib/tipos";

describe("Page (Server Component)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("obtiene los datos en el servidor y renderiza el listado", async () => {
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

  it("si la API falla, muestra el estado de error sin romper", async () => {
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
});

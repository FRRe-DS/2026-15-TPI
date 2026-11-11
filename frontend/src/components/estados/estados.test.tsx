import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EstadoCarga, EstadoError, EstadoVacio } from "./estados";

describe("estados", () => {
  it("muestra el mensaje de carga", () => {
    render(<EstadoCarga mensaje="Cargando solicitudes..." />);

    expect(screen.getByText("Cargando solicitudes...")).toBeInTheDocument();
  });

  it("muestra el mensaje de error con role alert", () => {
    render(<EstadoError mensaje="No se pudieron cargar las solicitudes" />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se pudieron cargar las solicitudes",
    );
  });

  it("muestra el mensaje de estado vacío", () => {
    render(<EstadoVacio mensaje="No hay solicitudes" />);

    expect(screen.getByText("No hay solicitudes")).toBeInTheDocument();
  });
});

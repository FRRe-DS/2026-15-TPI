import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ListadoConductores } from "./ListadoConductores";
import type { ConductorConUbicacion, EstadoHabilitacion } from "../lib/tipos";

describe("ListadoConductores", () => {
  const conductorEjemplo: ConductorConUbicacion = {
    id: 1,
    dni: "12345678",
    nombre: "Juan",
    apellido: "Pérez",
    telefono: "1122334455",
    email: "juan@example.com",
    habilitacion: "APROBADA",
    conectado: true,
    disponible: true,
    documentos: [],
    vehiculos: [],
  };

  it("muestra nombre, apellido, DNI y habilitación de cada conductor", () => {
    render(<ListadoConductores conductores={[conductorEjemplo]} />);

    expect(screen.getByText(/Juan/)).toBeInTheDocument();
    expect(screen.getByText(/Pérez/)).toBeInTheDocument();
    expect(screen.getByText("12345678")).toBeInTheDocument();
    expect(screen.getByText("APROBADA")).toBeInTheDocument();
  });

  it("muestra el estado vacío 'No hay conductores' si la lista está vacía", () => {
    render(<ListadoConductores conductores={[]} />);

    expect(screen.getByText("No hay conductores")).toBeInTheDocument();
  });

  it("muestra el estado de error con un mensaje claro si ocurre un fallo", () => {
    const mensajeError = "Error al conectar con la API de conductores";
    render(<ListadoConductores error={mensajeError} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(mensajeError)).toBeInTheDocument();
  });

  it("renderiza badges con data-estado correspondiente para cada estado de habilitación", () => {
    const estados: EstadoHabilitacion[] = [
      "APROBADA",
      "PENDIENTE",
      "OBSERVADA",
      "SUSPENDIDA",
      "RECHAZADA",
    ];

    const conductoresVarios: ConductorConUbicacion[] = estados.map((estado, index) => ({
      id: index + 1,
      dni: `1000000${index}`,
      nombre: `Nombre${index}`,
      apellido: `Apellido${index}`,
      telefono: "1122334455",
      email: `test${index}@example.com`,
      habilitacion: estado,
      conectado: false,
      disponible: false,
      documentos: [],
      vehiculos: [],
    }));

    const { container } = render(<ListadoConductores conductores={conductoresVarios} />);

    estados.forEach((estado) => {
      const badge = container.querySelector(`[data-estado="${estado}"]`);
      expect(badge).toBeInTheDocument();
      expect(badge?.textContent).toBe(estado);
    });
  });
});

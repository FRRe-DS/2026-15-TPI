import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ListadoConductores } from "./ListadoConductores";
import styles from "./ListadoConductores.module.css";
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
    estado: "DISPONIBLE",
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

  describe("badges de habilitación", () => {
    const casos: [EstadoHabilitacion, string][] = [
      ["APROBADA", styles.verde],
      ["PENDIENTE", styles.amarillo],
      ["OBSERVADA", styles.amarillo],
      ["SUSPENDIDA", styles.rojo],
      ["RECHAZADA", styles.rojo],
    ];

    it.each(casos)(
      "muestra la habilitación %s como badge con la clase de color correspondiente",
      (habilitacion, claseColor) => {
        render(
          <ListadoConductores
            conductores={[{ ...conductorEjemplo, habilitacion }]}
          />,
        );

        const badge = screen.getByText(habilitacion);

        expect(badge).toHaveClass(styles.badge);
        expect(badge).toHaveClass(claseColor);
      },
    );
  });
});

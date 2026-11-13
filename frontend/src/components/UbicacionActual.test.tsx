import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { UbicacionActual } from "./UbicacionActual";
import type { UbicacionConductor } from "../lib/tipos";

const UBICACION: UbicacionConductor = {
  id_conductor: 1,
  latitud: -34.6037,
  longitud: -58.3816,
  fecha_act_ubic: "2026-11-10T18:50:00Z",
};

const DESCONOCIDA: UbicacionConductor = {
  id_conductor: 1,
  latitud: null,
  longitud: null,
  fecha_act_ubic: null,
};

describe("UbicacionActual", () => {
  it("muestra la última latitud, longitud y fecha", () => {
    render(<UbicacionActual ubicacion={UBICACION} />);

    expect(screen.getByText("Latitud")).toBeInTheDocument();
    expect(screen.getByText("-34.6037")).toBeInTheDocument();
    expect(screen.getByText("Longitud")).toBeInTheDocument();
    expect(screen.getByText("-58.3816")).toBeInTheDocument();
    expect(screen.getByText("Última actualización")).toBeInTheDocument();
    expect(screen.getByText("10/11/2026 18:50:00 UTC")).toBeInTheDocument();
  });

  it("muestra «desconocida» cuando los tres campos son null", () => {
    render(<UbicacionActual ubicacion={DESCONOCIDA} />);

    expect(screen.getByText(/ubicación desconocida/i)).toBeInTheDocument();
    expect(screen.queryByText("Latitud")).not.toBeInTheDocument();
    expect(screen.queryByText("Longitud")).not.toBeInTheDocument();
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(screen.queryByText("0, 0")).not.toBeInTheDocument();
    expect(screen.queryByText("0.0")).not.toBeInTheDocument();
  });

  it("trata una ubicación ausente como desconocida", () => {
    render(<UbicacionActual ubicacion={null} />);

    expect(screen.getByText(/ubicación desconocida/i)).toBeInTheDocument();
    expect(screen.queryByText("Latitud")).not.toBeInTheDocument();
  });

  it("si hay coordenadas pero falta la fecha, no inventa una", () => {
    render(
      <UbicacionActual
        ubicacion={{ ...UBICACION, fecha_act_ubic: null }}
      />
    );

    expect(screen.getByText("-34.6037")).toBeInTheDocument();
    expect(screen.getByText(/desconocida/i)).toBeInTheDocument();
  });
});

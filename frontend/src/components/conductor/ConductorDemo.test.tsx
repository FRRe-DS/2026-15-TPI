import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ConductorDemoProvider,
  EstadoScreen,
  LoginScreen,
  SolicitudesScreen,
  UbicacionScreen,
  ViajeScreen,
} from "./ConductorDemo";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

function FlujoDemo() {
  return (
    <ConductorDemoProvider>
      <EstadoScreen />
      <SolicitudesScreen />
      <ViajeScreen />
      <UbicacionScreen />
    </ConductorDemoProvider>
  );
}

describe("flujo mock del conductor", () => {
  afterEach(() => vi.clearAllMocks());

  it("acepta una solicitud, registra al pasajero y finaliza el viaje", () => {
    render(<FlujoDemo />);

    fireEvent.click(screen.getByRole("button", { name: "Aceptar viaje" }));
    expect(screen.getAllByText("OCUPADO")).toHaveLength(3);
    expect(push).toHaveBeenCalledWith("/viaje");

    fireEvent.click(screen.getByRole("button", { name: "Pasajero subió" }));
    fireEvent.click(screen.getByRole("button", { name: "Finalizar viaje" }));

    expect(screen.getByText("No hay solicitudes por ahora.")).toBeInTheDocument();
    expect(push).toHaveBeenCalledWith("/solicitudes");
  });

  it("muestra la coordenada simulada durante un viaje y no ofrece OCUPADO como estado", () => {
    render(<FlujoDemo />);

    expect(screen.queryByRole("button", { name: "OCUPADO" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aceptar viaje" }));
    expect(screen.getByText("-27.45030, -58.98560")).toBeInTheDocument();
  });

  it("envía el login como formulario nativo y muestra errores sin exponer credenciales", () => {
    render(<LoginScreen error="credenciales" demoDisponible />);

    expect(document.querySelector("form")).toHaveAttribute("action", "/api/sesion");
    expect(document.querySelector("form")).toHaveAttribute("method", "post");
    expect(screen.getByLabelText("Contraseña")).toHaveAttribute("type", "password");
    expect(screen.getByRole("alert")).toHaveTextContent("Usuario o contraseña inválidos.");
    expect(screen.getByRole("link", { name: "Explorar modo demo" })).toHaveAttribute("href", "/estado");
  });
});

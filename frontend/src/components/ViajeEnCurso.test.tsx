import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ViajeEnCurso, type ViajeDetalle } from "./ViajeEnCurso";

const { pushMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: vi.fn(),
  }),
}));

const viajeEjemplo: ViajeDetalle = {
  id: 340,
  id_viaje: 5521,
  id_conductor: 1,
  estado: "ACEPTADO",
  pasajero: "Laura Gómez",
  origen: "Av. San Martín 1540",
  destino: "Maipú 850",
  tarifa: "4.250",
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("ViajeEnCurso (T727)", () => {
  it("muestra el viaje tras la aceptación con identificador, datos y estado OCUPADO", () => {
    render(<ViajeEnCurso viaje={viajeEjemplo} />);

    expect(screen.getByText(/Viaje #5521/i)).toBeInTheDocument();
    expect(screen.getByText("OCUPADO")).toBeInTheDocument();
    expect(screen.getByText(/Laura Gómez/i)).toBeInTheDocument();
    expect(screen.getByText(/Av\. San Martín 1540/i)).toBeInTheDocument();
    expect(screen.getByText(/Maipú 850/i)).toBeInTheDocument();
    expect(screen.getByText(/\$ 4\.250/i)).toBeInTheDocument();

    // Stepper inicial: paso 1 completado, paso 2 activo, paso 3 pendiente
    const paso1 = screen.getByRole("listitem", { name: /conductor en camino/i });
    const paso2 = screen.getByRole("listitem", { name: /pasajero a bordo/i });
    const paso3 = screen.getByRole("listitem", { name: /destino final/i });

    expect(paso1).toBeInTheDocument();
    expect(paso2).toHaveAttribute("aria-current", "step");
    expect(paso3).not.toHaveAttribute("aria-current");

    // Botones iniciales
    expect(screen.getByRole("button", { name: /pasajero subió/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /finalizar viaje/i })).toBeDisabled();
  });

  it("«Pasajero subió» cambia el paso mostrado y habilita «Finalizar viaje»", async () => {
    const user = userEvent.setup();
    render(<ViajeEnCurso viaje={viajeEjemplo} />);

    const botonSubio = screen.getByRole("button", { name: /pasajero subió/i });
    const botonFinalizar = screen.getByRole("button", { name: /finalizar viaje/i });

    expect(botonSubio).toBeEnabled();
    expect(botonFinalizar).toBeDisabled();

    const paso2 = screen.getByRole("listitem", { name: /pasajero a bordo/i });
    expect(paso2).toHaveAttribute("aria-current", "step");

    await user.click(botonSubio);

    // El paso avanza al paso 3 (viaje hacia el destino)
    const paso3 = screen.getByRole("listitem", { name: /destino final/i });
    expect(paso3).toHaveAttribute("aria-current", "step");
    expect(paso2).not.toHaveAttribute("aria-current");

    // Botón pasajero subió deshabilitado y finalizar viaje habilitado
    expect(botonSubio).toBeDisabled();
    expect(botonFinalizar).toBeEnabled();
  });

  it("«Finalizar viaje» pide DISPONIBLE y vuelve a las solicitudes", async () => {
    const user = userEvent.setup();
    const finalizarViajeMock = vi.fn().mockResolvedValue(undefined);

    render(
      <ViajeEnCurso
        viaje={viajeEjemplo}
        finalizarViaje={finalizarViajeMock}
      />
    );

    const botonSubio = screen.getByRole("button", { name: /pasajero subió/i });
    await user.click(botonSubio);

    const botonFinalizar = screen.getByRole("button", { name: /finalizar viaje/i });
    expect(botonFinalizar).toBeEnabled();

    await user.click(botonFinalizar);

    await waitFor(() => {
      expect(finalizarViajeMock).toHaveBeenCalledTimes(1);
    });
    expect(finalizarViajeMock).toHaveBeenCalledWith({ estado: "DISPONIBLE" });
    expect(pushMock).toHaveBeenCalledWith("/solicitudes");
  });

  it("nunca utiliza el texto «quedar disponible» en los botones", () => {
    render(<ViajeEnCurso viaje={viajeEjemplo} />);

    expect(screen.queryByText(/quedar disponible/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /quedar disponible/i })
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /finalizar viaje/i })).toBeInTheDocument();
  });

  it("si falla la finalización del viaje muestra alerta y no redirige", async () => {
    const user = userEvent.setup();
    const finalizarViajeMock = vi.fn().mockRejectedValue(
      new Error("Error al conectar con la API central")
    );

    render(
      <ViajeEnCurso
        viaje={viajeEjemplo}
        finalizarViaje={finalizarViajeMock}
      />
    );

    await user.click(screen.getByRole("button", { name: /pasajero subió/i }));
    await user.click(screen.getByRole("button", { name: /finalizar viaje/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Error al conectar con la API central/i
    );
    expect(pushMock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /finalizar viaje/i })).toBeEnabled();
  });

  it("muestra el estado de carga", () => {
    render(<ViajeEnCurso cargando />);

    expect(screen.getByRole("status")).toHaveTextContent(/cargando viaje en curso/i);
  });

  it("muestra el estado de error", () => {
    render(<ViajeEnCurso error="No se pudo cargar el viaje en curso" />);

    expect(screen.getByRole("alert")).toHaveTextContent(
      /No se pudo cargar el viaje en curso/i
    );
  });

  it("muestra el estado vacío «Sin viaje en curso» cuando no hay viaje", () => {
    render(<ViajeEnCurso viaje={null} />);

    expect(screen.getByText(/Sin viaje en curso/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /finalizar viaje/i })
    ).not.toBeInTheDocument();
  });
});

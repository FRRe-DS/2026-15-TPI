import { describe, it, expect, vi, afterEach } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { ListadoSolicitudes, type ResponderSolicitud } from "./ListadoSolicitudes";
import { ErrorApi } from "../lib/api";
import type { EstadoSolicitud, Solicitud } from "../lib/tipos";

function enSegundos(segundos: number): string {
  return new Date(Date.now() + segundos * 1000).toISOString();
}

function crearSolicitud(
  id: number,
  estado: EstadoSolicitud,
  venceEn: string,
): Solicitud {
  return {
    id,
    id_conductor: 1,
    id_viaje: 5000 + id,
    estado,
    vence_en: venceEn,
    respuesta:
      estado === "ACEPTADO" || estado === "RECHAZADO" ? estado : null,
    hora_rta:
      estado === "ACEPTADO" || estado === "RECHAZADO"
        ? "2026-11-13T11:59:00Z"
        : null,
  };
}

function crearResponder(): ReturnType<typeof vi.fn<ResponderSolicitud>> {
  return vi.fn<ResponderSolicitud>();
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("ListadoSolicitudes", () => {
  it("muestra aceptar y rechazar solo en las solicitudes PENDIENTE", () => {
    const solicitudes = [
      crearSolicitud(341, "PENDIENTE", enSegundos(120)),
      crearSolicitud(342, "ACEPTADO", "2026-11-13T11:00:00Z"),
      crearSolicitud(343, "RECHAZADO", "2026-11-13T10:00:00Z"),
      crearSolicitud(344, "VENCIDA", "2026-11-13T09:00:00Z"),
    ];

    render(
      <ListadoSolicitudes
        solicitudes={solicitudes}
        responder={crearResponder()}
      />,
    );

    const pendiente = screen.getByRole("listitem", {
      name: /solicitud 341/i,
    });
    expect(
      within(pendiente).getByRole("button", { name: /aceptar/i }),
    ).toBeInTheDocument();
    expect(
      within(pendiente).getByRole("button", { name: /rechazar/i }),
    ).toBeInTheDocument();

    expect(screen.getAllByRole("button", { name: /aceptar/i })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /rechazar/i })).toHaveLength(1);
    expect(screen.getByText("ACEPTADO")).toBeInTheDocument();
    expect(screen.getByText("RECHAZADO")).toBeInTheDocument();
    expect(screen.getByText("VENCIDA")).toBeInTheDocument();
  });

  it("hace la cuenta regresiva con vence_en y deshabilita los botones al vencer", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-13T12:00:00Z"));

    render(
      <ListadoSolicitudes
        solicitudes={[
          crearSolicitud(341, "PENDIENTE", "2026-11-13T12:00:30Z"),
        ]}
        responder={crearResponder()}
      />,
    );

    expect(screen.getByText("Vence en 30 s")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(screen.getByText("Vence en 20 s")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(20_000);
    });

    expect(screen.getByText(/oferta vencida/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /aceptar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /rechazar/i })).toBeDisabled();
  });

  it.each([
    ["Aceptar", "ACEPTADO"],
    ["Rechazar", "RECHAZADO"],
  ] as const)(
    "al pulsar %s envía respuesta %s y hora_rta en el cuerpo",
    async (boton, respuesta) => {
      const responder = crearResponder().mockImplementation(
        async (id, cuerpo) => ({
          ...crearSolicitud(id, cuerpo.respuesta, enSegundos(120)),
          respuesta: cuerpo.respuesta,
          hora_rta: cuerpo.hora_rta,
        }),
      );

      render(
        <ListadoSolicitudes
          solicitudes={[
            crearSolicitud(341, "PENDIENTE", enSegundos(120)),
          ]}
          responder={responder}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: new RegExp(boton, "i") }));

      await waitFor(() => expect(responder).toHaveBeenCalledTimes(1));

      const [id, cuerpo] = responder.mock.calls[0];
      expect(id).toBe(341);
      expect(cuerpo.respuesta).toBe(respuesta);
      expect(typeof cuerpo.hora_rta).toBe("string");
      expect(new Date(cuerpo.hora_rta).toISOString()).toBe(cuerpo.hora_rta);
    },
  );

  it("muestra «No hay solicitudes» cuando la lista está vacía", () => {
    render(<ListadoSolicitudes solicitudes={[]} />);

    expect(screen.getByText("No hay solicitudes")).toBeInTheDocument();
  });

  it("muestra «oferta vencida» cuando la API responde 410", async () => {
    const responder = crearResponder().mockRejectedValue(
      new ErrorApi(410, "La oferta ya venció", "OFERTA_VENCIDA"),
    );

    render(
      <ListadoSolicitudes
        solicitudes={[
          crearSolicitud(341, "PENDIENTE", enSegundos(120)),
        ]}
        responder={responder}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /aceptar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/oferta vencida/i);
  });

  it("muestra el conflicto cuando la API responde 409", async () => {
    const responder = crearResponder().mockRejectedValue(
      new ErrorApi(409, "La solicitud ya fue respondida", "SOLICITUD_YA_RESPONDIDA"),
    );

    render(
      <ListadoSolicitudes
        solicitudes={[
          crearSolicitud(341, "PENDIENTE", enSegundos(120)),
        ]}
        responder={responder}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /rechazar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/conflicto/i);
  });

  it("muestra el estado de carga", () => {
    render(<ListadoSolicitudes cargando />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Cargando solicitudes...",
    );
  });

  it("muestra el estado de error", () => {
    render(
      <ListadoSolicitudes error="No se pudo conectar con la API de solicitudes" />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      /No se pudo conectar con la API de solicitudes/,
    );
  });
});

import { describe, it, expect, vi, afterEach } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ControlEstado, type CambiarEstado } from "./ControlEstado";
import { ErrorApi } from "../lib/api";
import { MOCK_ESTADOS_CONDUCTOR } from "../mocks/conductor.mock";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ControlEstado (T723)", () => {
  describe("Botones de estado operativo", () => {
    it("ofrece botones interactivos para DESCONECTADO, CONECTADO y DISPONIBLE", () => {
      render(<ControlEstado estado="CONECTADO" />);

      expect(
        screen.getByRole("button", { name: "DESCONECTADO" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "CONECTADO" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "DISPONIBLE" })
      ).toBeInTheDocument();
    });

    it("nunca ofrece el estado OCUPADO entre las opciones de cambio", () => {
      render(<ControlEstado estado="CONECTADO" />);

      expect(
        screen.queryByRole("button", { name: /ocupado/i })
      ).not.toBeInTheDocument();
    });

    it("nunca ofrece OCUPADO como opción incluso si el estado actual es OCUPADO", () => {
      render(<ControlEstado estado="OCUPADO" />);

      // Muestra que el estado actual es OCUPADO
      expect(screen.getByTestId("estado-actual")).toHaveTextContent("OCUPADO");

      // Pero no hay ningún botón para cambiar a OCUPADO
      expect(
        screen.queryByRole("button", { name: /ocupado/i })
      ).not.toBeInTheDocument();

      // Los únicos botones disponibles siguen siendo DESCONECTADO, CONECTADO y DISPONIBLE
      const botones = screen.getAllByRole("button");
      expect(botones).toHaveLength(3);
      expect(
        screen.getByRole("button", { name: "DESCONECTADO" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "CONECTADO" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "DISPONIBLE" })
      ).toBeInTheDocument();
    });

    it("llama a cambiarEstado con el nuevo estado al presionar un botón", async () => {
      const cambiarEstado = vi.fn<CambiarEstado>().mockResolvedValue(undefined);
      render(
        <ControlEstado estado="DESCONECTADO" cambiarEstado={cambiarEstado} />
      );

      fireEvent.click(screen.getByRole("button", { name: "CONECTADO" }));

      await waitFor(() => {
        expect(cambiarEstado).toHaveBeenCalledTimes(1);
        expect(cambiarEstado).toHaveBeenCalledWith("CONECTADO");
      });
    });

    it("actualiza el estado actual tras un cambio exitoso", async () => {
      const cambiarEstado = vi
        .fn<CambiarEstado>()
        .mockResolvedValue(MOCK_ESTADOS_CONDUCTOR.DISPONIBLE);

      render(
        <ControlEstado estado="CONECTADO" cambiarEstado={cambiarEstado} />
      );

      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "CONECTADO"
      );

      fireEvent.click(screen.getByRole("button", { name: "DISPONIBLE" }));

      await waitFor(() => {
        expect(screen.getByTestId("estado-actual")).toHaveTextContent(
          "DISPONIBLE"
        );
      });
    });
  });

  describe("Error CONDUCTOR_NO_HABILITADO (422)", () => {
    it("muestra el error CONDUCTOR_NO_HABILITADO (422) y no cambia el estado", async () => {
      const errorHabilitacion = new ErrorApi(
        422,
        "El conductor no cuenta con habilitación vigente ni vehículo activo aprobado.",
        "CONDUCTOR_NO_HABILITADO"
      );
      const cambiarEstado = vi
        .fn<CambiarEstado>()
        .mockRejectedValue(errorHabilitacion);

      render(
        <ControlEstado estado="CONECTADO" cambiarEstado={cambiarEstado} />
      );

      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "CONECTADO"
      );

      fireEvent.click(screen.getByRole("button", { name: "DISPONIBLE" }));

      const alerta = await screen.findByRole("alert");
      expect(alerta).toBeInTheDocument();
      expect(alerta).toHaveTextContent("CONDUCTOR_NO_HABILITADO");
      expect(alerta).toHaveTextContent("422");
      expect(alerta).toHaveTextContent(
        "El conductor no cuenta con habilitación vigente"
      );

      // El estado debe permanecer en CONECTADO, sin avanzar a DISPONIBLE
      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "CONECTADO"
      );
    });
  });

  describe("Estados de carga y error", () => {
    it("muestra estado de carga inicial cuando cargando=true", () => {
      render(<ControlEstado cargando={true} />);

      const carga = screen.getByRole("status");
      expect(carga).toBeInTheDocument();
      expect(carga).toHaveTextContent(/cargando/i);
    });

    it("muestra indicador de carga y deshabilita botones mientras se guarda el nuevo estado", async () => {
      let resolverPromesa!: (valor: void) => void;
      const promesaBloqueada = new Promise<void>((resolve) => {
        resolverPromesa = resolve;
      });

      const cambiarEstado = vi
        .fn<CambiarEstado>()
        .mockReturnValue(promesaBloqueada);

      render(
        <ControlEstado estado="CONECTADO" cambiarEstado={cambiarEstado} />
      );

      fireEvent.click(screen.getByRole("button", { name: "DESCONECTADO" }));

      // Indicador de carga activo
      expect(screen.getByRole("status")).toHaveTextContent(
        /actualizando estado/i
      );

      // Botones deshabilitados durante la carga
      expect(
        screen.getByRole("button", { name: "DESCONECTADO" })
      ).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "CONECTADO" })
      ).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "DISPONIBLE" })
      ).toBeDisabled();

      // Completamos la promesa
      await act(async () => {
        resolverPromesa();
      });

      // El indicador de carga desaparece y los botones se reactivan
      await waitFor(() => {
        expect(screen.queryByRole("status")).not.toBeInTheDocument();
      });
      expect(
        screen.getByRole("button", { name: "DESCONECTADO" })
      ).not.toBeDisabled();
    });

    it("muestra alerta de error inicial cuando se pasa la prop error", () => {
      render(
        <ControlEstado
          estado="DESCONECTADO"
          error="No se pudo conectar con el servidor M3"
        />
      );

      const alerta = screen.getByRole("alert");
      expect(alerta).toBeInTheDocument();
      expect(alerta).toHaveTextContent(
        "No se pudo conectar con el servidor M3"
      );
    });

    it("muestra estado de error general cuando cambiarEstado falla por red o 500", async () => {
      const errorGeneral = new ErrorApi(500, "Error interno en el servidor.");
      const cambiarEstado = vi
        .fn<CambiarEstado>()
        .mockRejectedValue(errorGeneral);

      render(
        <ControlEstado estado="CONECTADO" cambiarEstado={cambiarEstado} />
      );

      fireEvent.click(screen.getByRole("button", { name: "DESCONECTADO" }));

      const alerta = await screen.findByRole("alert");
      expect(alerta).toBeInTheDocument();
      expect(alerta).toHaveTextContent("500");
      expect(alerta).toHaveTextContent("Error interno en el servidor.");
      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "CONECTADO"
      );
    });

    it("muestra mensaje de estado vacío si no se proporciona información de estado", () => {
      render(<ControlEstado estado={null} />);

      expect(
        screen.getByText(/sin información del estado/i)
      ).toBeInTheDocument();
      expect(screen.queryByRole("button")).not.toBeInTheDocument();
    });

    it("limpia el error previo si un intento posterior resulta exitoso", async () => {
      const cambiarEstado = vi
        .fn<CambiarEstado>()
        .mockRejectedValueOnce(
          new ErrorApi(422, "Error temporal", "CONDUCTOR_NO_HABILITADO")
        )
        .mockResolvedValueOnce(MOCK_ESTADOS_CONDUCTOR.DESCONECTADO);

      render(
        <ControlEstado estado="CONECTADO" cambiarEstado={cambiarEstado} />
      );

      // Primer intento: falla y muestra error
      fireEvent.click(screen.getByRole("button", { name: "DISPONIBLE" }));
      expect(await screen.findByRole("alert")).toBeInTheDocument();

      // Segundo intento: tiene éxito y limpia el error
      fireEvent.click(screen.getByRole("button", { name: "DESCONECTADO" }));

      await waitFor(() => {
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      });
      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "DESCONECTADO"
      );
    });
  });

  describe("Compatibilidad con objeto EstadoConductor", () => {
    it("admite un objeto EstadoConductor completo en la prop estado", () => {
      render(
        <ControlEstado estado={MOCK_ESTADOS_CONDUCTOR.DISPONIBLE} />
      );

      expect(screen.getByTestId("estado-actual")).toHaveTextContent(
        "DISPONIBLE"
      );
    });
  });
});

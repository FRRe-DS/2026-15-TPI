import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Navegacion } from "./Navegacion";

const { usePathnameMock } = vi.hoisted(() => ({
  usePathnameMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: usePathnameMock,
}));

describe("Navegacion", () => {
  afterEach(() => {
    vi.resetAllMocks();
  });

  it("enlaza a cada pantalla", () => {
    usePathnameMock.mockReturnValue("/");
    render(<Navegacion />);

    const pantallas = [
      { nombre: "Conductores", ruta: "/" },
      { nombre: "Iniciar sesión", ruta: "/login" },
      { nombre: "Estado", ruta: "/estado" },
      { nombre: "Solicitudes", ruta: "/solicitudes" },
      { nombre: "Viaje", ruta: "/viaje" },
      { nombre: "Ubicación", ruta: "/ubicacion" },
    ];

    for (const pantalla of pantallas) {
      expect(
        screen.getByRole("link", { name: pantalla.nombre }),
      ).toHaveAttribute("href", pantalla.ruta);
    }
  });

  it("marca la pantalla activa", () => {
    usePathnameMock.mockReturnValue("/solicitudes");
    render(<Navegacion />);

    expect(
      screen.getByRole("link", { name: "Solicitudes" }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Estado" })).not.toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});

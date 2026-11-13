import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";
import { NOMBRE_COOKIE_SESION } from "../../lib/sesion";

const { cookiesMock, getCookieMock, redirectMock, replaceMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  getCookieMock: vi.fn(),
  redirectMock: vi.fn(),
  replaceMock: vi.fn(),
}));

vi.mock("next/headers", () => ({
  cookies: cookiesMock,
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({ replace: replaceMock }),
}));

function crearToken(payload: Record<string, unknown>): string {
  const parte = (objeto: unknown) =>
    Buffer.from(JSON.stringify(objeto)).toString("base64url");
  return `${parte({ alg: "none", typ: "JWT" })}.${parte(payload)}.firma`;
}

const segundosAhora = () => Math.floor(Date.now() / 1000);

const tokenVigente = () =>
  crearToken({ id_conductor: 1, exp: segundosAhora() + 300 });

const tokenVencido = () =>
  crearToken({ id_conductor: 1, exp: segundosAhora() - 1 });

function simularCookie(token: string | null) {
  getCookieMock.mockImplementation((nombre: string) =>
    token !== null && nombre === NOMBRE_COOKIE_SESION
      ? { name: nombre, value: token }
      : undefined
  );
  cookiesMock.mockResolvedValue({ get: getCookieMock });
}

afterEach(() => {
  vi.resetAllMocks();
});

describe("Página de login (Server Component)", () => {
  // El login es el destino de la redirección de las pantallas protegidas
  // cuando no hay sesión; acá se verifica que sin sesión no se avance al estado.
  it("sin sesión muestra el formulario de login y no redirige al estado", async () => {
    simularCookie(null);

    const pagina = await Page();
    render(pagina);

    expect(getCookieMock).toHaveBeenCalledWith(NOMBRE_COOKIE_SESION);
    expect(redirectMock).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    expect(screen.getByLabelText("Contraseña")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /iniciar sesión/i })
    ).toBeInTheDocument();
  });

  it.each([
    ["vencido", tokenVencido()],
    ["mal formado", "no-es-un-jwt"],
    ["sin id_conductor", crearToken({ exp: segundosAhora() + 300 })],
  ])(
    "un token %s cuenta como sin sesión y deja al conductor en el login",
    async (_caso, token) => {
      simularCookie(token);

      const pagina = await Page();
      render(pagina);

      expect(redirectMock).not.toHaveBeenCalled();
      expect(screen.getByLabelText("Usuario")).toBeInTheDocument();
    }
  );

  it("con una sesión vigente redirige a la pantalla de estado", async () => {
    simularCookie(tokenVigente());
    redirectMock.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });

    await expect(Page()).rejects.toThrow("NEXT_REDIRECT");

    expect(redirectMock).toHaveBeenCalledTimes(1);
    expect(redirectMock).toHaveBeenCalledWith("/estado");
  });
});

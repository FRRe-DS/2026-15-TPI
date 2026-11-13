import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";
import * as apiModule from "../../lib/api";
import { NOMBRE_COOKIE_SESION } from "../../lib/sesion";
import type { Solicitud } from "../../lib/tipos";

const { cookiesMock, getCookieMock, redirectMock, pushMock } = vi.hoisted(
  () => ({
    cookiesMock: vi.fn(),
    getCookieMock: vi.fn(),
    redirectMock: vi.fn(),
    pushMock: vi.fn(),
  }),
);

vi.mock("next/headers", () => ({
  cookies: cookiesMock,
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

function crearToken(payload: Record<string, unknown>): string {
  const parte = (objeto: unknown) =>
    Buffer.from(JSON.stringify(objeto)).toString("base64url");
  return `${parte({ alg: "none", typ: "JWT" })}.${parte(payload)}.firma`;
}

const segundosAhora = () => Math.floor(Date.now() / 1000);

const tokenVigente = () =>
  crearToken({ id_conductor: 1, exp: segundosAhora() + 300 });

function simularCookie(token: string | null) {
  getCookieMock.mockImplementation((nombre: string) =>
    token !== null && nombre === NOMBRE_COOKIE_SESION
      ? { name: nombre, value: token }
      : undefined,
  );
  cookiesMock.mockResolvedValue({ get: getCookieMock });
}

describe("Página de Viaje (Server Component)", () => {
  const originalUseMock = process.env.USE_MOCK;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    process.env.USE_MOCK = originalUseMock;
    vi.resetAllMocks();
  });

  it("en modo mock (USE_MOCK=true) renderiza el viaje simulado sin llamar a la API", async () => {
    process.env.USE_MOCK = "true";

    const pagina = await Page();
    render(pagina);

    expect(screen.getByText(/Viaje #5521/i)).toBeInTheDocument();
    expect(screen.getByText("OCUPADO")).toBeInTheDocument();
    expect(screen.getByText(/Laura Gómez/i)).toBeInTheDocument();
  });

  it("sin sesión en modo real redirige a /login", async () => {
    process.env.USE_MOCK = "false";
    simularCookie(null);
    redirectMock.mockImplementation(() => {
      throw new Error("NEXT_REDIRECT");
    });

    await expect(Page()).rejects.toThrow("NEXT_REDIRECT");
    expect(redirectMock).toHaveBeenCalledWith("/login");
  });

  it("con sesión en modo real obtiene las solicitudes y renderiza el viaje", async () => {
    process.env.USE_MOCK = "false";
    simularCookie(tokenVigente());

    const solicitudesMock: Solicitud[] = [
      {
        id: 101,
        id_viaje: 7777,
        id_conductor: 1,
        estado: "ACEPTADO",
        vence_en: "2026-11-13T12:00:00Z",
        respuesta: "ACEPTADO",
        hora_rta: "2026-11-13T11:59:00Z",
      },
    ];

    vi.spyOn(apiModule, "listarSolicitudes").mockResolvedValue(solicitudesMock);

    const pagina = await Page();
    render(pagina);

    expect(apiModule.listarSolicitudes).toHaveBeenCalledWith(1, {
      token: expect.any(String),
      estado: "ACEPTADO",
    });
    expect(screen.getByText(/Viaje #7777/i)).toBeInTheDocument();
    expect(screen.getByText("OCUPADO")).toBeInTheDocument();
  });

  it("si la API falla muestra el estado de error", async () => {
    process.env.USE_MOCK = "false";
    simularCookie(tokenVigente());

    vi.spyOn(apiModule, "listarSolicitudes").mockRejectedValue(
      new apiModule.ErrorApi(500, "Error de prueba al conectar con la API"),
    );

    const pagina = await Page();
    render(pagina);

    expect(screen.getByRole("alert")).toHaveTextContent(
      /Error de prueba al conectar con la API/i,
    );
  });
});

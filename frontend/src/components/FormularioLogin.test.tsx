import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FormularioLogin } from "./FormularioLogin";

const { replaceMock } = vi.hoisted(() => ({
  replaceMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

function respuesta(status: number, cuerpo: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => cuerpo,
  } as Response;
}

function simularEnvio(resultado: Response | Error) {
  const fetchSimulado =
    resultado instanceof Error
      ? vi.fn().mockRejectedValue(resultado)
      : vi.fn().mockResolvedValue(resultado);
  vi.stubGlobal("fetch", fetchSimulado);
  return fetchSimulado;
}

async function completarFormulario(
  usuario = "conductor.m3",
  password = "clave-secreta"
) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Usuario"), usuario);
  await user.type(screen.getByLabelText("Contraseña"), password);
  await user.click(screen.getByRole("button", { name: /iniciar sesión/i }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  replaceMock.mockReset();
  localStorage.clear();
  sessionStorage.clear();
});

describe("FormularioLogin", () => {
  it("muestra los campos de usuario y contraseña", () => {
    render(<FormularioLogin />);

    const usuario = screen.getByLabelText("Usuario");
    const password = screen.getByLabelText("Contraseña");

    expect(usuario).toHaveAttribute("type", "text");
    expect(usuario).toHaveAttribute("autocomplete", "username");
    expect(password).toHaveAttribute("type", "password");
    expect(password).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByRole("button", { name: /iniciar sesión/i })).toBeInTheDocument();
  });

  it("envía las credenciales al servidor de Next, nunca directo a Keycloak", async () => {
    const fetchSimulado = simularEnvio(
      respuesta(200, { idConductor: 1 })
    );

    render(<FormularioLogin />);
    await completarFormulario();

    await waitFor(() => expect(fetchSimulado).toHaveBeenCalledTimes(1));
    const [url, init] = fetchSimulado.mock.calls[0] as [string, RequestInit];

    expect(url).toBe("/api/sesion");
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({
      "Content-Type": "application/json",
    });
    expect(init.credentials).toBe("same-origin");
    expect(JSON.parse(init.body as string)).toEqual({
      usuario: "conductor.m3",
      password: "clave-secreta",
    });
    expect(JSON.stringify(init)).not.toMatch(/keycloak|client_secret|grant_type/i);
  });

  it("ante credenciales inválidas muestra el mensaje y no redirige", async () => {
    simularEnvio(
      respuesta(401, {
        codigo: "CREDENCIALES_INVALIDAS",
        mensaje: "No se pudo iniciar sesión.",
      })
    );

    render(<FormularioLogin />);
    await completarFormulario("conductor.m3", "clave-incorrecta");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /credenciales inválidas/i
    );
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("con credenciales válidas redirige al estado y no guarda el token en el navegador", async () => {
    simularEnvio(respuesta(200, { idConductor: 1 }));

    render(<FormularioLogin />);
    await completarFormulario();

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/estado"));
    expect(replaceMock).toHaveBeenCalledTimes(1);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("mientras envía deshabilita el formulario y avisa que está verificando", async () => {
    let resolver: (respuesta: Response) => void = () => {};
    const pendiente = new Promise<Response>((resolve) => {
      resolver = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pendiente));

    render(<FormularioLogin />);
    await completarFormulario();

    const boton = screen.getByRole("button", { name: /verificando credenciales/i });
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute("aria-busy", "true");
    expect(screen.getByLabelText("Usuario")).toBeDisabled();
    expect(screen.getByLabelText("Contraseña")).toBeDisabled();

    resolver(respuesta(200, { idConductor: 1 }));
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/estado"));
  });

  it("si no hay conexión con el servidor muestra el error y no redirige", async () => {
    simularEnvio(new Error("sin red"));

    render(<FormularioLogin />);
    await completarFormulario();

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo conectar/i);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("ante un error del servidor muestra un mensaje y no redirige", async () => {
    simularEnvio(
      respuesta(500, { codigo: "ERROR_INTERNO", mensaje: "No se pudo iniciar sesión." })
    );

    render(<FormularioLogin />);
    await completarFormulario();

    expect(await screen.findByRole("alert")).toHaveTextContent(/no se pudo iniciar sesión/i);
    expect(replaceMock).not.toHaveBeenCalled();
  });
});

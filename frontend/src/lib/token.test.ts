import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { obtenerToken, ErrorAutenticacion, limpiarCacheToken } from "./token";

describe("obtenerToken (Keycloak)", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    limpiarCacheToken();
    vi.restoreAllMocks();
    process.env = {
      ...originalEnv,
      KEYCLOAK_URL: "http://keycloak.test:8081",
      KEYCLOAK_REALM: "m3",
      KEYCLOAK_CLIENT_ID: "frontend-client",
      KEYCLOAK_CLIENT_SECRET: "secret-123",
      TEST_USER: "operador_test",
      TEST_PASSWORD: "password_test",
    };
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.useRealTimers();
  });

  it("pide el token a /realms/m3/protocol/openid-connect/token con concesión de contraseña", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "mock-token-xyz",
        expires_in: 300,
        token_type: "Bearer",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const token = await obtenerToken();

    expect(token).toBe("mock-token-xyz");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe("http://keycloak.test:8081/realms/m3/protocol/openid-connect/token");
    expect(options.method).toBe("POST");
    expect(options.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");

    const params = new URLSearchParams(options.body);
    expect(params.get("grant_type")).toBe("password");
    expect(params.get("client_id")).toBe("frontend-client");
    expect(params.get("client_secret")).toBe("secret-123");
    expect(params.get("username")).toBe("operador_test");
    expect(params.get("password")).toBe("password_test");
  });

  it("reutiliza el token en caché hasta su vencimiento", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-22T10:00:00Z"));

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "mock-token-1",
        expires_in: 100, // expira en 100 segundos
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    // Primera llamada: pide token a Keycloak
    const token1 = await obtenerToken();
    expect(token1).toBe("mock-token-1");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Segunda llamada dentro del tiempo de expiración (50 segundos después): debe reutilizar
    vi.advanceTimersByTime(50 * 1000);
    const token2 = await obtenerToken();
    expect(token2).toBe("mock-token-1");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Tercera llamada luego del vencimiento: debe pedir uno nuevo
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: "mock-token-2",
        expires_in: 100,
      }),
    });

    vi.advanceTimersByTime(60 * 1000); // Pasaron 110s en total (> 100s)
    const token3 = await obtenerToken();
    expect(token3).toBe("mock-token-2");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("lanza ErrorAutenticacion si Keycloak responde un error", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({
        error: "invalid_grant",
        error_description: "Invalid user credentials",
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await expect(obtenerToken()).rejects.toThrow(ErrorAutenticacion);
    await expect(obtenerToken()).rejects.toThrow(/Invalid user credentials|401/);
  });
});

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  obtenerEstado,
  actualizarEstado,
  obtenerUbicacion,
  listarSolicitudes,
  responderSolicitud,
} from "./api";

const API = "http://api.test/api/v1";
const opciones = { apiUrl: API, token: "token-de-prueba" };

function simularRespuesta(status: number, cuerpo: unknown) {
  const fetchSimulado = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => cuerpo,
  });
  vi.stubGlobal("fetch", fetchSimulado);
  return fetchSimulado;
}

function primeraLlamada(fetchSimulado: ReturnType<typeof simularRespuesta>) {
  const [url, init] = fetchSimulado.mock.calls[0];
  return { url: new URL(url as string), init: init as RequestInit };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("obtenerEstado", () => {
  it("hace GET a /conductores/{id}/estado con el token y devuelve el cuerpo", async () => {
    const cuerpo = {
      id_conductor: 15,
      estado: "DISPONIBLE",
      id_vehiculo_activo: 3,
      actualizado: "2026-11-10T18:00:00Z",
    };
    const fetchSimulado = simularRespuesta(200, cuerpo);

    const resultado = await obtenerEstado(15, opciones);

    const { url, init } = primeraLlamada(fetchSimulado);
    expect(url.pathname).toBe("/api/v1/conductores/15/estado");
    expect(init.method).toBe("GET");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer token-de-prueba");
    expect(resultado).toEqual(cuerpo);
  });
});

describe("actualizarEstado", () => {
  it("hace PATCH a /conductores/{id}/estado con solo los campos indicados", async () => {
    const fetchSimulado = simularRespuesta(200, { id_conductor: 15, estado: "DISPONIBLE" });

    await actualizarEstado(15, { estado: "DISPONIBLE" }, opciones);

    const { url, init } = primeraLlamada(fetchSimulado);
    expect(url.pathname).toBe("/api/v1/conductores/15/estado");
    expect(init.method).toBe("PATCH");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ estado: "DISPONIBLE" });
  });

  it("envía latitud y longitud juntas cuando se informa la ubicación", async () => {
    const fetchSimulado = simularRespuesta(200, {});

    await actualizarEstado(15, { latitud: -34.6, longitud: -58.4 }, opciones);

    const { init } = primeraLlamada(fetchSimulado);
    expect(JSON.parse(init.body as string)).toEqual({ latitud: -34.6, longitud: -58.4 });
  });

  it("lanza ErrorApi con el código CONDUCTOR_NO_HABILITADO ante un 422", async () => {
    simularRespuesta(422, {
      codigo: "CONDUCTOR_NO_HABILITADO",
      mensaje: "El conductor no está habilitado.",
    });

    await expect(actualizarEstado(15, { estado: "DISPONIBLE" }, opciones)).rejects.toMatchObject({
      name: "ErrorApi",
      status: 422,
      codigo: "CONDUCTOR_NO_HABILITADO",
    });
  });
});

describe("obtenerUbicacion", () => {
    it("hace GET a /conductores/{id}/ubicacion y devuelve los campos null tal cual", async () => {
      const cuerpo = { id_conductor: 15, latitud: null, longitud: null, fecha_act_ubic: null };
      const fetchSimulado = simularRespuesta(200, cuerpo);
  
      const resultado = await obtenerUbicacion(15, opciones);
  
      const { url, init } = primeraLlamada(fetchSimulado);
      expect(url.pathname).toBe("/api/v1/conductores/15/ubicacion");
      expect(init.method).toBe("GET");
      expect(resultado).toEqual(cuerpo);
    });
  });
  
  describe("listarSolicitudes", () => {
    it("hace GET a /conductores/{id}/solicitudes sin filtro", async () => {
      const fetchSimulado = simularRespuesta(200, []);
  
      await listarSolicitudes(15, opciones);
  
      const { url } = primeraLlamada(fetchSimulado);
      expect(url.pathname).toBe("/api/v1/conductores/15/solicitudes");
      expect(url.search).toBe("");
    });
  
    it("envía el filtro estado como parámetro de consulta", async () => {
      const fetchSimulado = simularRespuesta(200, []);
  
      await listarSolicitudes(15, { ...opciones, estado: "PENDIENTE" });
  
      const { url } = primeraLlamada(fetchSimulado);
      expect(url.searchParams.get("estado")).toBe("PENDIENTE");
    });
  });
  
  describe("responderSolicitud", () => {
    it("hace POST a /solicitudes/{id} con respuesta y hora_rta", async () => {
      const fetchSimulado = simularRespuesta(200, { id: 340, estado: "ACEPTADO" });
      const cuerpo = { respuesta: "ACEPTADO" as const, hora_rta: "2026-11-10T18:44:10Z" };
  
      await responderSolicitud(340, cuerpo, opciones);
  
      const { url, init } = primeraLlamada(fetchSimulado);
      expect(url.pathname).toBe("/api/v1/solicitudes/340");
      expect(init.method).toBe("POST");
      expect(JSON.parse(init.body as string)).toEqual(cuerpo);
    });
  
    it.each([409, 410])("lanza ErrorApi con el status %i y el código del servidor", async (status) => {
      simularRespuesta(status, { codigo: "CODIGO_DE_PRUEBA", mensaje: "Mensaje de prueba" });
  
      await expect(
        responderSolicitud(340, { respuesta: "ACEPTADO", hora_rta: "2026-11-10T18:44:10Z" }, opciones)
      ).rejects.toMatchObject({ name: "ErrorApi", status, codigo: "CODIGO_DE_PRUEBA" });
    });
  });
  
  describe("errores comunes del cliente", () => {
    it.each([401, 403, 404, 409, 410, 422])(
      "convierte un %i en ErrorApi con {codigo, mensaje}",
      async (status) => {
        simularRespuesta(status, { codigo: "CODIGO_DE_PRUEBA", mensaje: "Mensaje de prueba" });
  
        await expect(obtenerEstado(15, opciones)).rejects.toMatchObject({
          name: "ErrorApi",
          status,
          codigo: "CODIGO_DE_PRUEBA",
          message: "Mensaje de prueba",
        });
      }
    );
  
    it("lanza ErrorApi con status 0 si falla la conexión", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("sin red")));
  
      await expect(obtenerEstado(15, opciones)).rejects.toMatchObject({
        name: "ErrorApi",
        status: 0,
      });
    });
  });
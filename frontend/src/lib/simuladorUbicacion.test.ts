import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  generarRecorrido,
  iniciarSimuladorUbicacion,
  type PuntoUbicacion,
} from "./simuladorUbicacion";

const ORIGEN: PuntoUbicacion = { latitud: -34.6037, longitud: -58.3816 };
const DESTINO: PuntoUbicacion = { latitud: -34.5937, longitud: -58.3716 };

function crearSimulador(opciones: Partial<Parameters<typeof iniciarSimuladorUbicacion>[0]> = {}) {
  const enviar = vi.fn(async (_punto: PuntoUbicacion) => {});
  const estaOcupado = vi.fn(() => true);
  const recorrido = opciones.recorrido ?? generarRecorrido(ORIGEN, DESTINO, 3);
  const simulador = iniciarSimuladorUbicacion({
    recorrido,
    enviar,
    estaOcupado,
    intervaloMs: 5000,
    ...opciones,
  });
  return { enviar, estaOcupado, recorrido, simulador };
}

describe("generarRecorrido", () => {
  it("genera puntos equiespaciados entre el origen y el destino, con ambos extremos", () => {
    const puntos = generarRecorrido(ORIGEN, DESTINO, 5);

    expect(puntos).toHaveLength(5);
    expect(puntos[0]).toEqual(ORIGEN);
    expect(puntos[1]).toEqual({ latitud: -34.6012, longitud: -58.3791 });
    expect(puntos[2]).toEqual({ latitud: -34.5987, longitud: -58.3766 });
    expect(puntos[3]).toEqual({ latitud: -34.5962, longitud: -58.3741 });
    expect(puntos[4]).toEqual(DESTINO);
  });

  it("cada punto lleva latitud y longitud juntas y en rango", () => {
    const puntos = generarRecorrido(ORIGEN, DESTINO, 8);

    for (const punto of puntos) {
      expect(typeof punto.latitud).toBe("number");
      expect(typeof punto.longitud).toBe("number");
      expect(punto.latitud).toBeGreaterThanOrEqual(-90);
      expect(punto.latitud).toBeLessThanOrEqual(90);
      expect(punto.longitud).toBeGreaterThanOrEqual(-180);
      expect(punto.longitud).toBeLessThanOrEqual(180);
    }
  });

  it.each([0, 1, 2.5, Number.NaN])(
    "rechaza una cantidad de puntos inválida (%s)",
    (cantidad) => {
      expect(() => generarRecorrido(ORIGEN, DESTINO, cantidad)).toThrow(RangeError);
    }
  );
});

describe("iniciarSimuladorUbicacion", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("envía un punto cada N segundos mientras el conductor está OCUPADO", async () => {
    const { enviar, recorrido, simulador } = crearSimulador();

    await vi.advanceTimersByTimeAsync(0);
    expect(enviar).toHaveBeenCalledTimes(1);
    expect(enviar).toHaveBeenLastCalledWith(recorrido[0]);

    await vi.advanceTimersByTimeAsync(5000);
    expect(enviar).toHaveBeenCalledTimes(2);
    expect(enviar).toHaveBeenLastCalledWith(recorrido[1]);

    await vi.advanceTimersByTimeAsync(5000);
    expect(enviar).toHaveBeenCalledTimes(3);
    expect(enviar).toHaveBeenLastCalledWith(recorrido[2]);

    for (const [punto] of enviar.mock.calls) {
      expect(typeof punto.latitud).toBe("number");
      expect(typeof punto.longitud).toBe("number");
    }

    simulador.detener();
  });

  it("usa cinco segundos entre envíos por defecto", async () => {
    const enviar = vi.fn(async (_punto: PuntoUbicacion) => {});
    const simulador = iniciarSimuladorUbicacion({
      recorrido: generarRecorrido(ORIGEN, DESTINO, 2),
      enviar,
      estaOcupado: () => true,
    });

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(4999);
    expect(enviar).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1);
    expect(enviar).toHaveBeenCalledTimes(2);

    simulador.detener();
  });

  it("se detiene al terminar el recorrido", async () => {
    const { enviar } = crearSimulador();

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(60_000);

    expect(enviar).toHaveBeenCalledTimes(3);
  });

  it("no envía puntos si el conductor no está OCUPADO", async () => {
    const { enviar } = crearSimulador({ estaOcupado: () => false });

    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(20_000);

    expect(enviar).not.toHaveBeenCalled();
  });

  it("deja de enviar cuando el conductor deja de estar OCUPADO", async () => {
    let ocupado = true;
    const { enviar } = crearSimulador({
      recorrido: generarRecorrido(ORIGEN, DESTINO, 10),
      estaOcupado: () => ocupado,
    });

    await vi.advanceTimersByTimeAsync(0);
    expect(enviar).toHaveBeenCalledTimes(1);

    ocupado = false;
    await vi.advanceTimersByTimeAsync(20_000);

    expect(enviar).toHaveBeenCalledTimes(1);
  });

  it("detener corta la transmisión", async () => {
    const { enviar, simulador } = crearSimulador({
      recorrido: generarRecorrido(ORIGEN, DESTINO, 10),
    });

    await vi.advanceTimersByTimeAsync(0);
    expect(enviar).toHaveBeenCalledTimes(1);

    simulador.detener();
    await vi.advanceTimersByTimeAsync(60_000);

    expect(enviar).toHaveBeenCalledTimes(1);
  });

  it("informa un error de envío y continúa con el siguiente punto", async () => {
    const error = new Error("sin red");
    const enviar = vi
      .fn(async (_punto: PuntoUbicacion) => {})
      .mockRejectedValueOnce(error)
      .mockResolvedValue(undefined);
    const alError = vi.fn();
    const simulador = iniciarSimuladorUbicacion({
      recorrido: generarRecorrido(ORIGEN, DESTINO, 3),
      enviar,
      estaOcupado: () => true,
      intervaloMs: 5000,
      alError,
    });

    await vi.advanceTimersByTimeAsync(0);
    expect(alError).toHaveBeenCalledWith(error);
    expect(enviar).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(5000);
    expect(enviar).toHaveBeenCalledTimes(2);

    simulador.detener();
  });
});

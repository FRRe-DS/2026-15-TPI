import { describe, it, expect } from "vitest";
import { MOCK_CONDUCTORES } from "./conductores.mock";
import type { EstadoOperativo } from "../lib/tipos";

const ESTADOS_OPERATIVOS: EstadoOperativo[] = [
  "DESCONECTADO",
  "CONECTADO",
  "DISPONIBLE",
  "OCUPADO",
];

describe("MOCK_CONDUCTORES", () => {
  it("incluye conductores con habilitación APROBADA, PENDIENTE y RECHAZADA", () => {
    const habilitaciones = MOCK_CONDUCTORES.map((c) => c.habilitacion);

    expect(habilitaciones).toEqual(
      expect.arrayContaining(["APROBADA", "PENDIENTE", "RECHAZADA"])
    );
  });

  it("incluye conductores con y sin ubicación", () => {
    const conUbicacion = MOCK_CONDUCTORES.filter(
      (c) => c.latitud != null && c.longitud != null
    );
    const sinUbicacion = MOCK_CONDUCTORES.filter(
      (c) => c.latitud == null && c.longitud == null
    );

    expect(conUbicacion.length).toBeGreaterThan(0);
    expect(sinUbicacion.length).toBeGreaterThan(0);
  });

  it("informa latitud y longitud siempre juntas", () => {
    MOCK_CONDUCTORES.forEach((c) => {
      expect(c.latitud == null).toBe(c.longitud == null);
    });
  });

  it("cada conductor tiene un estado operativo válido del contrato", () => {
    MOCK_CONDUCTORES.forEach((c) => {
      expect(ESTADOS_OPERATIVOS).toContain(c.estado);
    });
  });

  it("cada conductor tiene un id único", () => {
    const ids = MOCK_CONDUCTORES.map((c) => c.id);

    expect(new Set(ids).size).toBe(ids.length);
  });

  it("cada DNI cumple el formato del contrato (7 u 8 dígitos)", () => {
    MOCK_CONDUCTORES.forEach((c) => {
      expect(c.dni).toMatch(/^[0-9]{7,8}$/);
    });
  });
});
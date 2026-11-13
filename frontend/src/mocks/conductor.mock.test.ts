import { describe, it, expect } from "vitest";
import {
  MOCK_ESTADOS_CONDUCTOR,
  MOCK_SOLICITUDES,
  MOCK_UBICACION,
  MOCK_UBICACION_DESCONOCIDA,
} from "./conductor.mock";
import type { EstadoOperativo, EstadoSolicitud } from "../lib/tipos";

const ESTADOS_OPERATIVOS: EstadoOperativo[] = [
  "DESCONECTADO",
  "CONECTADO",
  "DISPONIBLE",
  "OCUPADO",
];

const ESTADOS_SOLICITUD: EstadoSolicitud[] = [
  "PENDIENTE",
  "ACEPTADO",
  "RECHAZADO",
  "VENCIDA",
];

describe("MOCK_ESTADOS_CONDUCTOR", () => {
  it.each(ESTADOS_OPERATIVOS)("incluye el estado %s", (estado) => {
    expect(MOCK_ESTADOS_CONDUCTOR[estado].estado).toBe(estado);
  });

  it("DISPONIBLE y OCUPADO tienen vehículo activo, como exige el contrato", () => {
    expect(MOCK_ESTADOS_CONDUCTOR.DISPONIBLE.id_vehiculo_activo != null).toBe(true);
    expect(MOCK_ESTADOS_CONDUCTOR.OCUPADO.id_vehiculo_activo != null).toBe(true);
  });
});

describe("MOCK_SOLICITUDES", () => {
  it.each(ESTADOS_SOLICITUD)("incluye una solicitud en estado %s", (estado) => {
    expect(MOCK_SOLICITUDES.some((s) => s.estado === estado)).toBe(true);
  });

  it("cada solicitud tiene un id único y una fecha de vencimiento", () => {
    const ids = MOCK_SOLICITUDES.map((s) => s.id);

    expect(new Set(ids).size).toBe(ids.length);
    MOCK_SOLICITUDES.forEach((s) => {
      expect(s.vence_en).toBeTruthy();
    });
  });

  it("las ACEPTADO y RECHAZADO traen respuesta y hora_rta coherentes", () => {
    const respondidas = MOCK_SOLICITUDES.filter(
      (s) => s.estado === "ACEPTADO" || s.estado === "RECHAZADO"
    );

    expect(respondidas.length).toBeGreaterThan(0);
    respondidas.forEach((s) => {
      expect(s.respuesta).toBe(s.estado);
      expect(s.hora_rta).toBeTruthy();
    });
  });

  it("las PENDIENTE todavía no tienen respuesta", () => {
    MOCK_SOLICITUDES.filter((s) => s.estado === "PENDIENTE").forEach((s) => {
      expect(s.respuesta ?? null).toBeNull();
    });
  });
});

describe("ubicación simulada", () => {
  it("MOCK_UBICACION informa latitud, longitud y fecha dentro de rango", () => {
    expect(MOCK_UBICACION.latitud).not.toBeNull();
    expect(MOCK_UBICACION.longitud).not.toBeNull();
    expect(MOCK_UBICACION.fecha_act_ubic).not.toBeNull();
    expect(Math.abs(MOCK_UBICACION.latitud as number)).toBeLessThanOrEqual(90);
    expect(Math.abs(MOCK_UBICACION.longitud as number)).toBeLessThanOrEqual(180);
  });

  it("MOCK_UBICACION_DESCONOCIDA trae los tres campos en null", () => {
    expect(MOCK_UBICACION_DESCONOCIDA.latitud).toBeNull();
    expect(MOCK_UBICACION_DESCONOCIDA.longitud).toBeNull();
    expect(MOCK_UBICACION_DESCONOCIDA.fecha_act_ubic).toBeNull();
  });
});
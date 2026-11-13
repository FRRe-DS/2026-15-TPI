import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { actualizarEstado, listarSolicitudes } from "../../lib/api";
import { NOMBRE_COOKIE_SESION, leerSesion } from "../../lib/sesion";
import {
  MOCK_ESTADOS_CONDUCTOR,
  MOCK_SOLICITUDES,
} from "../../mocks/conductor.mock";
import { ViajeEnCurso, type ViajeDetalle } from "../../components/ViajeEnCurso";
import type { EstadoConductorRequest } from "../../lib/tipos";

export const dynamic = "force-dynamic";

function usaMocks(): boolean {
  return process.env.USE_MOCK === "true";
}

async function finalizarViajeMock(
  _cambios?: EstadoConductorRequest,
): Promise<void> {
  MOCK_ESTADOS_CONDUCTOR.DISPONIBLE = {
    ...MOCK_ESTADOS_CONDUCTOR.DISPONIBLE,
    actualizado: new Date().toISOString(),
  };
}

async function finalizarViajeAction(
  cambios?: EstadoConductorRequest,
): Promise<void> {
  "use server";

  if (usaMocks()) {
    return finalizarViajeMock(cambios);
  }

  const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;
  const sesion = leerSesion(token);

  if (!token || !sesion) {
    redirect("/login");
  }

  await actualizarEstado(
    sesion.idConductor,
    { estado: "DISPONIBLE", ...cambios },
    { token },
  );
}

export default async function Page() {
  let viaje: ViajeDetalle | null = null;
  let error: string | null = null;

  if (usaMocks()) {
    const solicitudAceptada = MOCK_SOLICITUDES.find(
      (s) => s.estado === "ACEPTADO",
    );
    if (solicitudAceptada) {
      viaje = {
        ...solicitudAceptada,
        pasajero: "Laura Gómez",
        origen: "Av. San Martín 1540",
        destino: "Maipú 850",
        tarifa: "4.250",
      };
    }
  } else {
    const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;
    const sesion = leerSesion(token);

    if (!token || !sesion) {
      redirect("/login");
    }

    try {
      const solicitudes = await listarSolicitudes(sesion.idConductor, {
        token,
        estado: "ACEPTADO",
      });
      const activa = solicitudes.find((s) => s.estado === "ACEPTADO");
      if (activa) {
        viaje = activa;
      }
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: "bold" }}>
          Viaje en curso
        </h1>
        <p style={{ color: "#666" }}>
          Confirmá que subió el pasajero y finalizá el viaje
        </p>
      </header>
      <ViajeEnCurso
        viaje={viaje}
        error={error}
        finalizarViaje={finalizarViajeAction}
      />
    </main>
  );
}

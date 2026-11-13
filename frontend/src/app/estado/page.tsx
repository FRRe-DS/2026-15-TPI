import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  actualizarEstado,
  obtenerEstado,
} from "../../lib/api";
import { NOMBRE_COOKIE_SESION, leerSesion } from "../../lib/sesion";
import { MOCK_ESTADOS_CONDUCTOR } from "../../mocks/conductor.mock";
import { ControlEstado } from "../../components/ControlEstado";
import type { EstadoConductor, EstadoOperativoPedible } from "../../lib/tipos";

export const dynamic = "force-dynamic";

function usaMocks(): boolean {
  return process.env.USE_MOCK === "true";
}

let mockEstadoActual: EstadoConductor = {
  ...MOCK_ESTADOS_CONDUCTOR.CONECTADO,
};

async function cambiarEstadoMock(
  nuevoEstado: EstadoOperativoPedible
): Promise<EstadoConductor> {
  mockEstadoActual = {
    ...mockEstadoActual,
    estado: nuevoEstado,
    actualizado: new Date().toISOString(),
  };
  return mockEstadoActual;
}

async function cambiarEstado(
  nuevoEstado: EstadoOperativoPedible
): Promise<EstadoConductor> {
  "use server";

  if (usaMocks()) {
    return cambiarEstadoMock(nuevoEstado);
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(NOMBRE_COOKIE_SESION)?.value;
  const sesion = leerSesion(token);

  if (!token || !sesion) {
    redirect("/login");
  }

  return actualizarEstado(
    sesion.idConductor,
    { estado: nuevoEstado },
    { token }
  );
}

export default async function Page() {
  let estado: EstadoConductor | null = null;
  let error: string | null = null;

  if (usaMocks()) {
    estado = mockEstadoActual;
  } else {
    const cookieStore = await cookies();
    const token = cookieStore.get(NOMBRE_COOKIE_SESION)?.value;
    const sesion = leerSesion(token);

    if (!token || !sesion) {
      redirect("/login");
    }

    try {
      estado = await obtenerEstado(sesion.idConductor, { token });
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  return (
    <main
      style={{
        padding: "2rem",
        fontFamily: "system-ui, -apple-system, sans-serif",
        maxWidth: "600px",
        margin: "0 auto",
      }}
    >
      <header style={{ marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.75rem",
            fontWeight: "bold",
            margin: "0 0 0.5rem 0",
            color: "var(--color-text-primary, #0f172a)",
          }}
        >
          Estado del Conductor
        </h1>
        <p
          style={{
            color: "var(--color-text-secondary, #64748b)",
            margin: 0,
          }}
        >
          Controlá tu disponibilidad operativa para recibir viajes
        </p>
      </header>
      <ControlEstado
        estado={estado}
        error={error}
        cambiarEstado={cambiarEstado}
      />
    </main>
  );
}

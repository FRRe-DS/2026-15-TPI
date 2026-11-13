import React from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  ErrorApi,
  listarSolicitudes,
  responderSolicitud,
} from "../../lib/api";
import { NOMBRE_COOKIE_SESION, leerSesion } from "../../lib/sesion";
import { MOCK_SOLICITUDES } from "../../mocks/conductor.mock";
import { ListadoSolicitudes } from "../../components/ListadoSolicitudes";
import type { RespuestaSolicitudRequest, Solicitud } from "../../lib/tipos";

export const dynamic = "force-dynamic";

function usaMocks(): boolean {
  return process.env.USE_MOCK === "true";
}

async function responderSolicitudMock(
  idSolicitud: number,
  cuerpo: RespuestaSolicitudRequest,
): Promise<Solicitud> {
  const solicitud = MOCK_SOLICITUDES.find((item) => item.id === idSolicitud);
  if (!solicitud) {
    throw new ErrorApi(404, "No encontramos la solicitud.", "SOLICITUD_NO_ENCONTRADA");
  }
  if (solicitud.estado !== "PENDIENTE") {
    throw new ErrorApi(
      409,
      "La solicitud ya fue respondida.",
      "SOLICITUD_YA_RESPONDIDA",
    );
  }

  return {
    ...solicitud,
    estado: cuerpo.respuesta,
    respuesta: cuerpo.respuesta,
    hora_rta: cuerpo.hora_rta,
  };
}

async function responder(
  idSolicitud: number,
  cuerpo: RespuestaSolicitudRequest,
): Promise<Solicitud> {
  "use server";

  if (usaMocks()) {
    return responderSolicitudMock(idSolicitud, cuerpo);
  }

  const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;
  const sesion = leerSesion(token);

  if (!token || !sesion) {
    redirect("/login");
  }

  return responderSolicitud(idSolicitud, cuerpo, { token });
}

export default async function Page() {
  let solicitudes: Solicitud[] = [];
  let error: string | null = null;

  if (usaMocks()) {
    solicitudes = MOCK_SOLICITUDES;
  } else {
    const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;
    const sesion = leerSesion(token);

    if (!token || !sesion) {
      redirect("/login");
    }

    try {
      solicitudes = await listarSolicitudes(sesion.idConductor, { token });
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : String(err);
    }
  }

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: "bold" }}>
          Pedidos entrantes
        </h1>
        <p style={{ color: "#666" }}>
          Revisá tus solicitudes y aceptá o rechazá las que están pendientes
        </p>
      </header>
      <ListadoSolicitudes
        solicitudes={solicitudes}
        error={error}
        responder={responder}
      />
    </main>
  );
}

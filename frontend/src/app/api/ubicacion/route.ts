import { NextResponse } from "next/server";
import { ErrorApi, actualizarEstado } from "../../../lib/api";
import { NOMBRE_COOKIE_SESION, leerSesion } from "../../../lib/sesion";

function leerTokenDeCookie(cabecera: string | null): string | null {
  if (!cabecera) return null;

  for (const parte of cabecera.split(";")) {
    const separador = parte.indexOf("=");
    if (separador === -1) continue;

    const nombre = parte.slice(0, separador).trim();
    if (nombre !== NOMBRE_COOKIE_SESION) continue;

    return decodeURIComponent(parte.slice(separador + 1).trim());
  }

  return null;
}

function esCoordenada(valor: unknown, minimo: number, maximo: number): valor is number {
  return (
    typeof valor === "number" &&
    Number.isFinite(valor) &&
    valor >= minimo &&
    valor <= maximo
  );
}

export async function POST(request: Request) {
  let cuerpo: unknown;
  try {
    cuerpo = await request.json();
  } catch {
    cuerpo = null;
  }

  const { latitud, longitud } = (cuerpo ?? {}) as {
    latitud?: unknown;
    longitud?: unknown;
  };

  if (!esCoordenada(latitud, -90, 90) || !esCoordenada(longitud, -180, 180)) {
    return NextResponse.json(
      {
        codigo: "SOLICITUD_INVALIDA",
        mensaje: "Latitud y longitud son obligatorias y deben estar en rango.",
      },
      { status: 400 }
    );
  }

  const token = leerTokenDeCookie(request.headers.get("cookie"));
  const sesion = leerSesion(token);
  if (!token || !sesion) {
    return NextResponse.json(
      { codigo: "SIN_SESION", mensaje: "No hay una sesión de conductor activa." },
      { status: 401 }
    );
  }

  try {
    await actualizarEstado(sesion.idConductor, { latitud, longitud }, { token });
    return NextResponse.json({ enviada: true, latitud, longitud });
  } catch (error: unknown) {
    if (error instanceof ErrorApi) {
      return NextResponse.json(
        {
          codigo: error.codigo ?? "ERROR_API",
          mensaje: error.message,
        },
        { status: error.status >= 400 && error.status <= 599 ? error.status : 502 }
      );
    }

    return NextResponse.json(
      { codigo: "ERROR_INTERNO", mensaje: "No se pudo enviar la ubicación." },
      { status: 500 }
    );
  }
}

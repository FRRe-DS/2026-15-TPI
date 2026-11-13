import { NextResponse } from "next/server";
import {
  NOMBRE_COOKIE_SESION,
  iniciarSesion,
  opcionesCookieSesion,
} from "../../../lib/sesion";
import { ErrorAutenticacion } from "../../../lib/token";

const esProduccion = () => process.env.NODE_ENV === "production";

export async function POST(request: Request) {
  let cuerpo: unknown;
  try {
    cuerpo = await request.json();
  } catch {
    cuerpo = null;
  }

  const { usuario, password } = (cuerpo ?? {}) as { usuario?: unknown; password?: unknown };
  if (typeof usuario !== "string" || typeof password !== "string" || !usuario || !password) {
    return NextResponse.json(
      { codigo: "SOLICITUD_INVALIDA", mensaje: "Usuario y contraseña son obligatorios." },
      { status: 400 }
    );
  }

  try {
    const sesion = await iniciarSesion(usuario, password);
    const respuesta = NextResponse.json({ idConductor: sesion.idConductor });
    respuesta.cookies.set(
      NOMBRE_COOKIE_SESION,
      sesion.accessToken,
      opcionesCookieSesion(sesion.expiresIn, esProduccion())
    );
    return respuesta;
  } catch (error: unknown) {
    if (error instanceof ErrorAutenticacion) {
      return NextResponse.json(
        { codigo: "CREDENCIALES_INVALIDAS", mensaje: "No se pudo iniciar sesión. Revisá tus datos e intentá de nuevo." },
        { status: 401 }
      );
    }
    return NextResponse.json(
      { codigo: "ERROR_INTERNO", mensaje: "No se pudo iniciar sesión." },
      { status: 500 }
    );
  }
}

export async function DELETE() {
  const respuesta = NextResponse.json({ cerrada: true });
  respuesta.cookies.set(NOMBRE_COOKIE_SESION, "", opcionesCookieSesion(0, esProduccion()));
  return respuesta;
}
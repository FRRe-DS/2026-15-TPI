import { NextResponse, type NextRequest } from "next/server";
import { NOMBRE_COOKIE_SESION } from "./lib/sesion";
import { redireccionDeSesion } from "./lib/sesion-servidor";

export function proxy(request: NextRequest) {
  const destino = redireccionDeSesion(
    request.nextUrl.pathname,
    request.cookies.get(NOMBRE_COOKIE_SESION)?.value
  );

  if (destino) {
    return NextResponse.redirect(new URL(destino, request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/estado/:path*",
    "/solicitudes/:path*",
    "/viaje/:path*",
    "/ubicacion/:path*",
  ],
};

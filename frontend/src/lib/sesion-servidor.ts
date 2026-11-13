import { leerSesion } from "./sesion";

export const RUTA_LOGIN = "/login";

/** Rutas de la app del conductor que exigen una sesión vigente. */
export const RUTAS_CONDUCTOR_PROTEGIDAS = [
  "/estado",
  "/solicitudes",
  "/viaje",
  "/ubicacion",
] as const;

export function esRutaConductorProtegida(pathname: string): boolean {
  return RUTAS_CONDUCTOR_PROTEGIDAS.some(
    (ruta) => pathname === ruta || pathname.startsWith(`${ruta}/`)
  );
}

/**
 * Guard de sesión compartido por el proxy y las pantallas del conductor.
 * Devuelve la ruta a la que redirigir, o null si la petición puede continuar.
 */
export function redireccionDeSesion(
  pathname: string,
  token: string | null | undefined
): string | null {
  if (!esRutaConductorProtegida(pathname)) return null;
  return leerSesion(token) ? null : RUTA_LOGIN;
}

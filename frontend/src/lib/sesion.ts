export const NOMBRE_COOKIE_SESION = "sesion_conductor";

export interface SesionConductor {
  id_conductor: number;
  token: string;
}

export function leerSesion(
  token: string | null | undefined,
  ahoraEnSegundos = Math.floor(Date.now() / 1000)
): SesionConductor | null {
  if (!token) return null;

  const partes = token.split(".");
  if (partes.length !== 3) return null;

  try {
    const payload = JSON.parse(Buffer.from(partes[1], "base64url").toString("utf8")) as unknown;
    if (!payload || typeof payload !== "object") return null;

    const claims = payload as { id_conductor?: unknown; exp?: unknown };
    if (
      !Number.isSafeInteger(claims.id_conductor) ||
      typeof claims.id_conductor !== "number" ||
      claims.id_conductor < 1 ||
      typeof claims.exp !== "number" ||
      !Number.isFinite(claims.exp) ||
      claims.exp <= ahoraEnSegundos
    ) {
      return null;
    }

    return { id_conductor: claims.id_conductor, token };
  } catch {
    return null;
  }
}

export function crearCookieSesion(
  token: string,
  maxAge: number,
  secure = process.env.NODE_ENV !== "development"
): string {
  const atributos = [
    `${NOMBRE_COOKIE_SESION}=${encodeURIComponent(token)}`,
    "Path=/",
    "HttpOnly",
    "SameSite=Lax",
    `Max-Age=${Math.max(0, Math.floor(maxAge))}`,
  ];
  if (secure) atributos.push("Secure");
  return atributos.join("; ");
}

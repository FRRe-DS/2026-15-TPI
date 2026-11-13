import { ErrorAutenticacion } from "./token";

export const NOMBRE_COOKIE_SESION = "sesion_m3";

export interface ConfigKeycloak {
  keycloakUrl?: string;
  realm?: string;
  clientId?: string;
  clientSecret?: string;
}

export interface SesionIniciada {
  accessToken: string;
  expiresIn: number;
  idConductor: number;
}

function leerPayload(token: string): Record<string, unknown> | null {
  const partes = token.split(".");
  if (partes.length !== 3) return null;
  try {
    const json = Buffer.from(partes[1], "base64url").toString("utf8");
    const payload: unknown = JSON.parse(json);
    return payload !== null && typeof payload === "object"
      ? (payload as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

/** Lee el claim id_conductor sin validar la firma: la valida la API. */
export function leerIdConductor(token: string): number | null {
  const id = leerPayload(token)?.id_conductor;
  return typeof id === "number" && Number.isInteger(id) && id > 0 ? id : null;
}

export function leerSesion(
  token: string | null | undefined,
  ahora: number = Date.now()
): { idConductor: number } | null {
  if (!token) return null;
  const payload = leerPayload(token);
  const idConductor = leerIdConductor(token);
  const exp = payload?.exp;
  if (idConductor === null || typeof exp !== "number") return null;
  if (exp * 1000 <= ahora) return null;
  return { idConductor };
}

export function opcionesCookieSesion(maxAge: number, secure: boolean) {
  return {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge,
    secure,
  } as const;
}

export async function iniciarSesion(
  usuario: string,
  password: string,
  config: ConfigKeycloak = {}
): Promise<SesionIniciada> {
  const url = (config.keycloakUrl ?? process.env.KEYCLOAK_URL ?? "http://localhost:8081").replace(/\/$/, "");
  const realm = config.realm ?? process.env.KEYCLOAK_REALM ?? "m3";
  const endpoint = `${url}/realms/${realm}/protocol/openid-connect/token`;

  const cuerpo = new URLSearchParams({
    grant_type: "password",
    client_id: config.clientId ?? process.env.KEYCLOAK_CLIENT_ID ?? "",
    client_secret: config.clientSecret ?? process.env.KEYCLOAK_CLIENT_SECRET ?? "",
    username: usuario,
    password,
  });

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: cuerpo.toString(),
    });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : String(error);
    throw new ErrorAutenticacion(`Error al conectar con el servidor de autenticación: ${msg}`);
  }

  if (!response.ok) {
    let detalle = response.statusText;
    try {
      const datos = await response.json();
      detalle = datos.error_description || datos.error || detalle;
    } catch {
      // se usa el texto de estado
    }
    throw new ErrorAutenticacion(`Error en autenticación (${response.status}): ${detalle}`);
  }

  const datos = await response.json();
  if (!datos.access_token) {
    throw new ErrorAutenticacion("La respuesta de autenticación no contiene access_token");
  }

  const idConductor = leerIdConductor(datos.access_token);
  if (idConductor === null) {
    throw new ErrorAutenticacion("La cuenta no corresponde a un conductor");
  }

  const expiresIn = typeof datos.expires_in === "number" ? datos.expires_in : 60;
  return { accessToken: datos.access_token, expiresIn, idConductor };
}
export class ErrorAutenticacion extends Error {
  constructor(mensaje: string) {
    super(mensaje);
    this.name = "ErrorAutenticacion";
  }
}

interface TokenCache {
  accessToken: string;
  expiresAt: number;
}

let cache: TokenCache | null = null;

export function limpiarCacheToken(): void {
  cache = null;
}

export interface ObtenerTokenOpciones {
  keycloakUrl?: string;
  realm?: string;
  clientId?: string;
  clientSecret?: string;
  username?: string;
  password?: string;
}

export async function obtenerToken(opciones?: ObtenerTokenOpciones): Promise<string> {
  const now = Date.now();
  if (cache && now < cache.expiresAt) {
    return cache.accessToken;
  }

  const rawUrl = opciones?.keycloakUrl ?? process.env.KEYCLOAK_URL ?? "http://localhost:8081";
  const keycloakUrl = rawUrl.replace(/\/$/, "");
  const realm = opciones?.realm ?? process.env.KEYCLOAK_REALM ?? "m3";
  const clientId = opciones?.clientId ?? process.env.KEYCLOAK_CLIENT_ID ?? "";
  const clientSecret = opciones?.clientSecret ?? process.env.KEYCLOAK_CLIENT_SECRET ?? "";
  const username = opciones?.username ?? process.env.TEST_USER ?? "";
  const password = opciones?.password ?? process.env.TEST_PASSWORD ?? "";

  const endpoint = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`;

  const body = new URLSearchParams({
    grant_type: "password",
    client_id: clientId,
    client_secret: clientSecret,
    username,
    password,
  });

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
    });
  } catch (error: unknown) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    throw new ErrorAutenticacion(`Error al conectar con el servidor de autenticación: ${errorMsg}`);
  }

  if (!response.ok) {
    let detalle = "";
    try {
      const errorData = await response.json();
      detalle = errorData.error_description || errorData.error || response.statusText;
    } catch {
      detalle = response.statusText;
    }
    throw new ErrorAutenticacion(`Error en autenticación (${response.status}): ${detalle}`);
  }

  const data = await response.json();
  if (!data.access_token) {
    throw new ErrorAutenticacion("La respuesta de autenticación no contiene access_token");
  }

  const expiresInSeconds = typeof data.expires_in === "number" ? data.expires_in : 60;
  // Margen de seguridad para expiración
  const bufferMs = Math.min(2000, (expiresInSeconds * 1000) / 4);

  cache = {
    accessToken: data.access_token,
    expiresAt: now + expiresInSeconds * 1000 - bufferMs,
  };

  return data.access_token;
}

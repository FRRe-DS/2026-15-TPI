import { crearCookieSesion, leerSesion, NOMBRE_COOKIE_SESION } from "@/lib/sesion";

function respuestaJson(body: object, status = 200, headers?: HeadersInit): Response {
  const responseHeaders = new Headers(headers);
  responseHeaders.set("Cache-Control", "no-store");
  return Response.json(body, { status, headers: responseHeaders });
}

function leerCookieSesion(cookieHeader: string | null): string | null {
  if (!cookieHeader) return null;

  const cookie = cookieHeader
    .split(";")
    .map((parte) => parte.trim())
    .find((parte) => parte.startsWith(`${NOMBRE_COOKIE_SESION}=`));

  return cookie ? cookie.slice(NOMBRE_COOKIE_SESION.length + 1) : null;
}

function cookieSegura(): boolean {
  return process.env.NODE_ENV !== "development";
}

function redirigirLogin(request: Request, error: string): Response {
  return new Response(null, {
    status: 303,
    headers: {
      Location: new URL(`/login?error=${error}`, request.url).toString(),
      "Cache-Control": "no-store",
    },
  });
}

export async function GET(request: Request): Promise<Response> {
  const token = leerCookieSesion(request.headers.get("cookie"));
  const sesion = leerSesion(token);

  if (!sesion) return respuestaJson({ error: "No hay una sesión activa" }, 401);
  return respuestaJson({ id_conductor: sesion.id_conductor });
}

export async function POST(request: Request): Promise<Response> {
  const tipoContenido = request.headers.get("content-type") ?? "";
  const esFormulario = tipoContenido.includes("application/x-www-form-urlencoded") ||
    tipoContenido.includes("multipart/form-data");
  let credenciales: unknown;

  try {
    if (esFormulario) {
      const datos = await request.formData();
      credenciales = { username: datos.get("usuario"), password: datos.get("contrasena") };
    } else {
      credenciales = await request.json();
    }
  } catch {
    return esFormulario
      ? redirigirLogin(request, "solicitud")
      : respuestaJson({ error: "Solicitud inválida" }, 400);
  }

  if (!credenciales || typeof credenciales !== "object") {
    return esFormulario
      ? redirigirLogin(request, "solicitud")
      : respuestaJson({ error: "Solicitud inválida" }, 400);
  }

  const { username, password } = credenciales as { username?: unknown; password?: unknown };
  if (
    typeof username !== "string" ||
    username.trim() === "" ||
    typeof password !== "string" ||
    password === ""
  ) {
    return esFormulario
      ? redirigirLogin(request, "solicitud")
      : respuestaJson({ error: "Solicitud inválida" }, 400);
  }

  const keycloakUrl = (process.env.KEYCLOAK_URL || "http://localhost:8081").replace(/\/$/, "");
  const realm = process.env.KEYCLOAK_REALM || "m3";
  const clientId = process.env.KEYCLOAK_CLIENT_ID || "m3-api";
  const clientSecret = process.env.KEYCLOAK_CLIENT_SECRET;
  if (!clientSecret) {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "No se pudo iniciar sesión" }, 500);
  }

  const body = new URLSearchParams({
    grant_type: "password",
    client_id: clientId,
    client_secret: clientSecret,
    username,
    password,
  });

  let response: Response;
  try {
    response = await fetch(
      `${keycloakUrl}/realms/${realm}/protocol/openid-connect/token`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: body.toString(),
        cache: "no-store",
      }
    );
  } catch {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "No se pudo conectar con el servidor de autenticación" }, 502);
  }

  if (!response.ok) {
    if (response.status === 400 || response.status === 401) {
      return esFormulario
        ? redirigirLogin(request, "credenciales")
        : respuestaJson({ error: "Usuario o contraseña inválidos" }, 401);
    }
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "No se pudo iniciar sesión" }, 502);
  }

  let tokenData: unknown;
  try {
    tokenData = await response.json();
  } catch {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "Respuesta inválida del servidor de autenticación" }, 502);
  }

  if (!tokenData || typeof tokenData !== "object") {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "Respuesta inválida del servidor de autenticación" }, 502);
  }

  const { access_token: accessToken, expires_in: expiresIn } = tokenData as {
    access_token?: unknown;
    expires_in?: unknown;
  };
  if (
    typeof accessToken !== "string" ||
    typeof expiresIn !== "number" ||
    !Number.isFinite(expiresIn) ||
    expiresIn < 1
  ) {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "Respuesta inválida del servidor de autenticación" }, 502);
  }

  const sesion = leerSesion(accessToken);
  if (!sesion) {
    return esFormulario
      ? redirigirLogin(request, "servidor")
      : respuestaJson({ error: "Respuesta inválida del servidor de autenticación" }, 502);
  }

  const headers = { "Set-Cookie": crearCookieSesion(accessToken, expiresIn, cookieSegura()) };
  if (esFormulario) {
    return new Response(null, {
      status: 303,
      headers: {
        Location: new URL("/estado", request.url).toString(),
        "Cache-Control": "no-store",
        ...headers,
      },
    });
  }
  return respuestaJson({ id_conductor: sesion.id_conductor }, 200, headers);
}

export async function DELETE(): Promise<Response> {
  const cookie = `${NOMBRE_COOKIE_SESION}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${
    cookieSegura() ? "; Secure" : ""
  }`;
  return new Response(null, {
    status: 204,
    headers: {
      "Cache-Control": "no-store",
      "Set-Cookie": cookie,
    },
  });
}

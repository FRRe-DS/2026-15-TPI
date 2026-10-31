/**
 * Fixtures de API para las pruebas E2E.
 *
 * A diferencia de `backend/tests/contrato/`, acá no se firma ningún token:
 * se pide uno real a Keycloak con concesión de contraseña. Así se ejercita el
 * realm (`m3`), el cliente confidencial y los claims que la API valida.
 *
 * Credenciales: se leen del entorno del proceso o, si no están, de
 * `infra/.env`, para que `npm test` funcione sin exportar nada a mano.
 */
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

import { request, test as base, type APIRequestContext } from "@playwright/test";

function cargarEnvDeInfra(): Record<string, string> {
  const candidatos = [
    resolve(process.cwd(), "infra/.env"),
    resolve(process.cwd(), "../infra/.env"),
  ];
  const ruta = candidatos.find((candidato) => existsSync(candidato));
  if (!ruta) return {};

  const valores: Record<string, string> = {};
  for (const linea of readFileSync(ruta, "utf8").split(/\r?\n/)) {
    const limpia = linea.trim();
    if (!limpia || limpia.startsWith("#")) continue;
    const separador = limpia.indexOf("=");
    if (separador === -1) continue;
    valores[limpia.slice(0, separador).trim()] = limpia.slice(separador + 1).trim();
  }
  return valores;
}

const ENV_INFRA = cargarEnvDeInfra();

/** Lee una variable del proceso y, si falta, de `infra/.env`. */
export function leerEnv(nombre: string): string | undefined {
  return process.env[nombre] ?? ENV_INFRA[nombre];
}

export const API_URL =
  process.env.API_URL ?? `http://localhost:${leerEnv("API_PORT") ?? "8080"}/api/v1`;
export const KEYCLOAK_URL =
  leerEnv("KEYCLOAK_PUBLIC_URL") ?? process.env.KEYCLOAK_URL ?? "http://localhost:8081";
const KEYCLOAK_REALM = leerEnv("KEYCLOAK_REALM") ?? "m3";
const KEYCLOAK_CLIENT_ID = leerEnv("KEYCLOAK_M3_CLIENT_ID") ?? "m3-api";
const KEYCLOAK_CLIENT_SECRET =
  leerEnv("KEYCLOAK_M3_CLIENT_SECRET") ?? leerEnv("KEYCLOAK_CLIENT_SECRET") ?? "";

export type Usuario = "operador" | "conductor";

const CREDENCIALES: Record<Usuario, { username: string; password: string }> = {
  operador: {
    username: leerEnv("M3_OPERADOR_USERNAME") ?? "operador.m3",
    password: leerEnv("M3_OPERADOR_PASSWORD") ?? "",
  },
  conductor: {
    username: leerEnv("M3_CONDUCTOR_USERNAME") ?? "conductor.m3",
    password: leerEnv("M3_CONDUCTOR_PASSWORD") ?? "",
  },
};

const tokens = new Map<Usuario, string>();

/** Pide un access token real a Keycloak y lo cachea por usuario. */
export async function obtenerToken(usuario: Usuario = "operador"): Promise<string> {
  const cacheado = tokens.get(usuario);
  if (cacheado) return cacheado;

  const { username, password } = CREDENCIALES[usuario];
  if (!password) {
    throw new Error(
      `Falta la clave de "${usuario}". Completá infra/.env (M3_${usuario.toUpperCase()}_PASSWORD).`,
    );
  }

  const respuesta = await fetch(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "password",
        client_id: KEYCLOAK_CLIENT_ID,
        client_secret: KEYCLOAK_CLIENT_SECRET,
        username,
        password,
      }),
    },
  );

  if (!respuesta.ok) {
    const detalle = await respuesta.text();
    throw new Error(`Keycloak rechazó el token de ${usuario}: ${respuesta.status} ${detalle}`);
  }

  const cuerpo = (await respuesta.json()) as { access_token?: string };
  if (!cuerpo.access_token) {
    throw new Error(`Keycloak no devolvió access_token para ${usuario}.`);
  }

  tokens.set(usuario, cuerpo.access_token);
  return cuerpo.access_token;
}

/** Decodifica el payload de un JWT sin validar la firma (para asserciones). */
export function claimsDelToken(token: string): Record<string, unknown> {
  const payload = token.split(".")[1];
  if (!payload) throw new Error("El token no tiene payload.");
  return JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as Record<string, unknown>;
}

type Fixtures = {
  apiOperador: APIRequestContext;
  apiConductor: APIRequestContext;
};

/** Cliente HTTP autenticado con un token real de Keycloak. */
export const test = base.extend<Fixtures>({
  apiOperador: async ({}, use) => {
    const contexto = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { Authorization: `Bearer ${await obtenerToken("operador")}` },
    });
    await use(contexto);
    await contexto.dispose();
  },

  apiConductor: async ({}, use) => {
    const contexto = await request.newContext({
      baseURL: API_URL,
      extraHTTPHeaders: { Authorization: `Bearer ${await obtenerToken("conductor")}` },
    });
    await use(contexto);
    await contexto.dispose();
  },
});

export { expect } from "@playwright/test";

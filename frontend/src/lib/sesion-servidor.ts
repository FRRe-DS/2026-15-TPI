import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { leerSesion, NOMBRE_COOKIE_SESION } from "./sesion";

export async function requerirSesionConductor(): Promise<void> {
  if (process.env.NODE_ENV === "development" && process.env.USE_MOCK === "true") return;

  const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;
  if (!leerSesion(token)) redirect("/login");
}

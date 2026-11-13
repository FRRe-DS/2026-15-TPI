import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { FormularioLogin } from "../../components/FormularioLogin";
import { NOMBRE_COOKIE_SESION, leerSesion } from "../../lib/sesion";

export const dynamic = "force-dynamic";

export default async function Page() {
  const token = (await cookies()).get(NOMBRE_COOKIE_SESION)?.value;

  // Si ya hay una sesión vigente, el conductor no necesita volver a autenticarse.
  if (leerSesion(token)) redirect("/estado");

  return (
    <main
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "2rem",
        boxSizing: "border-box",
        backgroundColor: "var(--color-bg-canvas, #f8fafc)",
      }}
    >
      <FormularioLogin />
    </main>
  );
}

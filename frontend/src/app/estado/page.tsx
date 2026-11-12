import { EstadoScreen } from "../../components/conductor/ConductorDemo";
import { requerirSesionConductor } from "../../lib/sesion-servidor";

export default async function Page() {
  await requerirSesionConductor();
  return <EstadoScreen />;
}

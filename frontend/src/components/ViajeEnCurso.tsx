"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type {
  EstadoConductorRequest,
  EstadoOperativo,
  EstadoSolicitud,
  Solicitud,
} from "../lib/tipos";
import { EstadoCarga, EstadoError, EstadoVacio } from "./estados/estados";
import styles from "./ViajeEnCurso.module.css";

export interface ViajeInfo {
  id?: number | null;
  id_viaje?: number | null;
  id_solicitud?: number | null;
  id_conductor?: number;
  estado?: EstadoOperativo | EstadoSolicitud;
  pasajero?: string;
  origen?: string;
  destino?: string;
  tarifa?: string | number;
}

export type ViajeDetalle = ViajeInfo | Solicitud;

export type FinalizarViajeFn = (
  cambios?: EstadoConductorRequest,
) => Promise<unknown> | unknown;

export interface ViajeEnCursoProps {
  viaje?: ViajeDetalle | null;
  cargando?: boolean;
  error?: string | null;
  finalizarViaje?: FinalizarViajeFn;
  onFinalizado?: () => void;
}

export function ViajeEnCurso({
  viaje,
  cargando = false,
  error = null,
  finalizarViaje,
  onFinalizado,
}: ViajeEnCursoProps) {
  const router = useRouter();
  const [pasajeroSubio, setPasajeroSubio] = useState(false);
  const [finalizando, setFinalizando] = useState(false);
  const [errorFinalizar, setErrorFinalizar] = useState<string | null>(null);

  if (cargando) {
    return <EstadoCarga mensaje="Cargando viaje en curso..." />;
  }

  if (error) {
    return <EstadoError mensaje={error} />;
  }

  if (!viaje) {
    return <EstadoVacio mensaje="Sin viaje en curso" />;
  }

  const idViaje = viaje.id_viaje ?? viaje.id;
  const pasajero = ("pasajero" in viaje && viaje.pasajero) || "Pasajero asignado";
  const origen = ("origen" in viaje && viaje.origen) || "Origen asignado";
  const destino = ("destino" in viaje && viaje.destino) || "Destino asignado";
  const tarifa = "tarifa" in viaje && viaje.tarifa ? String(viaje.tarifa) : null;

  function handlePasajeroSubio() {
    setPasajeroSubio(true);
  }

  async function handleFinalizarViaje() {
    if (!pasajeroSubio || finalizando) return;
    setFinalizando(true);
    setErrorFinalizar(null);

    try {
      if (finalizarViaje) {
        await finalizarViaje({ estado: "DISPONIBLE" });
      }
      onFinalizado?.();
      router.push("/solicitudes");
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Error al finalizar el viaje. Intente nuevamente.";
      setErrorFinalizar(msg);
    } finally {
      setFinalizando(false);
    }
  }

  return (
    <div className={styles.contenedor}>
      <header className={styles.encabezado}>
        <div>
          <h2 className={styles.tripId}>Viaje #{idViaje}</h2>
          {tarifa && (
            <div className={styles.tarifa}>Tarifa pactada: $ {tarifa}</div>
          )}
        </div>
        <span className={styles.badgeOcupado}>OCUPADO</span>
      </header>

      <section className={styles.tarjetaDetalle}>
        <p className={styles.pasajeroTexto}>
          <strong>Pasajero:</strong> {pasajero}
        </p>
        <p className={styles.rutaTexto}>
          Origen: {origen} → Destino: {destino}
        </p>
      </section>

      <div className={styles.indicadorPaso} role="status">
        Paso actual:{" "}
        {pasajeroSubio
          ? "Viaje hacia el destino final"
          : "Pasajero a bordo del vehículo"}
      </div>

      {/* Stepper de progresión */}
      <ol className={styles.stepper} aria-label="Progreso del viaje">
        <li
          className={styles.pasoItem}
          aria-label="Paso 1: Conductor en camino al punto de partida"
        >
          <span className={styles.iconoDone}>✓</span>
          <span className={styles.textoDone}>
            1. Conductor en camino al punto de partida
          </span>
        </li>
        <li
          className={styles.pasoItem}
          aria-label="Paso 2: Pasajero a bordo del vehículo"
          aria-current={!pasajeroSubio ? "step" : undefined}
        >
          <span
            className={pasajeroSubio ? styles.iconoDone : styles.iconoActivo}
          >
            {pasajeroSubio ? "✓" : "2"}
          </span>
          <span
            className={pasajeroSubio ? styles.textoDone : styles.textoActivo}
          >
            2. Pasajero a bordo del vehículo
          </span>
        </li>
        <li
          className={styles.pasoItem}
          aria-label="Paso 3: Viaje hacia el destino final"
          aria-current={pasajeroSubio ? "step" : undefined}
        >
          <span
            className={
              pasajeroSubio ? styles.iconoActivo : styles.iconoPendiente
            }
          >
            3
          </span>
          <span
            className={
              pasajeroSubio ? styles.textoActivo : styles.textoPendiente
            }
          >
            3. Viaje hacia el destino final
          </span>
        </li>
      </ol>

      {errorFinalizar && (
        <div role="alert" className={styles.errorAlert}>
          {errorFinalizar}
        </div>
      )}

      {/* Acciones del viaje */}
      <div className={styles.acciones}>
        <button
          type="button"
          className={styles.btnSubio}
          onClick={handlePasajeroSubio}
          disabled={pasajeroSubio || finalizando}
          aria-label="Pasajero subió"
        >
          Pasajero subió{pasajeroSubio ? " ✓" : ""}
        </button>
        <button
          type="button"
          className={styles.btnFinalizar}
          onClick={handleFinalizarViaje}
          disabled={!pasajeroSubio || finalizando}
          aria-busy={finalizando}
          aria-label="Finalizar viaje"
        >
          {finalizando ? "Finalizando viaje..." : "Finalizar viaje"}
        </button>
      </div>

      <p className={styles.notaInfo}>
        Al finalizar el viaje, se solicita el estado DISPONIBLE y se retorna a
        las solicitudes.
      </p>
    </div>
  );
}

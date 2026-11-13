"use client";

import { useState } from "react";
import { ErrorApi } from "../lib/api";
import type {
  EstadoConductor,
  EstadoOperativo,
  EstadoOperativoPedible,
} from "../lib/tipos";
import { EstadoCarga, EstadoVacio } from "./estados/estados";
import styles from "./ControlEstado.module.css";

export type CambiarEstado = (
  nuevoEstado: EstadoOperativoPedible
) => Promise<EstadoConductor | void>;

export interface ControlEstadoProps {
  estado?: EstadoOperativo | EstadoConductor | null;
  estadoInicial?: EstadoOperativo | EstadoConductor | null;
  cargando?: boolean;
  error?: string | null;
  cambiarEstado?: CambiarEstado;
}

const ESTADOS_DISPONIBLES_A_PEDIR: EstadoOperativoPedible[] = [
  "DESCONECTADO",
  "CONECTADO",
  "DISPONIBLE",
];

interface InfoError {
  status?: number;
  codigo?: string;
  mensaje: string;
}

function normalizarError(err: unknown): InfoError {
  if (err instanceof ErrorApi) {
    return {
      status: err.status,
      codigo: err.codigo,
      mensaje: err.message,
    };
  }
  if (err instanceof Error) {
    return { mensaje: err.message };
  }
  if (typeof err === "string") {
    return { mensaje: err };
  }
  return { mensaje: "Ocurrió un error inesperado al actualizar el estado." };
}

function extraerEstado(
  val: EstadoOperativo | EstadoConductor | null | undefined | void
): EstadoOperativo | null {
  if (!val) return null;
  if (typeof val === "object" && "estado" in val) {
    return val.estado;
  }
  return val as EstadoOperativo;
}

export function ControlEstado({
  estado = null,
  estadoInicial = null,
  cargando = false,
  error = null,
  cambiarEstado,
}: ControlEstadoProps) {
  const estadoDeProp = extraerEstado(estado ?? estadoInicial);
  const [estadoLocal, setEstadoLocal] = useState<EstadoOperativo | null>(null);
  const [prevEstadoProp, setPrevEstadoProp] = useState(estadoDeProp);

  if (estadoDeProp !== prevEstadoProp) {
    setPrevEstadoProp(estadoDeProp);
    setEstadoLocal(null);
  }

  const estadoActual = estadoLocal ?? estadoDeProp;
  const [guardando, setGuardando] = useState(false);
  const [errorLocal, setErrorLocal] = useState<InfoError | null>(null);

  if (cargando) {
    return <EstadoCarga mensaje="Cargando estado del conductor..." />;
  }

  const errorVisible = errorLocal ?? (error ? normalizarError(error) : null);

  if (!estadoActual && !guardando) {
    if (errorVisible) {
      return (
        <div role="alert" className={styles.alertaError}>
          <p className={styles.errorTitulo}>
            {errorVisible.codigo && errorVisible.status
              ? `${errorVisible.codigo} (${errorVisible.status})`
              : errorVisible.codigo ||
                (errorVisible.status ? `Error ${errorVisible.status}` : "Error")}
          </p>
          <p className={styles.errorMensaje}>{errorVisible.mensaje}</p>
        </div>
      );
    }
    return <EstadoVacio mensaje="Sin información del estado del conductor" />;
  }

  async function handleCambiarEstado(nuevoEstado: EstadoOperativoPedible) {
    if (guardando || cargando) return;

    setGuardando(true);
    setErrorLocal(null);

    try {
      if (cambiarEstado) {
        const respuesta = await cambiarEstado(nuevoEstado);
        const proximo = extraerEstado(respuesta) ?? nuevoEstado;
        setEstadoLocal(proximo);
      } else {
        setEstadoLocal(nuevoEstado);
      }
    } catch (err: unknown) {
      setErrorLocal(normalizarError(err));
    } finally {
      setGuardando(false);
    }
  }

  const claseBadge = estadoActual
    ? styles[estadoActual.toLowerCase()] || ""
    : "";

  return (
    <div className={styles.tarjeta}>
      {errorVisible && (
        <div role="alert" className={styles.alertaError}>
          <p className={styles.errorTitulo}>
            {errorVisible.codigo && errorVisible.status
              ? `${errorVisible.codigo} (${errorVisible.status})`
              : errorVisible.codigo ||
                (errorVisible.status ? `Error ${errorVisible.status}` : "Error")}
          </p>
          <p className={styles.errorMensaje}>{errorVisible.mensaje}</p>
        </div>
      )}

      <div className={styles.seccionEstadoActual}>
        <span className={styles.etiquetaActual}>Estado Operativo Actual</span>
        <span
          className={`${styles.badge} ${claseBadge}`}
          data-testid="estado-actual"
        >
          {estadoActual ?? "DESCONOCIDO"}
        </span>
      </div>

      {guardando && (
        <div
          role="status"
          aria-live="polite"
          className={styles.indicadorGuardando}
        >
          Actualizando estado...
        </div>
      )}

      <div
        className={styles.grupoBotones}
        role="group"
        aria-label="Acciones de cambio de estado"
      >
        {ESTADOS_DISPONIBLES_A_PEDIR.map((opcion) => {
          const esActual = estadoActual === opcion;
          return (
            <button
              key={opcion}
              type="button"
              className={`${styles.botonEstado} ${
                esActual ? styles.botonActivo : ""
              } ${opcion === "DISPONIBLE" ? styles.botonDisponible : ""}`}
              onClick={() => handleCambiarEstado(opcion)}
              disabled={guardando || cargando}
              aria-pressed={esActual}
              aria-label={opcion}
            >
              <span className={styles.nombreOpcion}>{opcion}</span>
              {esActual && <span className={styles.marcaActual}> (Actual)</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

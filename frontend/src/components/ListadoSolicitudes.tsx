"use client";

import { useEffect, useState } from "react";
import { ErrorApi } from "../lib/api";
import type {
  EstadoSolicitud,
  RespuestaSolicitud,
  RespuestaSolicitudRequest,
  Solicitud,
} from "../lib/tipos";
import { EstadoCarga, EstadoError, EstadoVacio } from "./estados/estados";
import styles from "./ListadoSolicitudes.module.css";

export type ResponderSolicitud = (
  idSolicitud: number,
  cuerpo: RespuestaSolicitudRequest,
) => Promise<Solicitud>;

export interface ListadoSolicitudesProps {
  solicitudes?: Solicitud[];
  cargando?: boolean;
  error?: string | null;
  responder?: ResponderSolicitud;
}

const CLASE_ESTADO: Record<EstadoSolicitud, string> = {
  PENDIENTE: styles.pendiente,
  ACEPTADO: styles.aceptado,
  RECHAZADO: styles.rechazado,
  VENCIDA: styles.vencida,
};

function segundosRestantes(venceEn: string, ahora: number): number {
  const vencimiento = new Date(venceEn).getTime();
  if (Number.isNaN(vencimiento)) return 0;
  return Math.max(0, Math.ceil((vencimiento - ahora) / 1000));
}

function formatearRestante(segundos: number): string {
  if (segundos <= 0) return "Oferta vencida";

  if (segundos < 60) return `Vence en ${segundos} s`;

  const minutos = Math.floor(segundos / 60);
  const resto = segundos % 60;
  return resto === 0
    ? `Vence en ${minutos} min`
    : `Vence en ${minutos} min ${resto} s`;
}

function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorApi) {
    if (error.status === 410) {
      return "Oferta vencida: ya no se puede responder.";
    }
    if (error.status === 409) {
      return `Conflicto: ${error.message}`;
    }
    return error.message;
  }

  if (error instanceof Error) return error.message;
  return "No se pudo responder la solicitud.";
}

export function ListadoSolicitudes({
  solicitudes = [],
  cargando = false,
  error = null,
  responder,
}: ListadoSolicitudesProps) {
  const [ahora, setAhora] = useState(() => Date.now());
  const [respondiendo, setRespondiendo] = useState<number | null>(null);
  const [errores, setErrores] = useState<Record<number, string>>({});
  const [respuestas, setRespuestas] = useState<Record<number, Solicitud>>({});

  useEffect(() => {
    setAhora(Date.now());
    const intervalo = window.setInterval(() => setAhora(Date.now()), 1000);
    return () => window.clearInterval(intervalo);
  }, []);

  if (cargando) {
    return <EstadoCarga mensaje="Cargando solicitudes..." />;
  }

  if (error) {
    return (
      <EstadoError mensaje={`No se pudieron cargar las solicitudes: ${error}`} />
    );
  }

  if (solicitudes.length === 0) {
    return <EstadoVacio mensaje="No hay solicitudes" />;
  }

  async function responderSolicitud(
    idSolicitud: number,
    respuesta: RespuestaSolicitud,
  ) {
    if (!responder) return;

    const cuerpo: RespuestaSolicitudRequest = {
      respuesta,
      hora_rta: new Date().toISOString(),
    };

    setRespondiendo(idSolicitud);
    setErrores((anteriores) => {
      const siguientes = { ...anteriores };
      delete siguientes[idSolicitud];
      return siguientes;
    });

    try {
      const actualizada = await responder(idSolicitud, cuerpo);
      setRespuestas((anteriores) => ({
        ...anteriores,
        [idSolicitud]: actualizada,
      }));
    } catch (err: unknown) {
      setErrores((anteriores) => ({
        ...anteriores,
        [idSolicitud]: mensajeDeError(err),
      }));
    } finally {
      setRespondiendo(null);
    }
  }

  return (
    <ul className={styles.lista}>
      {solicitudes.map((solicitud) => {
        const actual = respuestas[solicitud.id] ?? solicitud;
        const pendiente = actual.estado === "PENDIENTE";
        const restantes = segundosRestantes(actual.vence_en, ahora);
        const vencida = pendiente && restantes <= 0;
        const respondiendoEsta = respondiendo === actual.id;

        return (
          <li
            key={actual.id}
            className={styles.solicitud}
            aria-label={`Solicitud ${actual.id}`}
          >
            <div className={styles.encabezado}>
              <h2 className={styles.titulo}>Solicitud #{actual.id}</h2>
              <span className={`${styles.estado} ${CLASE_ESTADO[actual.estado]}`}>
                {actual.estado}
              </span>
            </div>

            {actual.id_viaje != null && (
              <p className={styles.detalle}>Viaje #{actual.id_viaje}</p>
            )}

            {pendiente ? (
              <>
                <p
                  className={vencida ? styles.contadorVencido : styles.contador}
                  role="timer"
                >
                  {formatearRestante(restantes)}
                </p>
                <div className={styles.acciones}>
                  <button
                    type="button"
                    className={styles.aceptar}
                    aria-label={`Aceptar solicitud ${actual.id}`}
                    onClick={() => responderSolicitud(actual.id, "ACEPTADO")}
                    disabled={vencida || respondiendoEsta || !responder}
                  >
                    Aceptar
                  </button>
                  <button
                    type="button"
                    className={styles.rechazar}
                    aria-label={`Rechazar solicitud ${actual.id}`}
                    onClick={() => responderSolicitud(actual.id, "RECHAZADO")}
                    disabled={vencida || respondiendoEsta || !responder}
                  >
                    Rechazar
                  </button>
                </div>
              </>
            ) : (
              actual.hora_rta && (
                <p className={styles.detalle}>
                  Respondida:{" "}
                  {new Date(actual.hora_rta).toLocaleString("es-AR")}
                </p>
              )
            )}

            {errores[actual.id] && (
              <p className={styles.errorAccion} role="alert">
                {errores[actual.id]}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

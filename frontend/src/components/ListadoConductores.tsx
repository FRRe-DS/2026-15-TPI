import React from "react";
import { EstadoError, EstadoVacio } from "./estados/estados";
import type { ConductorConUbicacion, EstadoHabilitacion } from "../lib/tipos";
import styles from "./ListadoConductores.module.css";

export interface ListadoConductoresProps {
  conductores?: ConductorConUbicacion[];
  error?: string | null;
}

export function ListadoConductores({
  conductores,
  error,
}: ListadoConductoresProps) {
  if (error) {
    return <EstadoError mensaje={error} />;
  }

  if (!conductores || conductores.length === 0) {
    return <EstadoVacio mensaje="No hay conductores" />;
  }

  const badge: Record<EstadoHabilitacion, string> = {
    APROBADA: styles.aprobada,
    PENDIENTE: styles.pendiente,
    OBSERVADA: styles.observada,
    SUSPENDIDA: styles.rechazada,
    RECHAZADA: styles.rechazada,
  };

  return (
    <div className={styles.tablaScroll}>
      <table className={styles.tabla}>
        <caption className={styles.oculto}>Conductores registrados</caption>
        <thead>
          <tr>
            <th scope="col">Nombre</th>
            <th scope="col">Apellido</th>
            <th scope="col">DNI</th>
            <th scope="col">Habilitación</th>
          </tr>
        </thead>
        <tbody>
          {conductores.map((conductor) => (
            <tr key={conductor.id}>
              <td>{conductor.nombre}</td>
              <td>{conductor.apellido}</td>
              <td>{conductor.dni}</td>
              <td><span className={`${styles.badge} ${badge[conductor.habilitacion]}`}>{conductor.habilitacion}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

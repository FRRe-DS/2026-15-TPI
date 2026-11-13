import styles from "./estados.module.css";

interface EstadoProps {
  mensaje: string;
}

export function EstadoCarga({ mensaje }: EstadoProps) {
  return (
    <p className={styles.carga} role="status" aria-live="polite">
      {mensaje}
    </p>
  );
}

export function EstadoError({ mensaje }: EstadoProps) {
  return (
    <p className={styles.error} role="alert">
      {mensaje}
    </p>
  );
}

export function EstadoVacio({ mensaje }: EstadoProps) {
  return <p className={styles.vacio}>{mensaje}</p>;
}

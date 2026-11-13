import type { UbicacionConductor } from "../lib/tipos";
import styles from "./UbicacionActual.module.css";

interface UbicacionActualProps {
  ubicacion: UbicacionConductor | null;
}

function formatearFecha(fechaIso: string | null): string {
  if (!fechaIso) return "desconocida";

  const fecha = new Date(fechaIso);
  if (Number.isNaN(fecha.getTime())) return "desconocida";

  const dosDigitos = (valor: number) => String(valor).padStart(2, "0");
  const dia = dosDigitos(fecha.getUTCDate());
  const mes = dosDigitos(fecha.getUTCMonth() + 1);
  const anio = fecha.getUTCFullYear();
  const horas = dosDigitos(fecha.getUTCHours());
  const minutos = dosDigitos(fecha.getUTCMinutes());
  const segundos = dosDigitos(fecha.getUTCSeconds());

  return `${dia}/${mes}/${anio} ${horas}:${minutos}:${segundos} UTC`;
}

export function UbicacionActual({ ubicacion }: UbicacionActualProps) {
  const desconocida =
    !ubicacion || ubicacion.latitud === null || ubicacion.longitud === null;

  return (
    <section className={styles.tarjeta} aria-labelledby="ubicacion-actual-titulo">
      <h2 className={styles.titulo} id="ubicacion-actual-titulo">
        Ubicación actual
      </h2>

      {desconocida ? (
        <p className={styles.desconocida}>Ubicación desconocida</p>
      ) : (
        <>
          <dl className={styles.datos}>
            <div className={styles.dato}>
              <dt className={styles.etiqueta}>Latitud</dt>
              <dd className={styles.valor}>{ubicacion.latitud}</dd>
            </div>
            <div className={styles.dato}>
              <dt className={styles.etiqueta}>Longitud</dt>
              <dd className={styles.valor}>{ubicacion.longitud}</dd>
            </div>
            <div className={styles.dato}>
              <dt className={styles.etiqueta}>Última actualización</dt>
              <dd className={styles.fecha}>
                {formatearFecha(ubicacion.fecha_act_ubic)}
              </dd>
            </div>
          </dl>
          <p className={styles.nota}>
            Coordenada informada por el recorrido simulado. Sin mapa.
          </p>
        </>
      )}
    </section>
  );
}

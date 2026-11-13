export interface PuntoUbicacion {
  latitud: number;
  longitud: number;
}

export interface OpcionesSimuladorUbicacion {
  recorrido: readonly PuntoUbicacion[];
  enviar: (punto: PuntoUbicacion) => void | Promise<void>;
  estaOcupado: () => boolean;
  intervaloMs?: number;
  alError?: (error: unknown) => void;
}

export interface SimuladorUbicacion {
  detener: () => void;
}

const INTERVALO_POR_DEFECTO_MS = 5000;
const DECIMALES = 6;

function redondear(valor: number): number {
  const factor = 10 ** DECIMALES;
  const redondeado = Math.round(valor * factor) / factor;
  return Object.is(redondeado, -0) ? 0 : redondeado;
}

/**
 * Genera `cantidad` puntos equiespaciados entre el origen y el destino,
 * incluyendo ambos extremos.
 */
export function generarRecorrido(
  origen: PuntoUbicacion,
  destino: PuntoUbicacion,
  cantidad: number
): PuntoUbicacion[] {
  if (!Number.isInteger(cantidad) || cantidad < 2) {
    throw new RangeError("El recorrido necesita al menos dos puntos.");
  }

  const tramos = cantidad - 1;
  const puntos: PuntoUbicacion[] = [];

  for (let indice = 0; indice < cantidad; indice += 1) {
    const avance = indice / tramos;
    puntos.push({
      latitud: redondear(origen.latitud + (destino.latitud - origen.latitud) * avance),
      longitud: redondear(
        origen.longitud + (destino.longitud - origen.longitud) * avance
      ),
    });
  }

  return puntos;
}

/**
 * Recorre los puntos enviando cada uno con latitud y longitud juntas.
 * Solo transmite mientras `estaOcupado()` sea verdadero y se detiene al
 * terminar el recorrido o al llamar a `detener()`.
 */
export function iniciarSimuladorUbicacion({
  recorrido,
  enviar,
  estaOcupado,
  intervaloMs = INTERVALO_POR_DEFECTO_MS,
  alError,
}: OpcionesSimuladorUbicacion): SimuladorUbicacion {
  let indice = 0;
  let detenido = false;
  let temporizador: ReturnType<typeof setTimeout> | null = null;

  const detener = () => {
    detenido = true;
    if (temporizador !== null) {
      clearTimeout(temporizador);
      temporizador = null;
    }
  };

  const programarSiguiente = () => {
    if (detenido) return;
    if (!estaOcupado() || indice >= recorrido.length) {
      detener();
      return;
    }
    temporizador = setTimeout(() => {
      void enviarSiguiente();
    }, intervaloMs);
  };

  const enviarSiguiente = async () => {
    if (detenido) return;
    if (!estaOcupado() || indice >= recorrido.length) {
      detener();
      return;
    }

    const punto = recorrido[indice];
    indice += 1;

    try {
      await enviar(punto);
    } catch (error: unknown) {
      alError?.(error);
    }

    programarSiguiente();
  };

  void enviarSiguiente();

  return { detener };
}

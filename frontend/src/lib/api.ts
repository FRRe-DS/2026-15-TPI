import { obtenerToken } from "./token";
import type { ConductorConUbicacion, TipoVehiculo, TipoServicio } from "./tipos";

export class ErrorApi extends Error {
  readonly status: number;
  readonly codigo?: string;

  constructor(status: number, mensaje: string, codigo?: string) {
    super(mensaje);
    this.name = "ErrorApi";
    this.status = status;
    this.codigo = codigo;
  }
}

export interface FiltrosListarConductores {
  disponible?: boolean;
  habilitado?: boolean;
  tipo_vehiculo?: TipoVehiculo;
  tipo_servicio?: TipoServicio;
  latitud?: number;
  longitud?: number;
}

export interface ListarConductoresOpciones {
  apiUrl?: string;
  token?: string;
  filtros?: FiltrosListarConductores;
}

export async function listarConductores(
  opciones?: ListarConductoresOpciones
): Promise<ConductorConUbicacion[]> {
  const token = opciones?.token ?? (await obtenerToken());
  const rawApiUrl = opciones?.apiUrl ?? process.env.API_URL ?? "http://localhost:8080/api/v1";
  const apiUrl = rawApiUrl.replace(/\/$/, "");

  let url = `${apiUrl}/conductores`;

  if (opciones?.filtros) {
    const params = new URLSearchParams();
    if (opciones.filtros.disponible !== undefined) {
      params.append("disponible", String(opciones.filtros.disponible));
    }
    if (opciones.filtros.habilitado !== undefined) {
      params.append("habilitado", String(opciones.filtros.habilitado));
    }
    if (opciones.filtros.tipo_vehiculo) {
      params.append("tipo_vehiculo", opciones.filtros.tipo_vehiculo);
    }
    if (opciones.filtros.tipo_servicio) {
      params.append("tipo_servicio", opciones.filtros.tipo_servicio);
    }
    if (opciones.filtros.latitud !== undefined) {
      params.append("latitud", String(opciones.filtros.latitud));
    }
    if (opciones.filtros.longitud !== undefined) {
      params.append("longitud", String(opciones.filtros.longitud));
    }
    const queryString = params.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/json",
      },
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new ErrorApi(0, `Error de conexión con la API: ${msg}`);
  }

  if (!response.ok) {
    let mensaje = `Error HTTP ${response.status}`;
    let codigo: string | undefined;

    try {
      const errBody = await response.json();
      if (errBody && typeof errBody === "object") {
        if (typeof errBody.mensaje === "string") {
          mensaje = errBody.mensaje;
        }
        if (typeof errBody.codigo === "string") {
          codigo = errBody.codigo;
        }
      }
    } catch {
      mensaje = response.statusText || mensaje;
    }

    throw new ErrorApi(response.status, mensaje, codigo);
  }

  return (await response.json()) as ConductorConUbicacion[];
}

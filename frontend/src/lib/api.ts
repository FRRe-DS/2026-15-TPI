import { obtenerToken } from "./token";
import type {
  ConductorConUbicacion,
  EstadoConductor,
  EstadoConductorRequest,
  EstadoOperativo,
  EstadoSolicitud,
  RespuestaSolicitudRequest,
  Solicitud,
  TipoVehiculo,
  TipoServicio,
  UbicacionConductor,
} from "./tipos";
import { esUuid } from "./ids";

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
  estado?: EstadoOperativo;
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
    if (opciones.filtros.estado) {
      params.append("estado", opciones.filtros.estado);
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

export interface OpcionesConductor {
  token: string;
  apiUrl?: string;
}

function resolverApiUrl(apiUrl?: string): string {
  const crudo = apiUrl ?? process.env.API_URL ?? "http://localhost:8080/api/v1";
  return crudo.replace(/\/$/, "");
}

async function leerError(response: Response): Promise<ErrorApi> {
  let mensaje = `Error HTTP ${response.status}`;
  let codigo: string | undefined;

  try {
    const cuerpo = await response.json();
    if (cuerpo && typeof cuerpo === "object") {
      if (typeof cuerpo.mensaje === "string") mensaje = cuerpo.mensaje;
      if (typeof cuerpo.codigo === "string") codigo = cuerpo.codigo;
    }
  } catch {
    mensaje = response.statusText || mensaje;
  }

  return new ErrorApi(response.status, mensaje, codigo);
}

async function pedir<T>(
  ruta: string,
  metodo: "GET" | "PATCH" | "POST",
  opciones: OpcionesConductor,
  cuerpo?: unknown
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${opciones.token}`,
    Accept: "application/json",
  };
  if (cuerpo !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(`${resolverApiUrl(opciones.apiUrl)}${ruta}`, {
      method: metodo,
      headers,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new ErrorApi(0, `Error de conexión con la API: ${msg}`);
  }

  if (!response.ok) throw await leerError(response);
  return (await response.json()) as T;
}

/** Corta antes de pedir: un id que no es UUID no llega a la URL (evita rutas como `../x`). */
function exigirUuid(id: string, descripcion: string): string {
  if (!esUuid(id)) {
    throw new ErrorApi(400, `El id ${descripcion} no es un UUID válido.`, "ID_INVALIDO");
  }
  return id;
}

export async function obtenerEstado(idConductor: string, opciones: OpcionesConductor) {
  return await pedir<EstadoConductor>(`/conductores/${exigirUuid(idConductor, "del conductor")}/estado`, "GET", opciones);
}

export async function actualizarEstado(
  idConductor: string,
  cambios: EstadoConductorRequest,
  opciones: OpcionesConductor
) {
  return await pedir<EstadoConductor>(`/conductores/${exigirUuid(idConductor, "del conductor")}/estado`, "PATCH", opciones, cambios);
}

export async function obtenerUbicacion(idConductor: string, opciones: OpcionesConductor) {
  return await pedir<UbicacionConductor>(`/conductores/${exigirUuid(idConductor, "del conductor")}/ubicacion`, "GET", opciones);
}

export interface OpcionesListarSolicitudes extends OpcionesConductor {
  estado?: EstadoSolicitud;
}

export async function listarSolicitudes(idConductor: string, opciones: OpcionesListarSolicitudes) {
  const { estado, ...base } = opciones;
  const consulta = estado ? `?${new URLSearchParams({ estado }).toString()}` : "";
  return await pedir<Solicitud[]>(`/conductores/${exigirUuid(idConductor, "del conductor")}/solicitudes${consulta}`, "GET", base);
}

export async function responderSolicitud(
  idSolicitud: string,
  respuesta: RespuestaSolicitudRequest,
  opciones: OpcionesConductor
) {
  return await pedir<Solicitud>(`/solicitudes/${exigirUuid(idSolicitud, "de la solicitud")}`, "POST", opciones, respuesta);
}

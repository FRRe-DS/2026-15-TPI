/**
 * Tipos basados en el contrato docs/contract/openapi.yaml (1.2.0) del Módulo M3
 */

export type EstadoHabilitacion =
  | "PENDIENTE"
  | "OBSERVADA"
  | "APROBADA"
  | "SUSPENDIDA"
  | "RECHAZADA";

export type AccionHabilitacion =
  | "ALTA"
  | "APROBAR"
  | "OBSERVAR"
  | "SUSPENDER"
  | "RECHAZAR";

export type TipoVehiculo = "AUTO" | "MOTO";

export type TipoServicio = "PASAJEROS" | "ENVIOS";

export type EstadoDocumento = "VIGENTE" | "VENCIDO";

/** Qué está haciendo el conductor ahora. OCUPADO lo asigna M3 al aceptar una solicitud. */
export type EstadoOperativo =
  | "DESCONECTADO"
  | "CONECTADO"
  | "DISPONIBLE"
  | "OCUPADO";

/** Estados que el conductor puede pedir en PATCH /conductores/{id}/estado (no incluye OCUPADO). */
export type EstadoOperativoPedible = Exclude<EstadoOperativo, "OCUPADO">;

/** Pendiente de confirmar con M5 (TODO en el contrato). */
export type EstadoSolicitud = "PENDIENTE" | "ACEPTADO" | "RECHAZADO" | "VENCIDA";

export type RespuestaSolicitud = "ACEPTADO" | "RECHAZADO";

export interface DocumentoConductor {
  id_conductor: number;
  tipo: string;
  numero: string;
  categoria?: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  url_archivo: string;
  estado: EstadoDocumento;
}

export interface VehiculoResumen {
  id: number;
  tipo: TipoVehiculo;
  patente: string;
  marca: string;
  modelo: string;
  anio: number;
  habilitacion: EstadoHabilitacion;
}

export interface Conductor {
  id: number;
  dni: string;
  nombre: string;
  apellido: string;
  telefono: string;
  email: string;
  habilitacion: EstadoHabilitacion;
  estado: EstadoOperativo;
  puntaje_promedio?: number | null;
  cantidad_calificaciones?: number;
  documentos: DocumentoConductor[];
  vehiculos: VehiculoResumen[];
}

export interface ConductorConUbicacion extends Conductor {
  id_vehiculo_activo?: number | null;
  latitud?: number | null;
  longitud?: number | null;
  fecha_act_ubic?: string | null;
}

/**
 * Cuerpo de PATCH /conductores/{id}/estado.
 * Hay que mandar al menos un campo, y latitud y longitud van juntas.
 */
export interface EstadoConductorRequest {
  estado?: EstadoOperativoPedible;
  id_vehiculo_activo?: number | null;
  latitud?: number;
  longitud?: number;
}

export interface EstadoConductor {
  id_conductor: number;
  estado: EstadoOperativo;
  id_vehiculo_activo?: number | null;
  actualizado: string;
}

/** Los tres campos en null significan ubicación desconocida. */
export interface UbicacionConductor {
  id_conductor: number;
  latitud: number | null;
  longitud: number | null;
  fecha_act_ubic: string | null;
}

export interface Solicitud {
  id: number;
  id_conductor: number;
  id_viaje?: number | null;
  estado: EstadoSolicitud;
  vence_en: string;
  respuesta?: RespuestaSolicitud | null;
  hora_rta?: string | null;
}

export interface RespuestaSolicitudRequest {
  respuesta: RespuestaSolicitud;
  hora_rta: string;
}
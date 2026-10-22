/**
 * Tipos basados en el contrato docs/contract/openapi.yaml del Módulo M3
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
  conectado: boolean;
  disponible: boolean;
  documentos: DocumentoConductor[];
  vehiculos: VehiculoResumen[];
}

export interface ConductorConUbicacion extends Conductor {
  latitud?: number | null;
  longitud?: number | null;
  fecha_act_ubic?: string | null;
}

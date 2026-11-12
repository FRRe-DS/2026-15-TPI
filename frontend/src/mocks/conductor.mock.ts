import type {
    EstadoConductor,
    EstadoOperativo,
    Solicitud,
    UbicacionConductor,
  } from "../lib/tipos";
  
  /**
   * Datos simulados del conductor en sesión, según el contrato 1.2.0.
   * Usan el conductor 1 y su vehículo 1 (ver conductores.mock.ts).
   */
  
  /** Un estado de ejemplo por cada estado operativo del contrato. */
  export const MOCK_ESTADOS_CONDUCTOR: Record<EstadoOperativo, EstadoConductor> = {
    DESCONECTADO: {
      id_conductor: 1,
      estado: "DESCONECTADO",
      id_vehiculo_activo: null,
      actualizado: "2026-11-10T08:00:00Z",
    },
    CONECTADO: {
      id_conductor: 1,
      estado: "CONECTADO",
      id_vehiculo_activo: 1,
      actualizado: "2026-11-10T09:00:00Z",
    },
    DISPONIBLE: {
      id_conductor: 1,
      estado: "DISPONIBLE",
      id_vehiculo_activo: 1,
      actualizado: "2026-11-10T09:30:00Z",
    },
    OCUPADO: {
      id_conductor: 1,
      estado: "OCUPADO",
      id_vehiculo_activo: 1,
      actualizado: "2026-11-10T18:44:10Z",
    },
  };
  
  /** Una solicitud en cada estado posible: PENDIENTE, ACEPTADO, RECHAZADO y VENCIDA. */
  export const MOCK_SOLICITUDES: Solicitud[] = [
    {
      id: 340,
      id_conductor: 1,
      id_viaje: 5521,
      estado: "ACEPTADO",
      vence_en: "2026-11-10T18:45:30Z",
      respuesta: "ACEPTADO",
      hora_rta: "2026-11-10T18:44:10Z",
    },
    {
      id: 341,
      id_conductor: 1,
      id_viaje: 5522,
      estado: "PENDIENTE",
      vence_en: "2026-11-12T20:30:00Z",
      respuesta: null,
      hora_rta: null,
    },
    {
      id: 342,
      id_conductor: 1,
      id_viaje: 5523,
      estado: "RECHAZADO",
      vence_en: "2026-11-10T17:20:30Z",
      respuesta: "RECHAZADO",
      hora_rta: "2026-11-10T17:19:50Z",
    },
    {
      id: 343,
      id_conductor: 1,
      id_viaje: 5524,
      estado: "VENCIDA",
      vence_en: "2026-11-10T16:05:30Z",
      respuesta: null,
      hora_rta: null,
    },
  ];
  
  /** Última ubicación informada por el conductor. */
  export const MOCK_UBICACION: UbicacionConductor = {
    id_conductor: 1,
    latitud: -34.6037,
    longitud: -58.3816,
    fecha_act_ubic: "2026-11-10T18:50:00Z",
  };
  
  /** Ubicación desconocida: los tres campos en null, nunca (0, 0). */
  export const MOCK_UBICACION_DESCONOCIDA: UbicacionConductor = {
    id_conductor: 1,
    latitud: null,
    longitud: null,
    fecha_act_ubic: null,
  };
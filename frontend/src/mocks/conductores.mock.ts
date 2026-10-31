/**
 * Datos mock del Módulo M3 para desarrollo sin backend.
 *
 * Estructura exactamente igual a la respuesta de GET /api/v1/conductores
 * (ConductorConUbicacion[]). Cubre los cinco estados de habilitación,
 * casos con y sin ubicación, documentos vigentes/vencidos y vehículos.
 *
 * Activar con USE_MOCK=true en .env.local
 */

import type { ConductorConUbicacion } from "../lib/tipos";

export const MOCK_CONDUCTORES: ConductorConUbicacion[] = [
  // ── 1. APROBADA ── completo: con documentos, vehículos y ubicación ──────────
  {
    id: 1,
    dni: "28345678",
    nombre: "María",
    apellido: "González",
    telefono: "3624123456",
    email: "maria.gonzalez@example.com",
    habilitacion: "APROBADA",
    conectado: true,
    disponible: true,
    latitud: -27.451,
    longitud: -58.986,
    fecha_act_ubic: "2026-10-30T12:00:00Z",
    documentos: [
      {
        id_conductor: 1,
        tipo: "LICENCIA",
        numero: "LIC-001",
        categoria: "B",
        fecha_emision: "2023-01-15",
        fecha_vencimiento: "2028-01-15",
        url_archivo: "https://storage.example.com/licencias/lic-001.pdf",
        estado: "VIGENTE",
      },
    ],
    vehiculos: [
      {
        id: 10,
        tipo: "AUTO",
        patente: "AB123CD",
        marca: "Toyota",
        modelo: "Corolla",
        anio: 2022,
        habilitacion: "APROBADA",
      },
    ],
  },

  // ── 2. PENDIENTE ── sin ubicación, sin documentos, sin vehículos ─────────────
  {
    id: 2,
    dni: "35678901",
    nombre: "Carlos",
    apellido: "Ramírez",
    telefono: "3624987654",
    email: "carlos.ramirez@example.com",
    habilitacion: "PENDIENTE",
    conectado: false,
    disponible: false,
    latitud: null,
    longitud: null,
    fecha_act_ubic: null,
    documentos: [],
    vehiculos: [],
  },

  // ── 3. OBSERVADA ── con licencia vencida, vehículo pendiente ─────────────────
  {
    id: 3,
    dni: "20111222",
    nombre: "Laura",
    apellido: "Fernández",
    telefono: "3624555333",
    email: "laura.fernandez@example.com",
    habilitacion: "OBSERVADA",
    conectado: false,
    disponible: false,
    latitud: null,
    longitud: null,
    fecha_act_ubic: null,
    documentos: [
      {
        id_conductor: 3,
        tipo: "LICENCIA",
        numero: "LIC-003",
        categoria: "A",
        fecha_emision: "2018-06-01",
        fecha_vencimiento: "2023-06-01",
        url_archivo: "https://storage.example.com/licencias/lic-003.pdf",
        estado: "VENCIDO",
      },
    ],
    vehiculos: [
      {
        id: 30,
        tipo: "MOTO",
        patente: "MO456PQ",
        marca: "Honda",
        modelo: "CB 300",
        anio: 2021,
        habilitacion: "PENDIENTE",
      },
    ],
  },

  // ── 4. SUSPENDIDA ── con ubicación, vehículo aprobado ────────────────────────
  {
    id: 4,
    dni: "18999000",
    nombre: "Jorge",
    apellido: "Medina",
    telefono: "3624000111",
    email: "jorge.medina@example.com",
    habilitacion: "SUSPENDIDA",
    conectado: false,
    disponible: false,
    latitud: -27.462,
    longitud: -58.971,
    fecha_act_ubic: "2026-10-28T09:30:00Z",
    documentos: [
      {
        id_conductor: 4,
        tipo: "LICENCIA",
        numero: "LIC-004",
        categoria: "B",
        fecha_emision: "2022-03-10",
        fecha_vencimiento: "2027-03-10",
        url_archivo: "https://storage.example.com/licencias/lic-004.pdf",
        estado: "VIGENTE",
      },
    ],
    vehiculos: [
      {
        id: 40,
        tipo: "AUTO",
        patente: "XY789AB",
        marca: "Renault",
        modelo: "Logan",
        anio: 2020,
        habilitacion: "APROBADA",
      },
    ],
  },

  // ── 5. RECHAZADA ── estado final, sin ubicación, sin vehículos ───────────────
  {
    id: 5,
    dni: "40123456",
    nombre: "Sofía",
    apellido: "Torres",
    telefono: "3624222999",
    email: "sofia.torres@example.com",
    habilitacion: "RECHAZADA",
    conectado: false,
    disponible: false,
    latitud: null,
    longitud: null,
    fecha_act_ubic: null,
    documentos: [],
    vehiculos: [],
  },

  // ── 6. APROBADA ── conectado pero no disponible, varios vehículos ─────────────
  {
    id: 6,
    dni: "31456789",
    nombre: "Diego",
    apellido: "López",
    telefono: "3624333777",
    email: "diego.lopez@example.com",
    habilitacion: "APROBADA",
    conectado: true,
    disponible: false,
    latitud: -27.455,
    longitud: -58.979,
    fecha_act_ubic: "2026-10-30T11:15:00Z",
    documentos: [
      {
        id_conductor: 6,
        tipo: "LICENCIA",
        numero: "LIC-006",
        categoria: "B",
        fecha_emision: "2021-07-20",
        fecha_vencimiento: "2026-07-20",
        url_archivo: "https://storage.example.com/licencias/lic-006.pdf",
        estado: "VIGENTE",
      },
    ],
    vehiculos: [
      {
        id: 60,
        tipo: "AUTO",
        patente: "RS321UV",
        marca: "Volkswagen",
        modelo: "Gol",
        anio: 2019,
        habilitacion: "APROBADA",
      },
      {
        id: 61,
        tipo: "MOTO",
        patente: "MM001ZZ",
        marca: "Yamaha",
        modelo: "FZ 25",
        anio: 2023,
        habilitacion: "PENDIENTE",
      },
    ],
  },
];

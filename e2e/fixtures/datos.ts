/**
 * Generadores de datos únicos.
 *
 * La API no expone `DELETE`, así que los tests que crean entidades son
 * aditivos: cada corrida usa un DNI y una patente distintos para no chocar con
 * la corrida anterior ni con el seed.
 */

let secuencia = 0;

function siguiente(): number {
  secuencia += 1;
  return secuencia;
}

/** DNI válido de 8 dígitos (`^[0-9]{7,8}$`), único dentro de la corrida. */
export function dniUnico(): string {
  const sufijo = String((Date.now() + siguiente()) % 10_000_000).padStart(7, "0");
  return `3${sufijo}`;
}

/** Patente única dentro de la corrida (máximo 10 caracteres). */
export function patenteUnica(): string {
  const sufijo = String((Date.now() + siguiente()) % 10_000_000).padStart(7, "0");
  return `E2E${sufijo}`;
}

export type DatosConductor = {
  dni: string;
  nombre: string;
  apellido: string;
  telefono: string;
  email: string;
};

export function datosConductor(cambios: Partial<DatosConductor> = {}): DatosConductor {
  const dni = dniUnico();
  return {
    dni,
    nombre: "E2E",
    apellido: "Playwright",
    telefono: "+5491100000000",
    email: `e2e-${dni}@example.com`,
    ...cambios,
  };
}

export type DatosVehiculo = {
  tipo: "AUTO" | "MOTO";
  patente: string;
  marca: string;
  modelo: string;
  anio: number;
  tipos_serv: Array<"PASAJEROS" | "ENVIOS">;
};

export function datosVehiculo(cambios: Partial<DatosVehiculo> = {}): DatosVehiculo {
  return {
    tipo: "AUTO",
    patente: patenteUnica(),
    marca: "Toyota",
    modelo: "Corolla",
    anio: 2022,
    tipos_serv: ["PASAJEROS"],
    ...cambios,
  };
}

export type DatosLicencia = {
  tipo: "LICENCIA";
  numero: string;
  categoria: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  url_archivo: string;
};

export function datosLicencia(cambios: Partial<DatosLicencia> = {}): DatosLicencia {
  return {
    tipo: "LICENCIA",
    numero: `LIC-${Date.now()}`,
    categoria: "B1",
    fecha_emision: "2024-05-10",
    fecha_vencimiento: "2028-05-10",
    url_archivo: "https://storage.example.com/licencias/e2e.pdf",
    ...cambios,
  };
}

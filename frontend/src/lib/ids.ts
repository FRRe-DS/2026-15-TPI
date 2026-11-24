const PATRON_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Indica si el valor es un UUID en su forma de texto (los ids del contrato 2.0.0). */
export function esUuid(valor: unknown): valor is string {
  return typeof valor === "string" && PATRON_UUID.test(valor);
}

/** Forma abreviada para mostrar en pantalla (el id completo no entra en un título). Solo es visual: nunca identifica ni se manda a la API. */
export function idCorto(id: string): string {
  return id.slice(0, 8);
}

/** UUID v4 determinista para los datos simulados y las pruebas: `uid(1)` es siempre el mismo. */
export function uid(numero: number): string {
  if (!Number.isInteger(numero) || numero < 0 || numero > 999_999_999_999) {
    throw new RangeError(`uid() admite enteros de 0 a 999999999999, no ${numero}`);
  }
  return `00000000-0000-4000-8000-${String(numero).padStart(12, "0")}`;
}

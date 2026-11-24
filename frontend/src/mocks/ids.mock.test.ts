import { describe, expect, it } from "vitest";
import { esUuid } from "../lib/ids";
import { uid } from "./ids.mock";

describe("uid", () => {
  it("devuelve siempre el mismo UUID válido para el mismo número", () => {
    expect(uid(5521)).toBe(uid(5521));
    expect(esUuid(uid(5521))).toBe(true);
    expect(uid(1)).not.toBe(uid(2));
  });

  it.each([-1, 1.5, Number.NaN, 1_000_000_000_000])("rechaza el número fuera de rango %s", (numero) => {
    expect(() => uid(numero)).toThrow(RangeError);
  });
});

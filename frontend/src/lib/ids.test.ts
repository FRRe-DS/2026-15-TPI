import { describe, expect, it } from "vitest";
import { esUuid, idCorto } from "./ids";

const UUID = "7b0e3a8e-4f7c-4d1a-9a52-1f0c2f9d6b11";

describe("esUuid", () => {
  it("acepta un UUID en minúsculas o mayúsculas", () => {
    expect(esUuid(UUID)).toBe(true);
    expect(esUuid(UUID.toUpperCase())).toBe(true);
  });

  it.each([1, 0, true, null, undefined, "", "1", "no-es-un-uuid", UUID.slice(1), `${UUID}0`])(
    "rechaza %s",
    (valor) => {
      expect(esUuid(valor)).toBe(false);
    }
  );
});

describe("idCorto", () => {
  it("devuelve los primeros 8 caracteres del UUID", () => {
    expect(idCorto(UUID)).toBe("7b0e3a8e");
  });
});

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import Page from "./page";
import * as apiModule from "../lib/api";
import { MOCK_CONDUCTORES } from "../mocks/conductores.mock";

describe("Page con USE_MOCK", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("con USE_MOCK=true muestra los datos simulados sin llamar a la API", async () => {
    vi.stubEnv("USE_MOCK", "true");
    const espia = vi
      .spyOn(apiModule, "listarConductores")
      .mockResolvedValue([]);

    const PageComponent = await Page();
    render(PageComponent);

    expect(espia).not.toHaveBeenCalled();
    MOCK_CONDUCTORES.forEach((conductor) => {
      expect(screen.getByText(conductor.dni)).toBeInTheDocument();
    });
    expect(screen.queryByText("No hay conductores")).not.toBeInTheDocument();
  });

  it.each(["false", ""])(
    "con USE_MOCK='%s' llama a la API como siempre",
    async (valor) => {
      vi.stubEnv("USE_MOCK", valor);
      const espia = vi
        .spyOn(apiModule, "listarConductores")
        .mockResolvedValue([]);

      const PageComponent = await Page();
      render(PageComponent);

      expect(espia).toHaveBeenCalledTimes(1);
      expect(screen.getByText("No hay conductores")).toBeInTheDocument();
    }
  );
});
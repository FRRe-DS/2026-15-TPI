import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DisenoPage from "./page";

describe("prototipo de viaje en curso", () => {
  it("habilita finalizar el viaje solo después de confirmar que el pasajero subió", () => {
    render(<DisenoPage />);

    fireEvent.click(screen.getByRole("button", { name: "4. Viaje en Curso (US4)" }));

    const passengerBoardedButton = screen.getByRole("button", { name: "Pasajero subió" });
    const finishTripButton = screen.getByRole("button", { name: "Finalizar viaje" });

    expect(passengerBoardedButton).toBeEnabled();
    expect(finishTripButton).toBeDisabled();

    fireEvent.click(passengerBoardedButton);

    expect(passengerBoardedButton).toBeDisabled();
    expect(finishTripButton).toBeEnabled();
  });
});

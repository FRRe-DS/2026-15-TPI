import React from "react";
import { listarConductores } from "../lib/api";
import { ListadoConductores } from "../components/ListadoConductores";
import type { ConductorConUbicacion } from "../lib/tipos";

export const dynamic = "force-dynamic";

export default async function Page() {
  let conductores: ConductorConUbicacion[] = [];
  let error: string | null = null;

  try {
    conductores = await listarConductores();
  } catch (err: unknown) {
    error = err instanceof Error ? err.message : String(err);
  }

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: "bold" }}>
          Módulo de Conductores - M3
        </h1>
        <p style={{ color: "#666" }}>
          Listado de conductores registrados en la plataforma
        </p>
      </header>
      <ListadoConductores conductores={conductores} error={error} />
    </main>
  );
}

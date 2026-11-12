import React from "react";
import { listarConductores } from "../lib/api";
import { ListadoConductores } from "../components/ListadoConductores";
import type { ConductorConUbicacion } from "../lib/tipos";
import styles from "./page.module.css";

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
    <main className={styles.pagina}>
      <header className={styles.encabezado}>
        <p className={styles.etiqueta}>OPERACIONES · MÓDULO M3</p>
        <h1>Conductores</h1>
        <p>Listado de conductores registrados en la plataforma</p>
      </header>
      <ListadoConductores conductores={conductores} error={error} />
    </main>
  );
}

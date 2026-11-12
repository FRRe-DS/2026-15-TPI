import React from "react";
import { Navegacion } from "../components/Navegacion";
import { ConductorDemoProvider } from "../components/conductor/ConductorDemo";
import "./globals.css";

export const metadata = {
  title: "Módulo M3 - Conductores y Vehículos",
  description: "Plataforma de Movilidad - Módulo de Conductores",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>
        <ConductorDemoProvider>
          <Navegacion />
          {children}
        </ConductorDemoProvider>
      </body>
    </html>
  );
}

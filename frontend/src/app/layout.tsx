import React from "react";

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
      <body style={{ margin: 0, padding: 0 }}>{children}</body>
    </html>
  );
}

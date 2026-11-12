"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Navegacion.module.css";

const pantallas = [
  { nombre: "Conductores", ruta: "/" },
  { nombre: "Iniciar sesión", ruta: "/login" },
  { nombre: "Estado", ruta: "/estado" },
  { nombre: "Solicitudes", ruta: "/solicitudes" },
  { nombre: "Viaje", ruta: "/viaje" },
  { nombre: "Ubicación", ruta: "/ubicacion" },
];

export function Navegacion() {
  const pathname = usePathname();

  if (pathname === "/login") return null;

  return (
    <nav className={styles.navegacion} aria-label="Navegación principal">
      <ul className={styles.lista}>
        {pantallas.map((pantalla) => (
          <li key={pantalla.ruta}>
            <Link
              className={styles.enlace}
              href={pantalla.ruta}
              aria-current={pathname === pantalla.ruta ? "page" : undefined}
            >
              {pantalla.nombre}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

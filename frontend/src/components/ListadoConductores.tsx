import React from "react";
import type { ConductorConUbicacion, EstadoHabilitacion } from "../lib/tipos";

export interface ListadoConductoresProps {
  conductores?: ConductorConUbicacion[];
  error?: string | null;
}
const ESTILOS_BADGE: Record<
  EstadoHabilitacion,
  { color: "verde" | "amarillo" | "rojo"; fondo: string; texto: string }
> = {
  APROBADA: { color: "verde", fondo: "#dcfce7", texto: "#166534" },
  PENDIENTE: { color: "amarillo", fondo: "#fef9c3", texto: "#854d0e" },
  OBSERVADA: { color: "amarillo", fondo: "#fef9c3", texto: "#854d0e" },
  SUSPENDIDA: { color: "rojo", fondo: "#fee2e2", texto: "#991b1b" },
  RECHAZADA: { color: "rojo", fondo: "#fee2e2", texto: "#991b1b" },
};

function BadgeHabilitacion({ estado }: { estado: EstadoHabilitacion }) {
  const { color, fondo, texto } = ESTILOS_BADGE[estado];

  return (
    <span
      data-color={color}
      style={{
        backgroundColor: fondo,
        color: texto,
        padding: "2px 10px",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: 600,
      }}
    >
      {estado}
    </span>
  );
}
export function ListadoConductores({
  conductores,
  error,
}: ListadoConductoresProps) {
  if (error) {
    return (
      <div role="alert" className="p-4 bg-red-100 border border-red-400 text-red-700 rounded">
        <p className="font-semibold">Error al cargar conductores:</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!conductores || conductores.length === 0) {
    return (
      <div className="p-4 text-gray-500 italic">
        <p>No hay conductores</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-left border">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Nombre
            </th>
            <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Apellido
            </th>
            <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
              DNI
            </th>
            <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Habilitación
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {conductores.map((conductor) => (
            <tr key={conductor.id}>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {conductor.nombre}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {conductor.apellido}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {conductor.dni}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                <BadgeHabilitacion estado={conductor.habilitacion} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

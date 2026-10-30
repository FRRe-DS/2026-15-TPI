import React from "react";
import type { ConductorConUbicacion, EstadoHabilitacion } from "../lib/tipos";

export interface ListadoConductoresProps {
  conductores?: ConductorConUbicacion[];
  error?: string | null;
}

const ESTILOS_BADGE: Record<EstadoHabilitacion, { bg: string; color: string; border: string }> = {
  APROBADA: {
    bg: "#e6f4ea",
    color: "#137333",
    border: "#ceead6",
  },
  PENDIENTE: {
    bg: "#fef7e0",
    color: "#b06000",
    border: "#feefc3",
  },
  OBSERVADA: {
    bg: "#fff0d4",
    color: "#c26400",
    border: "#ffd8a8",
  },
  SUSPENDIDA: {
    bg: "#fce8e6",
    color: "#c5221f",
    border: "#fad2cf",
  },
  RECHAZADA: {
    bg: "#f1f3f4",
    color: "#5f6368",
    border: "#dadce0",
  },
};

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
          {conductores.map((conductor) => {
            const estilo = ESTILOS_BADGE[conductor.habilitacion] ?? {
              bg: "#f1f3f4",
              color: "#3c4043",
              border: "#dadce0",
            };

            return (
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
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <span
                    data-estado={conductor.habilitacion}
                    style={{
                      display: "inline-block",
                      padding: "0.25rem 0.6rem",
                      borderRadius: "9999px",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      backgroundColor: estilo.bg,
                      color: estilo.color,
                      border: `1px solid ${estilo.border}`,
                    }}
                  >
                    {conductor.habilitacion}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

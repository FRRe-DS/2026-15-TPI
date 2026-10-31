import React from "react";
import type { ConductorConUbicacion } from "../lib/tipos";

export interface ListadoConductoresProps {
  conductores?: ConductorConUbicacion[];
  error?: string | null;
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
                {conductor.habilitacion}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

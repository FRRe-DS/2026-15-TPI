from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.dominio.documento_vehiculo import DocumentoVehiculo


class RepositorioDocumentosVehiculo(ABC):
    @abstractmethod
    def guardar(self, id_vehiculo: UUID, documento: DocumentoVehiculo) -> DocumentoVehiculo:
        """Persiste el documento del vehículo y le asigna id."""

    @abstractmethod
    def listar_por_vehiculo(self, id_vehiculo: UUID) -> list[DocumentoVehiculo]:
        """Lista los documentos del vehículo, sin orden garantizado (los ids son UUID)."""

    @abstractmethod
    def listar_por_vehiculos(
        self, ids_vehiculo: Sequence[UUID]
    ) -> dict[UUID, list[DocumentoVehiculo]]:
        """Lista por lote los documentos de varios vehículos, en una sola consulta.

        Devuelve una clave por cada id pedido (lista vacía si no tiene documentos), cada lista
        sin orden garantizado (los ids son UUID); con una secuencia vacía devuelve {}.
        """

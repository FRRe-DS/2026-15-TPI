from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.dominio.documento_vehiculo import DocumentoVehiculo


class RepositorioDocumentosVehiculo(ABC):
    @abstractmethod
    def guardar(self, id_vehiculo: int, documento: DocumentoVehiculo) -> DocumentoVehiculo:
        """Persiste el documento del vehículo y le asigna id."""

    @abstractmethod
    def listar_por_vehiculo(self, id_vehiculo: int) -> list[DocumentoVehiculo]:
        """Lista los documentos del vehículo, en orden de alta."""

    @abstractmethod
    def listar_por_vehiculos(
        self, ids_vehiculo: Sequence[int]
    ) -> dict[int, list[DocumentoVehiculo]]:
        """Lista por lote los documentos de varios vehículos, en una sola consulta.

        Devuelve una clave por cada id pedido (lista vacía si no tiene documentos), cada lista
        en orden de alta; con una secuencia vacía devuelve {}.
        """

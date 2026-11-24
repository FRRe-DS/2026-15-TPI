from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.dominio.documento import Documento


class RepositorioDocumentos(ABC):
    @abstractmethod
    def guardar(self, id_conductor: UUID, documento: Documento) -> Documento:
        """Persiste el documento del conductor y le asigna id."""

    @abstractmethod
    def listar_por_conductor(self, id_conductor: UUID) -> list[Documento]:
        """Lista los documentos del conductor."""

    @abstractmethod
    def listar_por_conductores(self, ids_conductor: Sequence[UUID]) -> dict[UUID, list[Documento]]:
        """Lista por lote los documentos de varios conductores, en una sola consulta.

        Devuelve una clave por cada id pedido (lista vacía si no tiene documentos), cada lista
        sin orden garantizado (los ids son UUID); con una secuencia vacía devuelve {}.
        """

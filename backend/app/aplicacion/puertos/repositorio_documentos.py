from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.dominio.documento import Documento


class RepositorioDocumentos(ABC):
    @abstractmethod
    def guardar(self, id_conductor: int, documento: Documento) -> Documento:
        """Persiste el documento del conductor y le asigna id."""

    @abstractmethod
    def listar_por_conductor(self, id_conductor: int) -> list[Documento]:
        """Lista los documentos del conductor."""

    @abstractmethod
    def listar_por_conductores(self, ids_conductor: Sequence[int]) -> dict[int, list[Documento]]:
        """Lista por lote los documentos de varios conductores, en una sola consulta.

        Devuelve una clave por cada id pedido (lista vacía si no tiene documentos), cada lista
        en orden de alta; con una secuencia vacía devuelve {}.
        """

from abc import ABC, abstractmethod

from app.dominio.documento import Documento


class RepositorioDocumentos(ABC):
    @abstractmethod
    def guardar(self, id_conductor: int, documento: Documento) -> Documento:
        """Persiste el documento del conductor y le asigna id."""

    @abstractmethod
    def listar_por_conductor(self, id_conductor: int) -> list[Documento]:
        """Lista los documentos del conductor."""

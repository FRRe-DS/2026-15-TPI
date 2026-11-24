from abc import ABC, abstractmethod
from uuid import UUID

from app.dominio.solicitud import Solicitud


class RepositorioSolicitudes(ABC):
    @abstractmethod
    def guardar(self, solicitud: Solicitud) -> Solicitud:
        """Persiste la solicitud: alta (asigna id) si no lo tiene, actualización si ya lo tiene."""

    @abstractmethod
    def obtener(self, id_solicitud: UUID) -> Solicitud | None:
        """Devuelve la solicitud, o None si no existe."""

    @abstractmethod
    def listar_por_conductor(self, id_conductor: UUID) -> list[Solicitud]:
        """Lista todas las solicitudes del conductor, sin orden garantizado (los ids son UUID)."""

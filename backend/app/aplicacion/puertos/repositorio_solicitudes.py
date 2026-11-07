from abc import ABC, abstractmethod

from app.dominio.solicitud import Solicitud


class RepositorioSolicitudes(ABC):
    @abstractmethod
    def guardar(self, solicitud: Solicitud) -> Solicitud:
        """Persiste la solicitud: alta (asigna id) si no lo tiene, actualización si ya lo tiene."""

    @abstractmethod
    def obtener(self, id_solicitud: int) -> Solicitud | None:
        """Devuelve la solicitud, o None si no existe."""

    @abstractmethod
    def listar_por_conductor(self, id_conductor: int) -> list[Solicitud]:
        """Lista todas las solicitudes del conductor, en orden de alta."""

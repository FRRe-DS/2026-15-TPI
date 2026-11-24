from abc import ABC, abstractmethod
from uuid import UUID

from app.dominio.habilitacion import EventoHabilitacion


class RepositorioHabilitaciones(ABC):
    @abstractmethod
    def registrar_evento_conductor(self, id_conductor: UUID, evento: EventoHabilitacion) -> None:
        """Agrega un evento al historial de habilitación del conductor."""

    @abstractmethod
    def registrar_evento_vehiculo(self, id_vehiculo: UUID, evento: EventoHabilitacion) -> None:
        """Agrega un evento al historial de habilitación del vehículo."""

    @abstractmethod
    def historial_conductor(self, id_conductor: UUID) -> list[EventoHabilitacion]:
        """Devuelve los eventos de habilitación del conductor."""

    @abstractmethod
    def historial_vehiculo(self, id_vehiculo: UUID) -> list[EventoHabilitacion]:
        """Devuelve los eventos de habilitación del vehículo."""

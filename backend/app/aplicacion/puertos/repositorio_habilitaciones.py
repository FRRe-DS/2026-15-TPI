from abc import ABC, abstractmethod

from app.dominio.habilitacion import EventoHabilitacion


class RepositorioHabilitaciones(ABC):
    @abstractmethod
    def registrar_evento_conductor(
        self, id_conductor: int, evento: EventoHabilitacion
    ) -> None:
        """Agrega un evento al historial de habilitación del conductor."""

    @abstractmethod
    def registrar_evento_vehiculo(
        self, id_vehiculo: int, evento: EventoHabilitacion
    ) -> None:
        """Agrega un evento al historial de habilitación del vehículo."""

    @abstractmethod
    def historial_conductor(self, id_conductor: int) -> list[EventoHabilitacion]:
        """Devuelve los eventos de habilitación del conductor."""

    @abstractmethod
    def historial_vehiculo(self, id_vehiculo: int) -> list[EventoHabilitacion]:
        """Devuelve los eventos de habilitación del vehículo."""

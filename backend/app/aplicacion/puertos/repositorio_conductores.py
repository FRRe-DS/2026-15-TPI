from abc import ABC, abstractmethod

from app.dominio.conductor import Conductor
from app.dominio.vehiculo import TipoVehiculo


class RepositorioConductores(ABC):
    @abstractmethod
    def guardar(self, conductor: Conductor) -> Conductor:
        """Persiste el conductor y le asigna id. Lanza DniDuplicado si el DNI ya existe."""

    @abstractmethod
    def obtener(self, id_conductor: int) -> Conductor | None:
        """Devuelve el conductor o None si no existe."""

    @abstractmethod
    def listar(
        self,
        *,
        habilitado: bool | None = None,
        disponible: bool | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
    ) -> list[Conductor]:
        """Lista los conductores que cumplen los filtros indicados."""

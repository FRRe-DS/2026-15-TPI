from abc import ABC, abstractmethod

from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import TipoVehiculo, Vehiculo


class RepositorioVehiculos(ABC):
    @abstractmethod
    def guardar(self, vehiculo: Vehiculo) -> Vehiculo:
        """Persiste el vehículo y le asigna id. Lanza PatenteDuplicada si la patente ya existe."""

    @abstractmethod
    def obtener(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        """Devuelve el vehículo, o None si no existe o es de otro conductor."""

    @abstractmethod
    def listar_por_conductor(
        self,
        id_conductor: int,
        *,
        tipo: TipoVehiculo | None = None,
        habilitacion: EstadoHabilitacion | None = None,
    ) -> list[Vehiculo]:
        """Lista los vehículos del conductor que cumplen los filtros indicados."""

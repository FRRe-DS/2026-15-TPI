from abc import ABC, abstractmethod

from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.vehiculo import TipoServicio, TipoVehiculo


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
        estado: EstadoConductor | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
        tipo_servicio: TipoServicio | None = None,
    ) -> list[Conductor]:
        """Lista los conductores que cumplen todos los filtros indicados.

        `tipo_vehiculo` exige al menos un vehiculo de ese tipo y `tipo_servicio` al menos un
        vehiculo con ese tipo de servicio habilitado.
        """

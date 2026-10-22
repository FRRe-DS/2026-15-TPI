from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from app.aplicacion.puertos.repositorio_conductores import RepositorioConductores
from app.aplicacion.puertos.repositorio_documentos import RepositorioDocumentos
from app.aplicacion.puertos.repositorio_habilitaciones import (
    RepositorioHabilitaciones,
)
from app.aplicacion.puertos.repositorio_vehiculos import RepositorioVehiculos
from app.dominio.conductor import Conductor
from app.dominio.vehiculo import Vehiculo


class UnidadDeTrabajo(ABC):
    conductores: RepositorioConductores
    vehiculos: RepositorioVehiculos
    documentos: RepositorioDocumentos
    habilitaciones: RepositorioHabilitaciones

    @abstractmethod
    def __enter__(self) -> Self:
        """Abre la transacción."""

    @abstractmethod
    def __exit__(
        self,
        tipo_excepcion: type[BaseException] | None,
        excepcion: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        """Cierra la transacción; revierte los cambios no confirmados."""

    @abstractmethod
    def commit(self) -> None:
        """Confirma los cambios de la transacción."""

    @abstractmethod
    def rollback(self) -> None:
        """Descarta los cambios de la transacción."""

    @abstractmethod
    def bloquear_conductor(self, id_conductor: int) -> Conductor | None:
        """Obtiene el conductor con bloqueo de fila (SELECT ... FOR UPDATE)."""

    @abstractmethod
    def bloquear_vehiculo(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        """Obtiene el vehículo del conductor con bloqueo de fila (SELECT ... FOR UPDATE)."""

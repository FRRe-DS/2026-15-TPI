import copy
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from app.aplicacion.puertos.repositorio_conductores import RepositorioConductores
from app.aplicacion.puertos.repositorio_documentos import RepositorioDocumentos
from app.aplicacion.puertos.repositorio_habilitaciones import (
    RepositorioHabilitaciones,
)
from app.aplicacion.puertos.repositorio_vehiculos import RepositorioVehiculos
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.documento import Documento
from app.dominio.errores import DniDuplicado, PatenteDuplicada
from app.dominio.habilitacion import EstadoHabilitacion, EventoHabilitacion
from app.dominio.vehiculo import TipoVehiculo, Vehiculo


@dataclass
class _Estado:
    """Contenido de la "base" en memoria, compartido por todos los repositorios."""

    conductores: dict[int, Conductor] = field(default_factory=dict)
    vehiculos: dict[int, Vehiculo] = field(default_factory=dict)
    documentos: dict[int, tuple[int, Documento]] = field(default_factory=dict)
    eventos_conductor: dict[int, list[EventoHabilitacion]] = field(default_factory=dict)
    eventos_vehiculo: dict[int, list[EventoHabilitacion]] = field(default_factory=dict)

    def reemplazar_por(self, otro: "_Estado") -> None:
        self.__dict__.update(otro.__dict__)


def _guardar(entidades: dict, entidad):
    """Alta si la entidad no tiene id (se lo asigna); actualizacion si ya lo tiene."""
    if entidad.id is None:
        entidad.id = max(entidades, default=0) + 1
    entidades[entidad.id] = entidad
    return entidad


class RepositorioConductoresEnMemoria(RepositorioConductores):
    def __init__(self, estado: _Estado) -> None:
        self._estado = estado

    def guardar(self, conductor: Conductor) -> Conductor:
        dni_en_uso = any(
            otro.dni == conductor.dni and otro.id != conductor.id
            for otro in self._estado.conductores.values()
        )
        if dni_en_uso:
            raise DniDuplicado(f"Ya existe un conductor con el DNI {conductor.dni}")
        return _guardar(self._estado.conductores, conductor)

    def obtener(self, id_conductor: int) -> Conductor | None:
        return self._estado.conductores.get(id_conductor)

    def listar(
        self,
        *,
        habilitado: bool | None = None,
        disponible: bool | None = None,
        tipo_vehiculo: TipoVehiculo | None = None,
    ) -> list[Conductor]:
        conductores = list(self._estado.conductores.values())
        if habilitado is not None:
            conductores = [
                c
                for c in conductores
                if (c.habilitacion is EstadoHabilitacion.APROBADA) == habilitado
            ]
        if disponible is not None:
            conductores = [c for c in conductores if c.disponible == disponible]
        if tipo_vehiculo is not None:
            con_ese_tipo = {
                v.id_conductor for v in self._estado.vehiculos.values() if v.tipo is tipo_vehiculo
            }
            conductores = [c for c in conductores if c.id in con_ese_tipo]
        return conductores


class RepositorioVehiculosEnMemoria(RepositorioVehiculos):
    def __init__(self, estado: _Estado) -> None:
        self._estado = estado

    def guardar(self, vehiculo: Vehiculo) -> Vehiculo:
        patente_en_uso = any(
            otro.patente == vehiculo.patente and otro.id != vehiculo.id
            for otro in self._estado.vehiculos.values()
        )
        if patente_en_uso:
            raise PatenteDuplicada(f"Ya existe un vehiculo con la patente {vehiculo.patente}")
        return _guardar(self._estado.vehiculos, vehiculo)

    def obtener(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        vehiculo = self._estado.vehiculos.get(id_vehiculo)
        if vehiculo is None or vehiculo.id_conductor != id_conductor:
            return None
        return vehiculo

    def listar_por_conductor(
        self,
        id_conductor: int,
        *,
        tipo: TipoVehiculo | None = None,
        habilitacion: EstadoHabilitacion | None = None,
    ) -> list[Vehiculo]:
        return [
            v
            for v in self._estado.vehiculos.values()
            if v.id_conductor == id_conductor
            and (tipo is None or v.tipo is tipo)
            and (habilitacion is None or v.habilitacion is habilitacion)
        ]


class RepositorioDocumentosEnMemoria(RepositorioDocumentos):
    def __init__(self, estado: _Estado) -> None:
        self._estado = estado

    def guardar(self, id_conductor: int, documento: Documento) -> Documento:
        if documento.id is None:
            documento.id = max(self._estado.documentos, default=0) + 1
        self._estado.documentos[documento.id] = (id_conductor, documento)
        return documento

    def listar_por_conductor(self, id_conductor: int) -> list[Documento]:
        return [
            documento
            for dueno, documento in self._estado.documentos.values()
            if dueno == id_conductor
        ]


class RepositorioHabilitacionesEnMemoria(RepositorioHabilitaciones):
    def __init__(self, estado: _Estado) -> None:
        self._estado = estado

    def registrar_evento_conductor(self, id_conductor: int, evento: EventoHabilitacion) -> None:
        self._estado.eventos_conductor.setdefault(id_conductor, []).append(evento)

    def registrar_evento_vehiculo(self, id_vehiculo: int, evento: EventoHabilitacion) -> None:
        self._estado.eventos_vehiculo.setdefault(id_vehiculo, []).append(evento)

    def historial_conductor(self, id_conductor: int) -> list[EventoHabilitacion]:
        return list(self._estado.eventos_conductor.get(id_conductor, []))

    def historial_vehiculo(self, id_vehiculo: int) -> list[EventoHabilitacion]:
        return list(self._estado.eventos_vehiculo.get(id_vehiculo, []))


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    def __init__(self) -> None:
        self._estado = _Estado()
        self._confirmado = copy.deepcopy(self._estado)
        self.conductores = RepositorioConductoresEnMemoria(self._estado)
        self.vehiculos = RepositorioVehiculosEnMemoria(self._estado)
        self.documentos = RepositorioDocumentosEnMemoria(self._estado)
        self.habilitaciones = RepositorioHabilitacionesEnMemoria(self._estado)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        tipo_excepcion: type[BaseException] | None,
        excepcion: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        self.rollback()

    def commit(self) -> None:
        self._confirmado = copy.deepcopy(self._estado)

    def rollback(self) -> None:
        self._estado.reemplazar_por(copy.deepcopy(self._confirmado))

    def bloquear_conductor(self, id_conductor: int) -> Conductor | None:
        return self.conductores.obtener(id_conductor)

    def bloquear_vehiculo(self, id_conductor: int, id_vehiculo: int) -> Vehiculo | None:
        return self.vehiculos.obtener(id_conductor, id_vehiculo)

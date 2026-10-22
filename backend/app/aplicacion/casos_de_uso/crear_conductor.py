from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor
from app.dominio.habilitacion import (
    AccionHabilitacion,
    EstadoHabilitacion,
    EventoHabilitacion,
)

MOTIVO_ALTA = "Alta del conductor"


class CrearConductor:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self, *, dni: str, nombre: str, apellido: str, telefono: str, email: str
    ) -> ConductorDetalle:
        conductor = Conductor.crear(
            dni=dni, nombre=nombre, apellido=apellido, telefono=telefono, email=email
        )
        with self._uow:
            conductor = self._uow.conductores.guardar(conductor)
            self._uow.habilitaciones.registrar_evento_conductor(
                conductor.id, self._evento_de_alta()
            )
            self._uow.commit()
        return ConductorDetalle(conductor=conductor, documentos=[], vehiculos=[])

    def _evento_de_alta(self) -> EventoHabilitacion:
        return EventoHabilitacion(
            accion=AccionHabilitacion.ALTA,
            estado_anterior=None,
            estado_nuevo=EstadoHabilitacion.PENDIENTE,
            motivo=MOTIVO_ALTA,
            id_operador=None,
            fecha=self._reloj.ahora(),
        )

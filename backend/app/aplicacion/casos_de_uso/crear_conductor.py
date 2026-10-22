from app.aplicacion.casos_de_uso.historial import evento_de_alta
from app.aplicacion.casos_de_uso.resultados import ConductorDetalle
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor

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
                conductor.id, evento_de_alta(MOTIVO_ALTA, self._reloj.ahora())
            )
            self._uow.commit()
        return ConductorDetalle(conductor=conductor, documentos=[], vehiculos=[])

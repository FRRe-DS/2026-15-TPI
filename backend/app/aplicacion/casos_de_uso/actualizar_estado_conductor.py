from datetime import datetime

from app.aplicacion.casos_de_uso.encontrado import exigir_conductor, exigir_vehiculo
from app.aplicacion.casos_de_uso.resultados import EstadoDelConductor
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.disponibilidad import NO_INFORMADO, aplicar_cambio_estado
from app.dominio.errores import DatosInvalidos
from app.dominio.vehiculo import Vehiculo


class ActualizarEstadoConductor:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        reloj: Reloj,
        *,
        latitud_simulada: float,
        longitud_simulada: float,
    ) -> None:
        if latitud_simulada == 0 and longitud_simulada == 0:
            raise ValueError("La ubicacion simulada no puede ser la coordenada 0, 0")
        self._uow = uow
        self._reloj = reloj
        self._latitud_simulada = latitud_simulada
        self._longitud_simulada = longitud_simulada

    def ejecutar(
        self,
        *,
        id_conductor: int,
        estado: EstadoConductor | str | None = None,
        id_vehiculo_activo: int | None = NO_INFORMADO,
        latitud: float | None = None,
        longitud: float | None = None,
    ) -> EstadoDelConductor:
        _exigir_pedido_valido(estado, id_vehiculo_activo, latitud, longitud)
        with self._uow:
            conductor = exigir_conductor(self._uow.bloquear_conductor(id_conductor), id_conductor)
            vehiculo_activo = self._buscar_vehiculo_activo(conductor, id_vehiculo_activo)
            ahora = self._reloj.ahora()
            estaba_desconectado = conductor.estado is EstadoConductor.DESCONECTADO

            aplicar_cambio_estado(
                conductor,
                vehiculo_activo,
                estado=estado,
                id_vehiculo_activo=id_vehiculo_activo,
                ahora=ahora,
            )
            if latitud is not None:
                conductor.fijar_ubicacion(latitud, longitud, ahora)
            elif estaba_desconectado and _salio_de_desconectado(conductor):
                self._asignar_ubicacion_simulada(conductor, ahora)

            self._uow.conductores.guardar(conductor)
            self._uow.commit()
            return EstadoDelConductor.desde_conductor(conductor)

    def _buscar_vehiculo_activo(
        self, conductor: Conductor, id_vehiculo_informado: int | None
    ) -> Vehiculo | None:
        """Devuelve el vehiculo que quedara activo; uno informado que no es suyo es NoEncontrado."""
        if id_vehiculo_informado is NO_INFORMADO:
            id_vehiculo = conductor.id_vehiculo_activo
            es_pedido_explicito = False
        else:
            id_vehiculo = id_vehiculo_informado
            es_pedido_explicito = True
        if id_vehiculo is None:
            return None
        vehiculo = self._uow.vehiculos.obtener(conductor.id, id_vehiculo)
        if es_pedido_explicito:
            return exigir_vehiculo(vehiculo, conductor.id, id_vehiculo)
        return vehiculo

    def _asignar_ubicacion_simulada(self, conductor: Conductor, ahora: datetime) -> None:
        if not conductor.tiene_ubicacion:
            conductor.fijar_ubicacion(self._latitud_simulada, self._longitud_simulada, ahora)


def _salio_de_desconectado(conductor: Conductor) -> bool:
    return conductor.estado is not EstadoConductor.DESCONECTADO


def _exigir_pedido_valido(
    estado: EstadoConductor | str | None,
    id_vehiculo_activo: int | None,
    latitud: float | None,
    longitud: float | None,
) -> None:
    if (latitud is None) != (longitud is None):
        raise DatosInvalidos("latitud y longitud se informan juntas")
    es_cuerpo_vacio = (
        estado is None
        and id_vehiculo_activo is NO_INFORMADO
        and latitud is None
        and longitud is None
    )
    if es_cuerpo_vacio:
        raise DatosInvalidos("El pedido debe informar al menos un campo")

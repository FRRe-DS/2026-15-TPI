"""Reglas del estado operativo del conductor.

Un solo lugar decide cuando un conductor puede quedar `DISPONIBLE`, aplica los cambios
de estado y vehiculo activo, y marca `OCUPADO` al aceptar una solicitud.
"""

from datetime import datetime

from app.dominio.conductor import Conductor, EstadoConductor
from app.dominio.errores import ConductorNoHabilitado, DatosInvalidos
from app.dominio.habilitacion import EstadoHabilitacion
from app.dominio.vehiculo import Vehiculo


class _NoInformado:
    """Marca un argumento no informado, para distinguirlo de `None`."""


NO_INFORMADO = _NoInformado()


def puede_quedar_disponible(conductor: Conductor, vehiculo_activo: Vehiculo | None) -> bool:
    return (
        conductor.habilitacion is EstadoHabilitacion.APROBADA
        and vehiculo_activo is not None
        and vehiculo_activo.habilitacion is EstadoHabilitacion.APROBADA
    )


def aplicar_cambio_estado(
    conductor: Conductor,
    vehiculo_activo: Vehiculo | None,
    *,
    estado: EstadoConductor | None = None,
    id_vehiculo_activo: int | None | _NoInformado = NO_INFORMADO,
    ahora: datetime,
) -> bool:
    """Aplica un cambio de estado y/o de vehiculo activo. Devuelve si hubo cambio.

    `estado=None` y `id_vehiculo_activo=NO_INFORMADO` significan "no informado": no se
    modifican. `id_vehiculo_activo=None` quita el vehiculo activo.
    """
    if estado is EstadoConductor.OCUPADO:
        raise DatosInvalidos("OCUPADO lo asigna el sistema al aceptar una solicitud")

    id_anterior = conductor.id_vehiculo_activo
    id_nuevo = id_anterior if id_vehiculo_activo is NO_INFORMADO else id_vehiculo_activo
    cambio_vehiculo = id_nuevo != id_anterior

    if estado is EstadoConductor.DISPONIBLE:
        if id_nuevo is None or not puede_quedar_disponible(conductor, vehiculo_activo):
            raise ConductorNoHabilitado(
                "El conductor necesita habilitacion aprobada y un vehiculo activo aprobado"
            )
        estado_nuevo = EstadoConductor.DISPONIBLE
    elif estado is not None:
        estado_nuevo = estado
    elif (
        conductor.estado is EstadoConductor.DISPONIBLE
        and cambio_vehiculo
        and not puede_quedar_disponible(conductor, vehiculo_activo)
    ):
        estado_nuevo = EstadoConductor.CONECTADO
    else:
        estado_nuevo = conductor.estado

    if estado_nuevo is conductor.estado and not cambio_vehiculo:
        return False

    conductor.estado = estado_nuevo
    conductor.id_vehiculo_activo = id_nuevo
    conductor.fecha_ultimo_cambio_estado = ahora
    return True


def marcar_ocupado(
    conductor: Conductor,
    vehiculo_activo: Vehiculo | None,
    ahora: datetime,
) -> None:
    if (
        conductor.estado not in (EstadoConductor.CONECTADO, EstadoConductor.DISPONIBLE)
        or conductor.id_vehiculo_activo is None
        or not puede_quedar_disponible(conductor, vehiculo_activo)
    ):
        raise ConductorNoHabilitado("El conductor no esta habilitado para aceptar una solicitud")
    conductor.estado = EstadoConductor.OCUPADO
    conductor.fecha_ultimo_cambio_estado = ahora

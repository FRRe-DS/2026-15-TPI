from app.aplicacion.casos_de_uso.encontrado import exigir_conductor
from app.aplicacion.casos_de_uso.historial import en_orden_cronologico
from app.aplicacion.casos_de_uso.resultados import HabilitacionEventos
from app.aplicacion.puertos.reloj import Reloj
from app.aplicacion.puertos.unidad_de_trabajo import UnidadDeTrabajo
from app.dominio.documento import EstadoDocumento
from app.dominio.errores import LicenciaVigenteRequerida
from app.dominio.habilitacion import AccionHabilitacion, aplicar_accion


class AccionarHabilitacionConductor:
    def __init__(self, uow: UnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow = uow
        self._reloj = reloj

    def ejecutar(
        self,
        *,
        id_conductor: int,
        accion: AccionHabilitacion,
        motivo: str,
        id_operador: int,
    ) -> HabilitacionEventos:
        with self._uow:
            conductor = exigir_conductor(self._uow.bloquear_conductor(id_conductor), id_conductor)
            evento = aplicar_accion(
                conductor.habilitacion,
                accion,
                motivo,
                id_operador,
                self._reloj.ahora(),
            )
            if accion is AccionHabilitacion.APROBAR:
                self._exigir_licencia_vigente(id_conductor)
            conductor.habilitacion = evento.estado_nuevo
            self._uow.conductores.guardar(conductor)
            self._uow.habilitaciones.registrar_evento_conductor(id_conductor, evento)
            self._uow.commit()
            historial = self._uow.habilitaciones.historial_conductor(id_conductor)
            return HabilitacionEventos(
                id_conductor=id_conductor,
                estado=conductor.habilitacion,
                eventos=en_orden_cronologico(historial),
            )

    def _exigir_licencia_vigente(self, id_conductor: int) -> None:
        hoy = self._reloj.hoy()
        documentos = self._uow.documentos.listar_por_conductor(id_conductor)
        tiene_licencia_vigente = any(
            documento.estado_al(hoy) is EstadoDocumento.VIGENTE for documento in documentos
        )
        if not tiene_licencia_vigente:
            raise LicenciaVigenteRequerida("Aprobar requiere al menos una licencia vigente")

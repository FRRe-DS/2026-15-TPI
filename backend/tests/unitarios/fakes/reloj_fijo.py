from datetime import date, datetime, timedelta

from app.aplicacion.puertos.reloj import Reloj


class RelojFijo(Reloj):
    def __init__(self, ahora: datetime) -> None:
        self._ahora = ahora

    def ahora(self) -> datetime:
        return self._ahora

    def hoy(self) -> date:
        return self._ahora.date()

    def avanzar(self, *, dias: int = 0) -> None:
        self._ahora += timedelta(days=dias)

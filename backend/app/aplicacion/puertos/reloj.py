from abc import ABC, abstractmethod
from datetime import date, datetime


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> datetime:
        """Fecha y hora actuales en UTC."""

    @abstractmethod
    def hoy(self) -> date:
        """Fecha actual."""

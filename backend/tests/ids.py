"""Ids UUID deterministas para las pruebas.

``uid(1)`` siempre devuelve el mismo UUID, así que los tests mantienen valores
legibles sin depender de la numeración de una base.
"""

from __future__ import annotations

from uuid import UUID


def uid(numero: int) -> UUID:
    """UUID estable para el número dado (``uid(1)`` es ``0000…0001``)."""
    return UUID(int=numero)


def como_claim(valor: object) -> object:
    """Los claims del token viajan como texto; un valor que no es UUID pasa sin cambios."""
    return str(valor) if isinstance(valor, UUID) else valor

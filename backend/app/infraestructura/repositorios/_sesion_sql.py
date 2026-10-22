from sqlalchemy.orm import Session


def flush_aislado(sesion: Session, fila: object) -> None:
    """Agrega la fila y hace flush dentro de un SAVEPOINT.

    Si el flush falla, solo se revierte el SAVEPOINT y la sesion sigue usable.
    """
    with sesion.begin_nested():
        sesion.add(fila)
        sesion.flush()

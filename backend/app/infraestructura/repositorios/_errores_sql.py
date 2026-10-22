from sqlalchemy.exc import IntegrityError


def nombre_de_restriccion(error: IntegrityError) -> str | None:
    """Nombre de la restriccion violada, segun el diagnostico de PostgreSQL."""
    diagnostico = getattr(error.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None)

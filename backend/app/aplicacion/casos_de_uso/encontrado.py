from app.dominio.errores import NoEncontrado


def exigir_encontrado[T](entidad: T | None, descripcion: str) -> T:
    """Devuelve la entidad o lanza NoEncontrado ("No existe <descripcion>")."""
    if entidad is None:
        raise NoEncontrado(f"No existe {descripcion}")
    return entidad

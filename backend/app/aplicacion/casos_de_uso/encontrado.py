from app.dominio.errores import NoEncontrado


def exigir_encontrado[T](entidad: T | None, descripcion: str) -> T:
    """Devuelve la entidad o lanza NoEncontrado ("No existe <descripcion>")."""
    if entidad is None:
        raise NoEncontrado(f"No existe {descripcion}")
    return entidad


def exigir_conductor[T](conductor: T | None, id_conductor: int) -> T:
    return exigir_encontrado(conductor, f"el conductor {id_conductor}")


def exigir_vehiculo[T](vehiculo: T | None, id_conductor: int, id_vehiculo: int) -> T:
    return exigir_encontrado(vehiculo, f"el vehiculo {id_vehiculo} del conductor {id_conductor}")

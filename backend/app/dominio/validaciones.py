from app.dominio.errores import DatosInvalidos


def exigir_texto(campo: str, valor: str) -> None:
    if not valor.strip():
        raise DatosInvalidos(f"El campo {campo} es obligatorio")

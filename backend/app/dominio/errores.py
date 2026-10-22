class ErrorDeDominio(Exception):
    """Base de los errores del dominio."""


class NoEncontrado(ErrorDeDominio):
    pass


class DniDuplicado(ErrorDeDominio):
    pass


class PatenteDuplicada(ErrorDeDominio):
    pass


class TransicionInvalida(ErrorDeDominio):
    pass


class LicenciaVigenteRequerida(ErrorDeDominio):
    pass


class DatosInvalidos(ErrorDeDominio):
    pass

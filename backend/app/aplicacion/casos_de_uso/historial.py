from app.dominio.habilitacion import EventoHabilitacion


def en_orden_cronologico(eventos: list[EventoHabilitacion]) -> list[EventoHabilitacion]:
    # sorted es estable: ante fechas iguales se mantiene el orden de registro.
    return sorted(eventos, key=lambda evento: evento.fecha)

"""Validacion de un evento capturado en el formulario, antes de escribirlo
en la Planilla S@MI. Misma filosofia que `validate_and_clean_data()` de
Analisis-Python.1 (ningun dato incompleto llega a los calculos de SLA), pero
aplicada a una sola captura en vivo: en vez de descartar filas de un CSV
cargado en bloque, se bloquea el envio y se muestra al analista exactamente
que falta corregir."""

from dataclasses import dataclass
from datetime import datetime


DURACION_MAXIMA_HORAS = 24 * 31  # una plataforma no puede estar caida mas de un mes


@dataclass
class EventoPayload:
    dispositivo: str
    analista: str
    ticket: str
    descripcion: str
    inicio: datetime | None
    causa: str
    areas: str
    solucion: str
    fin: datetime | None
    acceso_tigo: str = ""
    ticket_tigo_une: str = ""


def validate_event(payload: EventoPayload, device_label: str = "Dispositivo") -> list[str]:
    """Retorna la lista de errores encontrados. Lista vacia = evento valido."""
    errors: list[str] = []

    if not payload.dispositivo or not payload.dispositivo.strip():
        errors.append(f"{device_label} no puede estar vacio.")
    if not payload.analista or not payload.analista.strip():
        errors.append("Analista es obligatorio.")
    if not payload.ticket or not payload.ticket.strip():
        errors.append("Numero de Ticket es obligatorio.")
    if not payload.causa or not payload.causa.strip():
        errors.append("Causa es obligatoria.")
    if not payload.areas or not payload.areas.strip():
        errors.append("Areas Involucradas es obligatorio.")
    if not payload.solucion or not payload.solucion.strip():
        errors.append("Solucion es obligatoria (describe como se restablecio el servicio).")

    if payload.inicio is None:
        errors.append("Fecha/Hora Inicio Evento es obligatoria.")
    if payload.fin is None:
        errors.append("Fecha/Hora Fin Evento es obligatoria.")

    if payload.inicio is not None and payload.fin is not None:
        if payload.fin < payload.inicio:
            errors.append(
                "Fecha/Hora Fin Evento no puede ser anterior a Fecha/Hora Inicio Evento."
            )
        else:
            duracion_horas = (payload.fin - payload.inicio).total_seconds() / 3600
            if duracion_horas > DURACION_MAXIMA_HORAS:
                errors.append(
                    f"La duracion del evento ({duracion_horas:.1f} h) supera el maximo "
                    f"esperado de {DURACION_MAXIMA_HORAS} h. Verifica las fechas."
                )

    return errors

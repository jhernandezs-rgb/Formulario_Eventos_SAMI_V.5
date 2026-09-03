"""Estandar de nombramiento del archivo exporter de Nagios / monitoreo de
disponibilidad: `avail_<mes>_<anio>.<extension>`, por ejemplo
`avail_julio_2026.xlsx`. Mes siempre en español, minusculas y sin tildes."""

import re
import unicodedata

from monitoreo_schema import MESES

_PATRON = re.compile(r"^avail_([a-z]+)_(\d{4})\.(xlsx|csv)$")


def _sin_tildes(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar_mes(mes: str) -> str:
    return _sin_tildes(mes.strip().lower())


def nombre_archivo_avail(mes: str, anio: int, extension: str = "xlsx") -> str:
    """Construye el nombre estandar avail_mes_anio.ext. Lanza ValueError si
    el mes no es un mes valido en español o la extension no es xlsx/csv."""
    mes_normalizado = normalizar_mes(mes)
    if mes_normalizado not in MESES:
        raise ValueError(
            f"'{mes}' no es un mes valido. Debe ser uno de: {', '.join(MESES)}"
        )
    if extension not in ("xlsx", "csv"):
        raise ValueError("La extension debe ser 'xlsx' o 'csv'")
    return f"avail_{mes_normalizado}_{anio}.{extension}"


def es_nombre_valido(nombre_archivo: str) -> bool:
    """Verifica si un nombre de archivo ya sigue el estandar
    avail_mes_anio.xlsx / .csv (mes en español, sin tildes, minusculas)."""
    match = _PATRON.match(nombre_archivo.strip())
    if not match:
        return False
    mes = match.group(1)
    return mes in MESES


def descomponer_nombre(nombre_archivo: str) -> tuple[str, int] | None:
    """Si el nombre sigue el estandar, retorna (mes, anio). Si no, None."""
    match = _PATRON.match(nombre_archivo.strip())
    if not match or match.group(1) not in MESES:
        return None
    return match.group(1), int(match.group(2))

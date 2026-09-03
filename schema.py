"""Definicion de la estructura real de cada hoja de la Planilla Control de
Eventos S@MI, obtenida inspeccionando el archivo de origen. Cada hoja de
plataforma comparte el mismo patron: fila 1 = titulo, fila 2 = encabezados,
fila 3 en adelante = eventos (con formulas de Tiempo Total / Minutos / Horas
ya cargadas en cada fila, referenciando las columnas de fecha)."""

from dataclasses import dataclass, field


HEADER_ROW = 2
FIRST_DATA_ROW = 3


@dataclass(frozen=True)
class PlatformSchema:
    sheet: str
    device_label: str  # "Dispositivo" o "Elemento" segun la hoja
    has_tigo: bool  # hojas Telecomunicaciones e Internet tienen 2 columnas extra

    @property
    def columns(self) -> dict:
        """Mapa nombre_logico -> letra de columna para esta hoja."""
        if self.has_tigo:
            return {
                "item": "A",
                "device": "B",
                "analista": "C",
                "ticket": "D",
                "acceso_tigo": "E",
                "ticket_tigo_une": "F",
                "descripcion": "G",
                "inicio": "H",
                "causa": "I",
                "areas": "J",
                "solucion": "K",
                "fin": "L",
                "tiempo_total": "M",
                "tiempo_minutos": "N",
                "tiempo_horas": "O",
            }
        return {
            "item": "A",
            "device": "B",
            "analista": "C",
            "ticket": "D",
            "descripcion": "E",
            "inicio": "F",
            "causa": "G",
            "areas": "H",
            "solucion": "I",
            "fin": "J",
            "tiempo_total": "K",
            "tiempo_minutos": "L",
            "tiempo_horas": "M",
        }


# Nombre de pestaña -> definicion de columnas.
PLATFORMS: dict[str, PlatformSchema] = {
    "Telecomunicaciones": PlatformSchema("Telecomunicaciones", "Dispositivo", True),
    "Telefonia": PlatformSchema("Telefonia", "Dispositivo", False),
    "Seguridad Informatica": PlatformSchema("Seguridad Informatica", "Dispositivo", False),
    "Servidores": PlatformSchema("Servidores", "Dispositivo", False),
    "Correo": PlatformSchema("Correo", "Elemento", False),
    "Internet": PlatformSchema("Internet", "Dispositivo", True),
    "Portales": PlatformSchema("Portales", "Dispositivo", False),
    "SAP": PlatformSchema("SAP", "Dispositivo", False),
    "Intranet": PlatformSchema("Intranet", "Elemento", False),
    "Data Center": PlatformSchema("Data Center", "Dispositivo", False),
}

# Nombre de pestaña -> fila donde la hoja "Resumen" registra el numero de
# dispositivos y el total de horas del mes para esa plataforma. "Data Center"
# no tiene fila en Resumen en el archivo de origen (no se incluye en el
# calculo de disponibilidad global del libro).
RESUMEN_ROWS: dict[str, int] = {
    "Telecomunicaciones": 5,
    "Telefonia": 10,
    "Seguridad Informatica": 15,
    "Servidores": 20,
    "Internet": 25,
    "Portales": 30,
    "SAP": 35,
    "Correo": 40,
    "Intranet": 45,
}

SLA_OBJETIVO = 98.0

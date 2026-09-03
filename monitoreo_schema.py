"""Modelo de datos del monitoreo de disponibilidad tipo Nagios: el mismo
esquema de columnas que usa `avail.csv` en Analisis-Python.1-v3.0-BETA
(HOST_NAME, PERCENT_TOTAL_TIME_UP, PERCENT_TOTAL_TIME_DOWN, ...), mas dos
columnas propias de esta herramienta (Categoria y Causa) para poder agrupar
por plataforma y excluir del SLA las caidas por causas externas, igual que
en la revision de la Planilla S@MI.

Supuesto (sin confirmar por el usuario): un archivo de monitoreo = un mes
completo, con todos los dispositivos de todas las categorias en una sola
hoja. "Portales" es una Categoria mas dentro de ese mismo archivo, no un
archivo separado. Si el estandar real separa un archivo por plataforma,
ajustar aqui."""

from dataclasses import dataclass

SLA_OBJETIVO = 98.0

CATEGORIAS = [
    "Telecomunicaciones",
    "Telefonia",
    "Seguridad Informatica",
    "Servidores",
    "Correo",
    "Internet",
    "Portales",
    "SAP",
    "Intranet",
    "Data Center",
    "Bases de Datos",
    "Almacenamiento",
]

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

HOJA_DISPONIBILIDAD = "Disponibilidad"

# Columna logica -> encabezado en la hoja. El orden aqui es el orden real
# de columnas en el archivo.
COLUMNAS = {
    "categoria": "Categoria",
    "host_name": "HOST_NAME",
    "causa": "Causa (si esta caido)",
    "no_controlado": "No controlado (excluir del SLA)",
    "percent_up": "PERCENT_TOTAL_TIME_UP",
    "percent_down": "PERCENT_TOTAL_TIME_DOWN",
    "percent_unreachable": "PERCENT_TOTAL_TIME_UNREACHABLE",
    "percent_undetermined": "PERCENT_TOTAL_TIME_UNDETERMINED",
    "total_time_down": "TOTAL_TIME_DOWN",
}

ENCABEZADOS = list(COLUMNAS.values())


@dataclass
class DispositivoPayload:
    categoria: str
    host_name: str
    percent_up: float
    percent_down: float
    causa: str = ""
    no_controlado: bool = False
    percent_unreachable: float = 0.0
    percent_undetermined: float = 0.0
    total_time_down: float = 0.0

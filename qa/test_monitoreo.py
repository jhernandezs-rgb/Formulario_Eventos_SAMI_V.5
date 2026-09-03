import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest

from monitoreo_io import (
    agregar_dispositivo,
    cargar_libro_monitoreo,
    dispositivos_caidos,
    leer_dispositivos,
    nuevo_libro_monitoreo,
)
from monitoreo_naming import (
    descomponer_nombre,
    es_nombre_valido,
    nombre_archivo_avail,
    normalizar_mes,
)
from monitoreo_pdf import build_pdf_dispositivos_caidos
from monitoreo_schema import COLUMNAS, DispositivoPayload
from monitoreo_validation import validate_dispositivo


class TestNombreArchivoAvail:
    def test_nombre_estandar_se_construye_correctamente(self):
        assert nombre_archivo_avail("Julio", 2026) == "avail_julio_2026.xlsx"

    def test_normaliza_tildes_y_mayusculas(self):
        assert nombre_archivo_avail("Diciembre", 2025) == "avail_diciembre_2025.xlsx"
        assert normalizar_mes(" JULIO ") == "julio"

    def test_extension_csv(self):
        assert nombre_archivo_avail("marzo", 2026, "csv") == "avail_marzo_2026.csv"

    def test_mes_invalido_lanza_error(self):
        with pytest.raises(ValueError):
            nombre_archivo_avail("mes_inventado", 2026)

    def test_extension_invalida_lanza_error(self):
        with pytest.raises(ValueError):
            nombre_archivo_avail("julio", 2026, "docx")

    def test_es_nombre_valido_acepta_estandar(self):
        assert es_nombre_valido("avail_julio_2026.xlsx") is True

    def test_es_nombre_valido_rechaza_otros_formatos(self):
        assert es_nombre_valido("Planilla Julio 2026.xlsx") is False
        assert es_nombre_valido("avail_2026.xlsx") is False
        assert es_nombre_valido("avail_julio2026.xlsx") is False

    def test_descomponer_nombre_extrae_mes_y_anio(self):
        assert descomponer_nombre("avail_julio_2026.xlsx") == ("julio", 2026)

    def test_descomponer_nombre_none_si_no_es_estandar(self):
        assert descomponer_nombre("otro_archivo.xlsx") is None


class TestValidateDispositivo:
    def test_dispositivo_valido_sin_caida_no_genera_errores(self):
        payload = DispositivoPayload(
            categoria="Servidores", host_name="srv01", percent_up=100.0, percent_down=0.0
        )
        assert validate_dispositivo(payload) == []

    def test_dispositivo_con_caida_y_causa_no_genera_errores(self):
        payload = DispositivoPayload(
            categoria="Servidores", host_name="srv01", percent_up=99.5, percent_down=0.5,
            causa="Mantenimiento programado",
        )
        assert validate_dispositivo(payload) == []

    def test_host_name_vacio_es_error(self):
        payload = DispositivoPayload(categoria="Servidores", host_name="", percent_up=100, percent_down=0)
        errors = validate_dispositivo(payload)
        assert any("HOST_NAME" in e for e in errors)

    def test_porcentaje_fuera_de_rango_es_error(self):
        payload = DispositivoPayload(categoria="Servidores", host_name="srv01", percent_up=150, percent_down=0)
        errors = validate_dispositivo(payload)
        assert any("PERCENT_TOTAL_TIME_UP" in e for e in errors)

    def test_suma_up_down_mayor_a_105_es_error(self):
        payload = DispositivoPayload(categoria="Servidores", host_name="srv01", percent_up=80, percent_down=80)
        errors = validate_dispositivo(payload)
        assert any("105" in e for e in errors)

    def test_caida_sin_causa_es_error(self):
        payload = DispositivoPayload(categoria="Servidores", host_name="srv01", percent_up=90, percent_down=10, causa="")
        errors = validate_dispositivo(payload)
        assert any("Causa" in e for e in errors)

    def test_caida_con_causa_no_genera_error_de_causa(self):
        payload = DispositivoPayload(
            categoria="Servidores", host_name="srv01", percent_up=90, percent_down=10, causa="Falla electrica"
        )
        errors = validate_dispositivo(payload)
        assert not any("Causa" in e for e in errors)


class TestMonitoreoIO:
    def test_nuevo_libro_tiene_encabezados(self):
        wb = nuevo_libro_monitoreo()
        ws = wb["Disponibilidad"]
        assert ws.cell(row=1, column=1).value == COLUMNAS["categoria"]

    def test_agregar_y_leer_dispositivo(self):
        wb = nuevo_libro_monitoreo()
        payload = DispositivoPayload(
            categoria="Portales", host_name="https://portal.test", percent_up=97.0, percent_down=3.0,
            causa="Suspendido", no_controlado=False,
        )
        agregar_dispositivo(wb, payload)
        dispositivos = leer_dispositivos(wb)
        assert len(dispositivos) == 1
        assert dispositivos[0][COLUMNAS["host_name"]] == "https://portal.test"
        assert dispositivos[0][COLUMNAS["percent_up"]] == 97.0

    def test_libro_guardado_y_recargado_conserva_datos(self):
        from io import BytesIO

        wb = nuevo_libro_monitoreo()
        agregar_dispositivo(
            wb,
            DispositivoPayload(categoria="Servidores", host_name="srv01", percent_up=99.9, percent_down=0.1),
        )
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        wb2 = cargar_libro_monitoreo(buffer)
        dispositivos = leer_dispositivos(wb2)
        assert len(dispositivos) == 1
        assert dispositivos[0][COLUMNAS["host_name"]] == "srv01"

    def test_dispositivos_caidos_separa_total_y_ajustado(self):
        dispositivos = [
            {COLUMNAS["percent_up"]: 90.0, COLUMNAS["no_controlado"]: "NO", COLUMNAS["categoria"]: "Servidores"},
            {COLUMNAS["percent_up"]: 85.0, COLUMNAS["no_controlado"]: "SI", COLUMNAS["categoria"]: "Telecomunicaciones"},
            {COLUMNAS["percent_up"]: 99.9, COLUMNAS["no_controlado"]: "NO", COLUMNAS["categoria"]: "SAP"},
        ]
        resultado = dispositivos_caidos(dispositivos, umbral=98.0)
        assert len(resultado["total"]) == 2
        assert len(resultado["ajustado"]) == 1
        assert len(resultado["excluidos"]) == 1


class TestMonitoreoPdf:
    def test_pdf_se_genera_sin_dispositivos(self):
        caidos = {"total": [], "ajustado": [], "excluidos": []}
        pdf_bytes = build_pdf_dispositivos_caidos(caidos, periodo="Julio 2026")
        assert pdf_bytes.startswith(b"%PDF")

    def test_pdf_se_genera_con_dispositivos(self):
        caidos = {
            "total": [{
                COLUMNAS["categoria"]: "Servidores", COLUMNAS["host_name"]: "srv01",
                COLUMNAS["percent_up"]: 90.0, COLUMNAS["percent_down"]: 10.0,
                COLUMNAS["causa"]: "Falla de disco", COLUMNAS["no_controlado"]: "NO",
            }],
            "ajustado": [{
                COLUMNAS["categoria"]: "Servidores", COLUMNAS["host_name"]: "srv01",
                COLUMNAS["percent_up"]: 90.0, COLUMNAS["percent_down"]: 10.0,
                COLUMNAS["causa"]: "Falla de disco", COLUMNAS["no_controlado"]: "NO",
            }],
            "excluidos": [],
        }
        pdf_bytes = build_pdf_dispositivos_caidos(caidos, periodo="Julio 2026")
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

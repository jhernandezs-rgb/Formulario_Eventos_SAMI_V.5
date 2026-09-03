import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from schema import PLATFORMS
from validation import EventoPayload
from workbook_io import (
    append_event,
    clean_analista_name,
    compute_disponibilidad,
    compute_downtime_hours,
    load_lookups,
    load_resumen_baseline,
    load_workbook_for_write,
)

SOURCE = Path(__file__).parents[1] / "sami_source_reparado.xlsx"


def _fresh_workbook():
    return load_workbook_for_write(SOURCE)


class TestCleanAnalistaName:
    def test_quita_turno_con_espacio_antes_de_la_barra(self):
        assert clean_analista_name("Anderson Garcia Cataño / 06:00 - 14:00") == "Anderson Garcia Cataño"

    def test_quita_turno_sin_espacio_antes_de_la_barra(self):
        assert clean_analista_name(" Roman Echavarría Meneses/ 06:00 - 14:00") == "Roman Echavarría Meneses"

    def test_nombre_sin_turno_queda_igual(self):
        assert clean_analista_name("Nombre Nuevo") == "Nombre Nuevo"

    def test_vacio_da_vacio(self):
        assert clean_analista_name("") == ""


class TestLookups:
    def test_lookups_no_estan_vacios(self):
        wb = _fresh_workbook()
        lookups = load_lookups(wb)
        assert lookups["analistas"], "No se encontraron analistas en Hoja1"
        assert lookups["areas"], "No se encontraron areas en Hoja1"
        assert lookups["causas"], "No se encontraron causas en Hoja1"

    def test_analistas_no_incluyen_el_turno(self):
        wb = _fresh_workbook()
        lookups = load_lookups(wb)
        assert all("/" not in nombre for nombre in lookups["analistas"])

    def test_analistas_estan_deduplicados_entre_turnos(self):
        # La misma persona aparece en la hoja una vez por cada turno que
        # cubre (mañana/tarde/noche); limpiar el turno debe dejar un solo
        # nombre por persona.
        wb = _fresh_workbook()
        lookups = load_lookups(wb)
        assert len(lookups["analistas"]) == len(set(lookups["analistas"]))


class TestResumenBaseline:
    def test_telecomunicaciones_tiene_baseline(self):
        wb = _fresh_workbook()
        baseline = load_resumen_baseline(wb, "Telecomunicaciones")
        assert baseline is not None
        assert baseline["dispositivos"] > 0
        assert baseline["total_horas_mes"] == baseline["dispositivos"] * baseline["dias_mes"] * 24

    def test_data_center_no_tiene_fila_en_resumen(self):
        wb = _fresh_workbook()
        assert load_resumen_baseline(wb, "Data Center") is None


class TestAppendEvent:
    def test_evento_nuevo_ocupa_una_fila_placeholder(self):
        wb = _fresh_workbook()
        schema = PLATFORMS["SAP"]
        ws = wb[schema.sheet]
        before_downtime, before_count = compute_downtime_hours(ws, schema)

        payload = EventoPayload(
            dispositivo="Servidor SAP QA",
            analista="Julian / 06:00 - 14:00",
            ticket="IM-9999",
            descripcion="Prueba QA",
            inicio=datetime(2026, 7, 15, 8, 0),
            causa="Bloqueo",
            areas="SERVIDORES",
            solucion="Reinicio controlado",
            fin=datetime(2026, 7, 15, 8, 30),
        )
        row = append_event(wb, "SAP", payload)
        assert ws.cell(row=row, column=2).value == "Servidor SAP QA"

        after_downtime, after_count = compute_downtime_hours(ws, schema)
        assert after_count == before_count + 1
        assert after_downtime > before_downtime

    def test_evento_con_tigo_escribe_columnas_extra(self):
        wb = _fresh_workbook()
        payload = EventoPayload(
            dispositivo="Router Test",
            analista="Julian / 06:00 - 14:00",
            ticket="IM-8888",
            descripcion="Prueba QA TIGO",
            inicio=datetime(2026, 7, 15, 9, 0),
            causa="Falla electrica",
            areas="TELECOMUNICACIONES",
            solucion="Se restablecio el fluido electrico",
            fin=datetime(2026, 7, 15, 9, 45),
            acceso_tigo="Fibra 1",
            ticket_tigo_une="TU-123",
        )
        row = append_event(wb, "Telecomunicaciones", payload)
        ws = wb["Telecomunicaciones"]
        assert ws.cell(row=row, column=5).value == "Fibra 1"
        assert ws.cell(row=row, column=6).value == "TU-123"


class TestGuardadoRepetido:
    def test_wb_save_se_puede_llamar_varias_veces(self):
        """Streamlit vuelve a ejecutar el script en cada interaccion, y el
        boton de descarga llama a wb.save() en cada rerender. Debe poder
        invocarse repetidamente sobre el mismo objeto sin lanzar excepcion."""
        wb = _fresh_workbook()
        for _ in range(3):
            buffer = BytesIO()
            wb.save(buffer)
            assert buffer.getvalue()


class TestDisponibilidad:
    def test_disponibilidad_100_sin_caidas(self):
        assert compute_disponibilidad(1000, 0) == 100.0

    def test_disponibilidad_baja_con_caida_alta(self):
        assert compute_disponibilidad(1000, 500) == 50.0

    def test_total_horas_cero_no_lanza_error(self):
        assert compute_disponibilidad(0, 10) == 0.0


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

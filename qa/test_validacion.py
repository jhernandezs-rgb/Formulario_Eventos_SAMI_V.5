from datetime import datetime

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from validation import EventoPayload, validate_event


def _valid_payload(**overrides) -> EventoPayload:
    base = dict(
        dispositivo="Sw_Test",
        analista="Julian / 06:00 - 14:00",
        ticket="IM-0001",
        descripcion="Descripcion",
        inicio=datetime(2026, 7, 1, 8, 0),
        causa="Bloqueo de Sw",
        areas="TELECOMUNICACIONES",
        solucion="Se reinicio el equipo.",
        fin=datetime(2026, 7, 1, 8, 30),
    )
    base.update(overrides)
    return EventoPayload(**base)


class TestCamposObligatorios:
    def test_evento_valido_no_genera_errores(self):
        assert validate_event(_valid_payload()) == []

    def test_dispositivo_vacio_es_error(self):
        errors = validate_event(_valid_payload(dispositivo="  "))
        assert any("no puede estar vacio" in e for e in errors)

    def test_analista_vacio_es_error(self):
        errors = validate_event(_valid_payload(analista=""))
        assert any("Analista" in e for e in errors)

    def test_ticket_vacio_es_error(self):
        errors = validate_event(_valid_payload(ticket=""))
        assert any("Ticket" in e for e in errors)

    def test_causa_vacia_es_error(self):
        errors = validate_event(_valid_payload(causa=""))
        assert any("Causa" in e for e in errors)

    def test_areas_vacias_es_error(self):
        errors = validate_event(_valid_payload(areas=""))
        assert any("Areas" in e for e in errors)

    def test_solucion_vacia_es_error(self):
        errors = validate_event(_valid_payload(solucion=""))
        assert any("Solucion" in e for e in errors)

    def test_fechas_faltantes_son_error(self):
        errors = validate_event(_valid_payload(inicio=None, fin=None))
        assert any("Inicio" in e for e in errors)
        assert any("Fin" in e for e in errors)


class TestConsistenciaCronologica:
    def test_fin_anterior_a_inicio_es_error(self):
        errors = validate_event(
            _valid_payload(inicio=datetime(2026, 7, 1, 10, 0), fin=datetime(2026, 7, 1, 9, 0))
        )
        assert any("no puede ser anterior" in e for e in errors)

    def test_duracion_excesiva_es_error(self):
        errors = validate_event(
            _valid_payload(inicio=datetime(2026, 1, 1, 0, 0), fin=datetime(2026, 7, 1, 0, 0))
        )
        assert any("supera el maximo" in e for e in errors)

    def test_duracion_igual_a_cero_es_valida(self):
        same = datetime(2026, 7, 1, 8, 0)
        errors = validate_event(_valid_payload(inicio=same, fin=same))
        assert errors == []


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

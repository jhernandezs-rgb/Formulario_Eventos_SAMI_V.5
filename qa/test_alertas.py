import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1]))

import pytest

from alertas import (
    AlertaSLA,
    ConfiguracionFaltante,
    config_correo_disponible,
    config_webhook_disponible,
    enviar_correo,
    enviar_webhook,
    evaluar_alertas,
)


class TestEvaluarAlertas:
    def test_plataforma_por_debajo_de_la_meta_genera_alerta(self):
        resultados = {"Telecomunicaciones": {"disponibilidad": 95.0, "horas_caida": 10.0}}
        alertas = evaluar_alertas(resultados, meta=98.0)
        assert len(alertas) == 1
        assert alertas[0].plataforma == "Telecomunicaciones"
        assert "SLA en riesgo" in alertas[0].mensaje

    def test_plataforma_sobre_la_meta_no_genera_alerta(self):
        resultados = {"SAP": {"disponibilidad": 99.5, "horas_caida": 1.0}}
        assert evaluar_alertas(resultados, meta=98.0) == []

    def test_disponibilidad_faltante_se_ignora(self):
        resultados = {"Correo": {"horas_caida": 5.0}}
        assert evaluar_alertas(resultados, meta=98.0) == []

    def test_varias_plataformas_mixtas(self):
        resultados = {
            "A": {"disponibilidad": 90.0, "horas_caida": 20.0},
            "B": {"disponibilidad": 99.9, "horas_caida": 0.1},
        }
        alertas = evaluar_alertas(resultados, meta=98.0)
        assert len(alertas) == 1
        assert alertas[0].plataforma == "A"


class TestConfigDisponible:
    def test_config_correo_incompleta_retorna_false(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        assert config_correo_disponible() is False

    def test_config_correo_completa_retorna_true(self, monkeypatch):
        for var, val in [
            ("SMTP_HOST", "smtp.test"), ("SMTP_PORT", "587"), ("SMTP_USER", "u"),
            ("SMTP_PASSWORD", "p"), ("SMTP_FROM", "alertas@test.com"),
        ]:
            monkeypatch.setenv(var, val)
        assert config_correo_disponible() is True

    def test_config_webhook_ausente_retorna_false(self, monkeypatch):
        monkeypatch.delenv("ALERTAS_WEBHOOK_URL", raising=False)
        assert config_webhook_disponible() is False

    def test_config_webhook_presente_retorna_true(self, monkeypatch):
        monkeypatch.setenv("ALERTAS_WEBHOOK_URL", "https://example.com/webhook")
        assert config_webhook_disponible() is True


class TestEnviarCorreo:
    def test_sin_configuracion_lanza_configuracion_faltante(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        with pytest.raises(ConfiguracionFaltante):
            enviar_correo(["a@test.com"], "Asunto", "Cuerpo")

    def test_con_configuracion_llama_a_smtp(self, monkeypatch):
        for var, val in [
            ("SMTP_HOST", "smtp.test"), ("SMTP_PORT", "587"), ("SMTP_USER", "u"),
            ("SMTP_PASSWORD", "p"), ("SMTP_FROM", "alertas@test.com"),
        ]:
            monkeypatch.setenv(var, val)

        with patch("alertas.smtplib.SMTP") as smtp_mock:
            instancia = MagicMock()
            smtp_mock.return_value.__enter__.return_value = instancia
            enviar_correo(["destino@test.com"], "Asunto", "Cuerpo")

        smtp_mock.assert_called_once_with("smtp.test", 587, timeout=15)
        instancia.starttls.assert_called_once()
        instancia.login.assert_called_once_with("u", "p")
        instancia.sendmail.assert_called_once()


class TestEnviarWebhook:
    def test_sin_configuracion_lanza_configuracion_faltante(self, monkeypatch):
        monkeypatch.delenv("ALERTAS_WEBHOOK_URL", raising=False)
        with pytest.raises(ConfiguracionFaltante):
            enviar_webhook("mensaje de prueba")

    def test_con_url_explicita_llama_a_requests_post(self):
        with patch("alertas.requests.post") as post_mock:
            respuesta = MagicMock()
            post_mock.return_value = respuesta
            enviar_webhook("mensaje de prueba", webhook_url="https://example.com/webhook")

        post_mock.assert_called_once_with(
            "https://example.com/webhook", json={"text": "mensaje de prueba"}, timeout=15
        )
        respuesta.raise_for_status.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

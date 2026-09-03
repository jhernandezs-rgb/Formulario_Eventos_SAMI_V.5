import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from auth import proteccion_activa, verificar_clave


class TestProteccionActiva:
    def test_sin_clave_configurada_no_hay_proteccion(self, monkeypatch):
        monkeypatch.delenv("PORTAL_PASSWORD", raising=False)
        assert proteccion_activa() is False

    def test_con_clave_configurada_hay_proteccion(self, monkeypatch):
        monkeypatch.setenv("PORTAL_PASSWORD", "clave123")
        assert proteccion_activa() is True

    def test_clave_vacia_no_cuenta_como_configurada(self, monkeypatch):
        monkeypatch.setenv("PORTAL_PASSWORD", "   ")
        assert proteccion_activa() is False


class TestVerificarClave:
    def test_sin_clave_configurada_cualquier_valor_pasa(self, monkeypatch):
        monkeypatch.delenv("PORTAL_PASSWORD", raising=False)
        assert verificar_clave("lo que sea") is True
        assert verificar_clave("") is True

    def test_clave_correcta_pasa(self, monkeypatch):
        monkeypatch.setenv("PORTAL_PASSWORD", "clave123")
        assert verificar_clave("clave123") is True

    def test_clave_incorrecta_no_pasa(self, monkeypatch):
        monkeypatch.setenv("PORTAL_PASSWORD", "clave123")
        assert verificar_clave("otra_clave") is False

    def test_clave_vacia_no_pasa_si_hay_una_configurada(self, monkeypatch):
        monkeypatch.setenv("PORTAL_PASSWORD", "clave123")
        assert verificar_clave("") is False


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

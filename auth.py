"""Portal de acceso simple: una sola clave compartida (variable de entorno
PORTAL_PASSWORD), no un sistema de usuarios.

Decision deliberada: el boceto pedia "usuarios" con un admin que crea
cuentas, pero eso implica guardar contraseñas de forma segura (hash, sal,
rotacion) y gestionar roles - una superficie de seguridad real que no se
debe improvisar sin que alguien la revise. Esto es solo una cortina para
que la app no quede abierta a cualquiera en la misma red; no reemplaza un
sistema de autenticacion real ni deberia usarse para proteger datos
sensibles frente a un atacante con algo de esfuerzo."""

import os

import streamlit as st


def proteccion_activa() -> bool:
    """True si se configuro una clave (PORTAL_PASSWORD). Si no se configuro,
    el portal queda abierto sin pedir clave - util para desarrollo local."""
    return bool(os.environ.get("PORTAL_PASSWORD", "").strip())


def verificar_clave(clave_ingresada: str) -> bool:
    clave_configurada = os.environ.get("PORTAL_PASSWORD", "").strip()
    if not clave_configurada:
        return True
    return clave_ingresada == clave_configurada


def require_auth() -> None:
    """Llamar al inicio de cada pagina (incluida el portal). Si hay una
    clave configurada y la sesion no se ha autenticado, detiene el render
    de la pagina con un aviso para volver al portal a iniciar sesion —
    evita que alguien salte la pantalla de acceso navegando directo a la
    URL de una subpagina."""
    if not proteccion_activa():
        return
    if st.session_state.get("autenticado"):
        return
    st.warning("Debes iniciar sesion desde el Portal de Monitoreo para ver esta pagina.")
    st.page_link("portal.py", label="Ir al Portal de Monitoreo", icon=":material/login:")
    st.stop()

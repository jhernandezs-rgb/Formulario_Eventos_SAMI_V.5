"""Portal de Monitoreo: pantalla de entrada con acceso simple (una clave
compartida, ver auth.py) y un menu de tarjetas hacia las tres herramientas.
No es un sistema de usuarios: es una cortina de acceso, no autenticacion
real. Ver auth.py para el porque de esa decision."""

import streamlit as st

from auth import proteccion_activa, verificar_clave
from theme import card_html, inject_theme

st.set_page_config(page_title="Portal de Monitoreo", page_icon="🛰️", layout="wide")
inject_theme()

st.session_state.setdefault("autenticado", False)


def _pantalla_login() -> None:
    st.html("<div style='height:6vh'></div>")
    _, centro, _ = st.columns([1, 1.1, 1])
    with centro:
        st.html(
            "<div style='text-align:center; font-size:42px; margin-bottom:4px;'>🛰️</div>"
            "<h1 style='text-align:center; margin-bottom:4px;'>Portal de Monitoreo</h1>"
            "<p style='text-align:center; color:var(--portal-ink-soft); margin-top:0;'>"
            "Disponibilidad de infraestructura · S@MI y monitoreo Nagios</p>"
        )
        with st.container(border=True):
            with st.form("login_form"):
                clave = st.text_input("Clave de acceso", type="password")
                entrar = st.form_submit_button("Ingresar", icon=":material/login:", width="stretch")
            if entrar:
                if verificar_clave(clave):
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("Clave incorrecta.")
        st.caption(
            "Acceso simple con una clave compartida (variable de entorno "
            "PORTAL_PASSWORD) — no es un sistema de usuarios ni reemplaza una "
            "autenticacion real. Ver DOCUMENTACION.md."
        )


def _menu_principal() -> None:
    st.html(
        "<h1 style='margin-bottom:2px;'>Menú de Monitoreo</h1>"
        "<p style='color:var(--portal-ink-soft); margin-top:0;'>"
        "Disponibilidad de infraestructura — meta de SLA: 98% o superior.</p>"
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.html(
            card_html(
                "Gestión Formulario S@MI",
                "Registra incidencias nuevas con validación en el momento.",
                "📝",
                "blue",
            )
        )
        st.page_link(
            "pages/1_Captura_de_Eventos.py", label="Abrir", icon=":material/arrow_forward:",
            width="stretch",
        )

    with col2:
        st.html(
            card_html(
                "Revisión Mensual S@MI",
                "Corrige el archivo del mes y clasifica causas no controladas.",
                "🔍",
                "green",
            )
        )
        st.page_link(
            "pages/2_Revisar_archivo_mensual.py", label="Abrir", icon=":material/arrow_forward:",
            width="stretch",
        )

    with col3:
        st.html(
            card_html(
                "Monitoreo Nagios",
                "Reporte tipo Nagios por dispositivo, PDF y alertas de SLA.",
                "📡",
                "orange",
            )
        )
        st.page_link(
            "pages/3_Monitoreo_Nagios.py", label="Abrir", icon=":material/arrow_forward:",
            width="stretch",
        )

    st.divider()
    if st.button("Cerrar sesión", icon=":material/logout:"):
        st.session_state.autenticado = False
        st.rerun()


if proteccion_activa() and not st.session_state.autenticado:
    _pantalla_login()
else:
    _menu_principal()

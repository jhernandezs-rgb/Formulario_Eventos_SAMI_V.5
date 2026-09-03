"""Tema visual compartido por todas las paginas: fondo oscuro, tarjetas con
acento de color y tipografia, inspirado en el boceto de "Portal de
Monitoreo" que trajo el usuario.

El fondo oscuro y el color de texto NO se fuerzan aqui por CSS: se definen
como el tema nativo de Streamlit en .streamlit/config.toml. Un intento
anterior pintaba el fondo con CSS crudo sin cambiar el tema real de
Streamlit, y los widgets nativos (botones, page_link) seguian usando sus
colores por defecto de tema claro - texto casi invisible sobre el fondo
oscuro. Con el tema nativo en dark, los widgets se ven correctamente y este
CSS solo agrega la tipografia y las tarjetas del menu."""

import streamlit as st

_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {
    --portal-bg: #0b1220;
    --portal-bg-soft: #101a2e;
    --portal-border: #24314f;
    --portal-ink: #e8edf7;
    --portal-ink-soft: #9fadc7;
    --portal-blue: #2563eb;
    --portal-green: #16a34a;
    --portal-orange: #d97706;
    --portal-purple: #7c3aed;
}

html, body {
    font-family: "Inter", ui-sans-serif, system-ui, sans-serif;
}

/* Los iconos de Streamlit dependen de su propia fuente de simbolos
   (Material Symbols); nunca se debe forzar font-family sobre ellos o el
   nombre del icono aparece como texto suelto en vez del glifo. */
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded" !important;
}

h1, h2, h3 {
    letter-spacing: -0.01em;
}

.portal-card {
    display: block;
    border-radius: 16px;
    padding: 22px 22px 20px;
    min-height: 168px;
    position: relative;
    color: white !important;
    text-decoration: none !important;
    box-shadow: 0 10px 30px -12px rgba(0,0,0,0.55);
    border: 1px solid rgba(255,255,255,0.08);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.portal-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 16px 36px -12px rgba(0,0,0,0.65);
}
.portal-card .portal-card-icon {
    font-size: 30px;
    margin-bottom: 14px;
    display: block;
}
.portal-card .portal-card-title {
    font-size: 17px;
    font-weight: 700;
    line-height: 1.25;
    display: block;
}
.portal-card .portal-card-desc {
    font-size: 12.5px;
    font-weight: 400;
    opacity: 0.88;
    margin-top: 6px;
    display: block;
}
.portal-card .portal-status {
    position: absolute;
    top: 16px;
    right: 18px;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    opacity: 0.85;
}
.portal-status .dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #4ade80;
    margin-right: 5px;
    box-shadow: 0 0 6px #4ade80;
}

.portal-card-blue   { background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%); }
.portal-card-green  { background: linear-gradient(135deg, #15803d 0%, #16a34a 100%); }
.portal-card-orange { background: linear-gradient(135deg, #b45309 0%, #d97706 100%); }
.portal-card-purple { background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%); }
</style>
"""


def inject_theme() -> None:
    # st.html() (no st.markdown) porque el CSS tiene lineas en blanco: el
    # parser de Markdown corta el bloque de HTML crudo en la primera linea
    # vacia y renderiza el resto como texto plano.
    st.html(_CSS)


def card_html(titulo: str, descripcion: str, icono: str, color: str) -> str:
    """`color` es uno de: blue, green, orange, purple."""
    return f"""
    <div class="portal-card portal-card-{color}">
        <span class="portal-status"><span class="dot"></span>Activo</span>
        <span class="portal-card-icon">{icono}</span>
        <span class="portal-card-title">{titulo}</span>
        <span class="portal-card-desc">{descripcion}</span>
    </div>
    """

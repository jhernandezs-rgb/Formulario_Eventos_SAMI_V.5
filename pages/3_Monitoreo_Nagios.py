"""Formulario de monitoreo de disponibilidad tipo Nagios: captura
dispositivos con su % de tiempo arriba/abajo (el mismo esquema que
avail.csv en Analisis-Python.1-v3.0-BETA), los guarda en un Excel con el
nombre estandar avail_<mes>_<anio>.xlsx, exporta un PDF de dispositivos
caidos, y permite disparar una alerta manual por correo o chat corporativo
cuando una plataforma esta por debajo de la meta de SLA.

Supuestos tomados sin confirmacion explicita del usuario (ajustar si no
aplican):
- Un archivo de monitoreo = un mes completo con todas las categorias
  (incluida "Portales") en una sola hoja, no un archivo por plataforma.
- El envio de alertas es siempre manual (boton), nunca automatico/
  desatendido; requiere que el usuario configure SMTP y/o un webhook
  (ver .env.example)."""

import sys
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from alertas import (  # noqa: E402
    ConfiguracionFaltante,
    config_correo_disponible,
    config_webhook_disponible,
    enviar_correo,
    enviar_webhook,
    evaluar_alertas,
)
from auth import require_auth  # noqa: E402
from monitoreo_io import (  # noqa: E402
    agregar_dispositivo,
    cargar_libro_monitoreo,
    dispositivos_caidos,
    leer_dispositivos,
    nuevo_libro_monitoreo,
    sugerir_no_controlado_dispositivo,
)
from monitoreo_naming import descomponer_nombre, es_nombre_valido, nombre_archivo_avail  # noqa: E402
from monitoreo_pdf import build_pdf_dispositivos_caidos  # noqa: E402
from monitoreo_schema import CATEGORIAS, COLUMNAS, MESES, SLA_OBJETIVO, DispositivoPayload  # noqa: E402
from monitoreo_validation import validate_dispositivo  # noqa: E402
from theme import inject_theme  # noqa: E402

st.set_page_config(page_title="Monitoreo de disponibilidad", page_icon="📡", layout="wide")
inject_theme()
require_auth()

st.sidebar.title("Monitoreo de disponibilidad")
st.sidebar.caption(
    "Formulario de captura tipo Nagios: un dispositivo por fila, con su % de "
    "tiempo arriba/abajo. Independiente de la Planilla S@MI."
)

mes = st.sidebar.selectbox("Mes", options=MESES, index=MESES.index("julio"))
anio = st.sidebar.number_input("Año", min_value=2000, max_value=2100, value=2026, step=1)
nombre_estandar = nombre_archivo_avail(mes, anio)
st.sidebar.caption(f"Nombre de archivo estandar: `{nombre_estandar}`")

uploaded = st.sidebar.file_uploader("Cargar archivo de monitoreo existente (.xlsx)", type=["xlsx"])

col_a, col_b = st.sidebar.columns(2)
crear_nuevo = col_a.button("Crear nuevo", icon=":material/note_add:")
cargar_subido = col_b.button("Cargar archivo", icon=":material/upload:", disabled=uploaded is None)

if crear_nuevo:
    st.session_state.wb_monitoreo = nuevo_libro_monitoreo()
    st.session_state.nombre_monitoreo = nombre_estandar
    st.session_state.dispositivos_sesion = []

if cargar_subido and uploaded is not None:
    st.session_state.wb_monitoreo = cargar_libro_monitoreo(BytesIO(uploaded.getvalue()))
    st.session_state.nombre_monitoreo = uploaded.name
    st.session_state.dispositivos_sesion = []

if "wb_monitoreo" not in st.session_state:
    st.session_state.wb_monitoreo = nuevo_libro_monitoreo()
    st.session_state.nombre_monitoreo = nombre_estandar
    st.session_state.dispositivos_sesion = []

wb = st.session_state.wb_monitoreo
nombre_actual = st.session_state.nombre_monitoreo

st.title("Captura de monitoreo de disponibilidad")
st.caption(f"Archivo actual: `{nombre_actual}`")

if not es_nombre_valido(nombre_actual):
    st.warning(
        f"⚠️ El nombre '{nombre_actual}' no sigue el estandar "
        f"`avail_<mes>_<año>.xlsx` (ej. `{nombre_estandar}`). Se puede seguir "
        "trabajando, pero al descargar se sugiere el nombre estandar."
    )
else:
    periodo_detectado = descomponer_nombre(nombre_actual)
    if periodo_detectado:
        mes, anio = periodo_detectado[0], periodo_detectado[1]

with st.form("form_dispositivo", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        categoria = st.selectbox("Categoria *", options=CATEGORIAS)
        es_portal = categoria == "Portales"
        host_name = st.text_input("URL del portal *" if es_portal else "Dispositivo (HOST_NAME) *")
        percent_up = st.number_input("PERCENT_TOTAL_TIME_UP (%) *", 0.0, 100.0, 100.0, 0.01)
        percent_down = st.number_input("PERCENT_TOTAL_TIME_DOWN (%) *", 0.0, 100.0, 0.0, 0.01)
    with col2:
        percent_unreachable = st.number_input("PERCENT_TOTAL_TIME_UNREACHABLE (%)", 0.0, 100.0, 0.0, 0.01)
        percent_undetermined = st.number_input("PERCENT_TOTAL_TIME_UNDETERMINED (%)", 0.0, 100.0, 0.0, 0.01)
        total_time_down = st.number_input("TOTAL_TIME_DOWN (segundos)", 0.0, value=0.0, step=60.0)
        causa = st.text_input("Causa (obligatoria si hay tiempo de caida)")
        no_controlado = st.checkbox(
            "No controlado (excluir del SLA, ej. falla electrica o de proveedor)"
        )

    submitted = st.form_submit_button("Agregar dispositivo", icon=":material/add:")

if submitted:
    payload = DispositivoPayload(
        categoria=categoria,
        host_name=host_name,
        percent_up=percent_up,
        percent_down=percent_down,
        causa=causa,
        no_controlado=no_controlado or sugerir_no_controlado_dispositivo(causa),
        percent_unreachable=percent_unreachable,
        percent_undetermined=percent_undetermined,
        total_time_down=total_time_down,
    )
    errors = validate_dispositivo(payload)
    if errors:
        st.error("No se agrego el dispositivo. Corrige lo siguiente:")
        for message in errors:
            st.markdown(f"- ❌ {message}")
    else:
        row = agregar_dispositivo(wb, payload)
        st.session_state.dispositivos_sesion.append({"Fila": row, **vars(payload)})
        st.success(f"✅ Dispositivo agregado en la fila {row}.")

dispositivos = leer_dispositivos(wb)

st.subheader("Cumplimiento de SLA")
if dispositivos:
    validos = [d for d in dispositivos if isinstance(d.get(COLUMNAS["percent_up"]), (int, float))]
    cumplen = [d for d in validos if d[COLUMNAS["percent_up"]] >= SLA_OBJETIVO]
    promedio = sum(d[COLUMNAS["percent_up"]] for d in validos) / len(validos) if validos else 0.0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Dispositivos", len(validos), border=True)
    metric_cols[1].metric("Cumplen SLA", len(cumplen), border=True)
    metric_cols[2].metric("Incumplen SLA", len(validos) - len(cumplen), border=True)
    metric_cols[3].metric("Disponibilidad promedio", f"{promedio:.2f}%", border=True)

    st.dataframe(dispositivos, hide_index=True, width="stretch")
else:
    st.info("Aun no hay dispositivos capturados en este archivo.")

st.divider()
st.subheader("Alertas de SLA")
st.caption(
    "Se agrupa por Categoria y se compara el promedio de disponibilidad contra "
    f"la meta ({SLA_OBJETIVO:.0f}%). El envio siempre es manual: nunca se envia "
    "nada sin que hagas clic en un boton."
)

resultados_por_categoria: dict = {}
if dispositivos:
    por_categoria = defaultdict(list)
    for d in dispositivos:
        if isinstance(d.get(COLUMNAS["percent_up"]), (int, float)):
            por_categoria[d.get(COLUMNAS["categoria"], "Sin categoria")].append(d)
    for cat, items in por_categoria.items():
        promedio_cat = sum(d[COLUMNAS["percent_up"]] for d in items) / len(items)
        horas_caida_cat = sum(
            (d.get(COLUMNAS["total_time_down"]) or 0) for d in items
        ) / 3600
        resultados_por_categoria[cat] = {
            "disponibilidad": promedio_cat,
            "horas_caida": horas_caida_cat,
        }

alertas = evaluar_alertas(resultados_por_categoria, SLA_OBJETIVO)

if not alertas:
    st.success("Ninguna categoria esta por debajo de la meta de SLA.", icon=":material/check_circle:")
else:
    for alerta in alertas:
        st.warning(alerta.mensaje, icon=":material/warning:")

    mensaje_completo = "\n".join(a.mensaje for a in alertas)

    alert_col1, alert_col2 = st.columns(2)
    with alert_col1:
        destinatarios_texto = st.text_input("Destinatarios de correo (separados por coma)")
        correo_habilitado = config_correo_disponible()
        if not correo_habilitado:
            st.caption("⚠️ Falta configurar SMTP_HOST/PORT/USER/PASSWORD/FROM (ver .env.example).")
        if st.button(
            "Enviar alerta por correo", icon=":material/mail:",
            disabled=not correo_habilitado or not destinatarios_texto.strip(),
        ):
            destinatarios = [d.strip() for d in destinatarios_texto.split(",") if d.strip()]
            try:
                enviar_correo(destinatarios, "Alerta de SLA - Monitoreo de disponibilidad", mensaje_completo)
                st.success("Correo enviado.")
            except ConfiguracionFaltante as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - se muestra al usuario, no se oculta
                st.error(f"No se pudo enviar el correo: {exc}")

    with alert_col2:
        webhook_habilitado = config_webhook_disponible()
        if not webhook_habilitado:
            st.caption("⚠️ Falta configurar ALERTAS_WEBHOOK_URL (Teams/Slack/Google Chat, ver .env.example).")
        if st.button(
            "Enviar alerta a Teams / chat corporativo", icon=":material/forum:",
            disabled=not webhook_habilitado,
        ):
            try:
                enviar_webhook(mensaje_completo)
                st.success("Mensaje enviado al chat corporativo.")
            except ConfiguracionFaltante as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo enviar el mensaje: {exc}")

st.divider()
st.subheader("Reporte de dispositivos caidos (PDF)")
if dispositivos:
    caidos = dispositivos_caidos(dispositivos, SLA_OBJETIVO)
    st.caption(
        f"{len(caidos['total'])} dispositivos por debajo de {SLA_OBJETIVO:.0f}% en total, "
        f"{len(caidos['ajustado'])} despues de excluir causas externas."
    )
    pdf_bytes = build_pdf_dispositivos_caidos(caidos, periodo=f"{mes.capitalize()} {anio}", umbral=SLA_OBJETIVO)
    st.download_button(
        "Descargar PDF de dispositivos caidos",
        data=pdf_bytes,
        file_name=f"dispositivos_caidos_{mes}_{anio}.pdf",
        mime="application/pdf",
        icon=":material/picture_as_pdf:",
    )
else:
    st.info("Agrega dispositivos para poder generar el reporte.")

st.divider()
buffer = BytesIO()
wb.save(buffer)
st.download_button(
    "Descargar archivo de monitoreo (Excel)",
    data=buffer.getvalue(),
    file_name=nombre_estandar,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    icon=":material/download:",
)
st.caption(f"Se descarga con el nombre estandar `{nombre_estandar}`.")

import sys
from datetime import date, datetime, time
from io import BytesIO
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auth import require_auth  # noqa: E402
from schema import PLATFORMS, SLA_OBJETIVO  # noqa: E402
from theme import inject_theme  # noqa: E402
from validation import EventoPayload, validate_event  # noqa: E402
from workbook_io import (  # noqa: E402
    append_event,
    compute_disponibilidad,
    compute_downtime_hours,
    load_lookups,
    load_resumen_baseline,
    load_workbook_for_write,
)

DEFAULT_SOURCE = BASE_DIR / "sami_source_reparado.xlsx"
OTRO = "Otro (escribir)"

st.set_page_config(page_title="Captura de Eventos S@MI", page_icon="🗒️", layout="wide")
inject_theme()
require_auth()


def _load_workbook(file_bytes: bytes | None):
    source = BytesIO(file_bytes) if file_bytes is not None else DEFAULT_SOURCE
    return load_workbook_for_write(source)


def _init_state(file_bytes: bytes | None, reset: bool = False):
    if reset or "wb" not in st.session_state:
        st.session_state.wb = _load_workbook(file_bytes)
        st.session_state.lookups = load_lookups(st.session_state.wb)
        st.session_state.eventos_sesion = []


st.sidebar.title("Formulario de Eventos S@MI")
st.sidebar.caption(
    "Captura eventos con las mismas validaciones de calidad de datos que el "
    "panel de disponibilidad (Analisis-Python.1), adaptadas a la Planilla "
    "Control de Eventos S@MI."
)

uploaded = st.sidebar.file_uploader(
    "Cargar una Planilla S@MI distinta (opcional)", type=["xlsx"]
)
uploaded_bytes = uploaded.getvalue() if uploaded is not None else None

if st.sidebar.button("Reiniciar formulario", icon=":material/restart_alt:"):
    _init_state(uploaded_bytes, reset=True)
    st.rerun()

_init_state(uploaded_bytes)

wb = st.session_state.wb
lookups = st.session_state.lookups

platform = st.sidebar.selectbox("Plataforma", options=list(PLATFORMS.keys()))
schema = PLATFORMS[platform]
ws = wb[schema.sheet]

baseline = load_resumen_baseline(wb, platform)
dias_mes_default = baseline["dias_mes"] if baseline else 31
dias_mes = st.sidebar.number_input(
    "Dias del mes a considerar para el SLA", min_value=1, max_value=31, value=int(dias_mes_default)
)

st.title(f"Captura de evento · {platform}")
st.badge("Formulario Eventos S@MI · v1.0", icon=":material/info:", color="blue")
st.caption(
    f"Hoja de origen: '{schema.sheet}'. Los campos obligatorios se validan antes de guardar; "
    "ningun evento incompleto llega a la planilla ni al calculo de SLA."
)

if baseline is None:
    st.info(
        f"La hoja 'Resumen' no tiene una fila de referencia para **{platform}** "
        "(numero de dispositivos / horas del mes), asi que no se puede calcular un "
        "porcentaje de disponibilidad para esta plataforma. El evento igual se puede "
        "capturar; solo se mostraran las horas de caida acumuladas."
    )

with st.form(f"formulario_{platform}", clear_on_submit=False):
    col1, col2 = st.columns(2)

    with col1:
        dispositivo = st.text_input(f"{schema.device_label} *")
        analista_choice = st.selectbox(
            "Analista *", options=[*lookups["analistas"], OTRO]
        )
        analista_libre = (
            st.text_input("Nombre del analista") if analista_choice == OTRO else ""
        )
        ticket = st.text_input("Numero de Ticket *")
        if schema.has_tigo:
            acceso_tigo = st.text_input("Acceso TIGO")
            ticket_tigo_une = st.text_input("Numero Ticket TIGO UNE")
        else:
            acceso_tigo = ""
            ticket_tigo_une = ""
        descripcion = st.text_area("Descripcion del Evento")

    with col2:
        inicio_fecha = st.date_input("Fecha Inicio Evento *", value=date.today())
        inicio_hora = st.time_input("Hora Inicio Evento *", value=time(0, 0))
        fin_fecha = st.date_input("Fecha Fin Evento *", value=date.today())
        fin_hora = st.time_input("Hora Fin Evento *", value=time(0, 0))
        causa_choice = st.selectbox("Causa *", options=[*lookups["causas"], OTRO])
        causa_libre = st.text_input("Especificar causa") if causa_choice == OTRO else ""
        areas_choice = st.selectbox("Areas Involucradas *", options=[*lookups["areas"], OTRO])
        areas_libre = st.text_input("Especificar area") if areas_choice == OTRO else ""

    solucion = st.text_area("Solucion *")

    submitted = st.form_submit_button("Guardar evento", icon=":material/save:")

if submitted:
    payload = EventoPayload(
        dispositivo=dispositivo,
        analista=analista_libre if analista_choice == OTRO else analista_choice,
        ticket=ticket,
        descripcion=descripcion,
        inicio=datetime.combine(inicio_fecha, inicio_hora),
        causa=causa_libre if causa_choice == OTRO else causa_choice,
        areas=areas_libre if areas_choice == OTRO else areas_choice,
        solucion=solucion,
        fin=datetime.combine(fin_fecha, fin_hora),
        acceso_tigo=acceso_tigo,
        ticket_tigo_une=ticket_tigo_une,
    )
    errors = validate_event(payload, device_label=schema.device_label)

    if errors:
        st.error("No se guardo el evento. Corrige lo siguiente:")
        for message in errors:
            st.markdown(f"- ❌ {message}")
    else:
        row = append_event(wb, platform, payload)
        st.session_state.eventos_sesion.append(
            {"Fila": row, "Plataforma": platform, **vars(payload)}
        )
        st.success(f"✅ Evento guardado en '{schema.sheet}', fila {row}.")

st.subheader("Cumplimiento de SLA en vivo")
downtime_hours, event_count = compute_downtime_hours(ws, schema)
metric_cols = st.columns(4)
metric_cols[0].metric("Eventos con fecha inicio/fin", event_count, border=True)
metric_cols[1].metric("Horas de caida acumuladas", f"{downtime_hours:.2f} h", border=True)

if baseline is not None:
    total_horas_mes = baseline["dispositivos"] * dias_mes * 24
    disponibilidad = compute_disponibilidad(total_horas_mes, downtime_hours)
    cumple = disponibilidad >= SLA_OBJETIVO
    metric_cols[2].metric("Disponibilidad del mes", f"{disponibilidad:.2f}%", border=True)
    with metric_cols[3]:
        if cumple:
            st.success(f"Cumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/check_circle:")
        else:
            st.error(f"Incumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/error:")
    st.caption(
        f"Base: {baseline['dispositivos']} dispositivos x {dias_mes} dias x 24 h = "
        f"{total_horas_mes:,.0f} horas disponibles en el mes."
    )
else:
    metric_cols[2].metric("Disponibilidad del mes", "N/D", border=True)

if st.session_state.eventos_sesion:
    with st.expander(f"Eventos guardados en esta sesion ({len(st.session_state.eventos_sesion)})"):
        st.dataframe(st.session_state.eventos_sesion, hide_index=True)

st.divider()
buffer = BytesIO()
wb.save(buffer)
st.download_button(
    "Descargar Planilla S@MI actualizada",
    data=buffer.getvalue(),
    file_name="Planilla Control de Eventos S@MI - actualizada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    icon=":material/download:",
)
st.caption(
    "Este boton descarga una copia con los eventos capturados en esta sesion. "
    "El archivo original en disco nunca se modifica automaticamente."
)

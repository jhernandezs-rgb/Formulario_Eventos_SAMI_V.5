"""Pagina de revision: carga el archivo mensual de incidencias ya
descargado, detecta problemas de captura (campos vacios, horas mal
digitadas) y separa la disponibilidad "total" de la "ajustada" excluyendo
las incidencias marcadas como no controladas (p. ej. causa electrica), para
compararlas contra la meta de SLA."""

import sys
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auth import require_auth  # noqa: E402
from schema import PLATFORMS, SLA_OBJETIVO  # noqa: E402
from review import FilaRevisada, aplicar_correcciones, calcular_sla, scan_platform  # noqa: E402
from theme import inject_theme  # noqa: E402
from workbook_io import load_resumen_baseline, load_workbook_for_write  # noqa: E402

DEFAULT_SOURCE = BASE_DIR / "sami_source_reparado.xlsx"

st.set_page_config(page_title="Revision mensual S@MI", page_icon="🔍", layout="wide")
inject_theme()
require_auth()


def _load_workbook(file_bytes: bytes | None):
    source = BytesIO(file_bytes) if file_bytes is not None else DEFAULT_SOURCE
    return load_workbook_for_write(source)


st.sidebar.title("Revision del archivo mensual")
st.sidebar.caption(
    "Carga el Excel de incidencias del mes, corrige lo que este mal y decide "
    "que incidencias no cuentan contra el SLA antes de reportar el cumplimiento."
)

uploaded = st.sidebar.file_uploader("Cargar archivo del mes (.xlsx)", type=["xlsx"])
uploaded_bytes = uploaded.getvalue() if uploaded is not None else None

if st.sidebar.button("Cargar / recargar archivo", icon=":material/refresh:"):
    st.session_state.wb = _load_workbook(uploaded_bytes)
    st.session_state.pop("no_controlados", None)

if "wb" not in st.session_state:
    st.session_state.wb = _load_workbook(uploaded_bytes)

wb = st.session_state.wb
st.session_state.setdefault("no_controlados", {})

platform = st.sidebar.selectbox("Plataforma", options=list(PLATFORMS.keys()))
schema = PLATFORMS[platform]
ws = wb[schema.sheet]

baseline = load_resumen_baseline(wb, platform)
dias_mes_default = baseline["dias_mes"] if baseline else 31
dias_mes = st.sidebar.number_input(
    "Dias del mes a considerar para el SLA",
    min_value=1,
    max_value=31,
    value=int(dias_mes_default),
)

st.title(f"Revision mensual · {platform}")
st.caption(
    f"Hoja de origen: '{schema.sheet}'. Meta de SLA: {SLA_OBJETIVO:.0f}% o superior."
)

filas = scan_platform(ws, schema)

if not filas:
    st.info("No se encontraron incidencias registradas en esta hoja.")
    st.stop()

overrides = st.session_state.no_controlados.setdefault(platform, {})

rows = []
for f in filas:
    default_no_controlado = overrides.get(f.fila, f.no_controlado_sugerido)
    rows.append(
        {
            "Fila": f.fila,
            "Item": f.item,
            schema.device_label: f.dispositivo,
            "Analista": f.analista,
            "Ticket": f.ticket,
            "Causa": f.causa,
            "Areas Involucradas": f.areas,
            "Solucion": f.solucion,
            "Inicio": f.inicio,
            "Fin": f.fin,
            "Duracion (h)": round(f.duracion_horas, 2),
            "No controlado (excluir del SLA)": default_no_controlado,
            "Problemas detectados": "; ".join(f.problemas) if f.problemas else "",
            "Notas": "; ".join(f.notas) if f.notas else "",
        }
    )
df = pd.DataFrame(rows)

problem_count = int((df["Problemas detectados"] != "").sum())
suggested_count = int(df["No controlado (excluir del SLA)"].sum())

metric_cols = st.columns(3)
metric_cols[0].metric("Incidencias en esta hoja", len(df), border=True)
metric_cols[1].metric("Con problemas detectados", problem_count, border=True)
metric_cols[2].metric("Marcadas como no controladas", suggested_count, border=True)

solo_problemas = st.checkbox("Mostrar solo filas con problemas detectados")
df_mostrado = df[df["Problemas detectados"] != ""] if solo_problemas else df

st.caption(
    "Edita directamente Dispositivo, Analista, Ticket, Causa, Areas, Solucion, "
    "Inicio y Fin donde haga falta. La columna 'No controlado' se sugiere "
    "automaticamente segun la Causa (fallas electricas, de proveedor, etc.) "
    "pero la decision final es tuya."
)

edited = st.data_editor(
    df_mostrado,
    hide_index=True,
    width="stretch",
    disabled=["Fila", "Item", "Duracion (h)", "Problemas detectados", "Notas"],
    column_config={
        "Inicio": st.column_config.DatetimeColumn("Fecha/Hora Inicio", step=60),
        "Fin": st.column_config.DatetimeColumn("Fecha/Hora Fin", step=60),
        "No controlado (excluir del SLA)": st.column_config.CheckboxColumn(
            "No controlado (excluir del SLA)"
        ),
    },
    key=f"editor_{platform}",
)

# Fusiona lo editado (que puede ser solo el subconjunto filtrado) sobre el
# conjunto completo, y guarda las decisiones de "no controlado" en sesion.
df_final = df.set_index("Fila")
df_final.update(edited.set_index("Fila"))
for fila, marcado in df_final["No controlado (excluir del SLA)"].items():
    overrides[int(fila)] = bool(marcado)

filas_actualizadas = []
no_controlados_set = set()
for f in filas:
    row_data = df_final.loc[f.fila]
    f.dispositivo = row_data[schema.device_label]
    f.analista = row_data["Analista"]
    f.ticket = row_data["Ticket"]
    f.causa = row_data["Causa"]
    f.areas = row_data["Areas Involucradas"]
    f.solucion = row_data["Solucion"]
    inicio = row_data["Inicio"]
    fin = row_data["Fin"]
    f.inicio = inicio.to_pydatetime() if isinstance(inicio, pd.Timestamp) else inicio
    f.fin = fin.to_pydatetime() if isinstance(fin, pd.Timestamp) else fin
    filas_actualizadas.append(f)
    if overrides.get(f.fila, False):
        no_controlados_set.add(f.fila)

st.subheader("Cumplimiento de SLA")
if baseline is not None:
    total_horas_mes = baseline["dispositivos"] * dias_mes * 24
    resultado = calcular_sla(filas_actualizadas, total_horas_mes, no_controlados_set)

    sla_cols = st.columns(2)
    with sla_cols[0]:
        st.metric(
            "Disponibilidad total (todas las causas cuentan)",
            f"{resultado['disponibilidad_total']:.2f}%",
            border=True,
        )
        if resultado["disponibilidad_total"] >= SLA_OBJETIVO:
            st.success(f"Cumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/check_circle:")
        else:
            st.error(f"Incumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/error:")
    with sla_cols[1]:
        st.metric(
            "Disponibilidad ajustada (excluye no controladas)",
            f"{resultado['disponibilidad_ajustada']:.2f}%",
            border=True,
        )
        if resultado["disponibilidad_ajustada"] >= SLA_OBJETIVO:
            st.success(f"Cumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/check_circle:")
        else:
            st.error(f"Incumple SLA ({SLA_OBJETIVO:.0f}%)", icon=":material/error:")

    st.caption(
        f"Base: {baseline['dispositivos']} dispositivos x {dias_mes} dias x 24 h = "
        f"{total_horas_mes:,.0f} horas disponibles en el mes. "
        f"Horas de caida: {resultado['horas_totales_caida']:.2f} h totales, de las "
        f"cuales {resultado['horas_no_controladas']:.2f} h se marcaron como no "
        "controladas."
    )
else:
    st.info(
        f"La hoja 'Resumen' no tiene una fila de referencia para **{platform}**, asi "
        "que no se puede calcular un porcentaje de disponibilidad. Solo se muestran "
        "las horas de caida."
    )

st.divider()
if st.button("Guardar correcciones en el libro", icon=":material/save:"):
    aplicar_correcciones(ws, schema, filas_actualizadas)
    st.success(
        f"Correcciones aplicadas a '{schema.sheet}'. Descarga el archivo actualizado abajo."
    )

buffer = BytesIO()
wb.save(buffer)
st.download_button(
    "Descargar Planilla S@MI revisada",
    data=buffer.getvalue(),
    file_name="Planilla Control de Eventos S@MI - revisada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    icon=":material/download:",
)
st.caption(
    "La clasificacion 'no controlado' vive solo en esta sesion (no se escribe en "
    "el Excel); las correcciones de texto y fechas si se guardan al hacer clic en "
    "'Guardar correcciones en el libro'."
)

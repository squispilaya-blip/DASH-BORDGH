# -*- coding: utf-8 -*-
"""
ui_comparador.py — Pestaña de comparación de dos reportes exportados.

El usuario sube dos archivos Excel del mismo RIS pero de fechas distintas
(exportados desde el dashboard), y se compara qué niños se vacunaron
y cuáles siguen faltando.
"""

import io
from datetime import date

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from comparador_exportado import (
    DOSE_COLS, compare_reportes, get_dose_cols_in,
    load_reporte, to_dataframe,
)


# ── Caché de carga ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Cargando reporte...")
def _load(file_bytes: bytes) -> pd.DataFrame:
    return load_reporte(file_bytes)


# ── Export Excel ──────────────────────────────────────────────────────────────

def _export_excel(df_resumen: pd.DataFrame, df_detalle: pd.DataFrame) -> bytes:
    wb = Workbook()
    _fill_ws(wb.active,           "Resumen",         df_resumen)
    _fill_ws(wb.create_sheet(),   "Detalle completo", df_detalle)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_ws(ws, title: str, df: pd.DataFrame) -> None:
    ws.title = title
    hfill = PatternFill(start_color="1A6FA8", end_color="1A6FA8", fill_type="solid")
    hfont = Font(bold=True, color="FFFFFF")
    for ci, h in enumerate(df.columns, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill, c.font = hfill, hfont
        c.alignment = Alignment(horizontal="center", wrap_text=True)
    for ri, row in enumerate(df.itertuples(index=False), 2):
        for ci, val in enumerate(row, 1):
            ws.cell(row=ri, column=ci, value=val).alignment = Alignment(
                wrap_text=True, vertical="top"
            )
    for col in ws.columns:
        length = max(
            (max((len(ln) for ln in str(c.value or "").split("\n")), default=0)
             for c in col), default=0
        )
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(length + 2, 50)
    ws.freeze_panes = "A2"


# ── UI principal ──────────────────────────────────────────────────────────────

def render_comparison_tab() -> None:
    st.subheader("🔄 Comparar dos reportes del mismo RIS")
    st.caption(
        "Sube el reporte **antiguo** y el **nuevo** (exportados desde el dashboard). "
        "Identifica qué niños se vacunaron y quiénes siguen faltando."
    )

    # ── Carga de archivos ─────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        file_a = st.file_uploader(
            "📂 Reporte ANTIGUO (primera fecha)",
            type=["xlsx"],
            key="comp_a",
            help="El reporte de la fecha anterior (ej. primera semana de abril).",
        )
    with col_b:
        file_b = st.file_uploader(
            "📂 Reporte NUEVO (fecha más reciente)",
            type=["xlsx"],
            key="comp_b",
            help="El reporte más reciente (ej. primera semana de mayo).",
        )

    if not file_a or not file_b:
        st.info("📋 Carga ambos reportes Excel para ver la comparación.")
        return

    try:
        df_a = _load(file_a.read())
        df_b = _load(file_b.read())
    except Exception as e:
        st.error(f"Error al leer los archivos: {e}")
        return

    # ── Validación básica ─────────────────────────────────────────────────────
    if 'DNI' not in df_a.columns or 'DNI' not in df_b.columns:
        st.error("Los archivos no tienen columna 'DNI'. Verifica que son reportes exportados del dashboard.")
        return

    ris_a = df_a['RIS'].iloc[0] if 'RIS' in df_a.columns else "—"
    ris_b = df_b['RIS'].iloc[0] if 'RIS' in df_b.columns else "—"

    st.success(
        f"**Reporte A:** {len(df_a):,} niños — RIS: {ris_a} &nbsp;|&nbsp; "
        f"**Reporte B:** {len(df_b):,} niños — RIS: {ris_b}"
    )

    # ── Comparación ───────────────────────────────────────────────────────────
    with st.spinner("Comparando reportes..."):
        results = compare_reportes(df_a, df_b)

    if not results:
        st.info("No se detectaron cambios entre los dos reportes.")
        return

    # ── Métricas globales ─────────────────────────────────────────────────────
    total_vac     = sum(1 for r in results if r['se_vacuno'])
    total_falta   = sum(1 for r in results if r['sigue_faltando'] and not r['se_vacuno'])
    total_parcial = sum(1 for r in results if r['se_vacuno'] and r['sigue_faltando'])
    total_nuevos  = sum(1 for r in results if r['categoria'] == 'nuevo')

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "✅ Se vacunaron",
        total_vac,
        help="Niños que recibieron al menos una vacuna pendiente entre los dos reportes",
    )
    m2.metric(
        "❌ Siguen faltando",
        total_falta,
        help="Niños que aún tienen vacunas pendientes en el reporte nuevo (sin ninguna nueva vacuna)",
    )
    m3.metric(
        "⚠️ Parcial",
        total_parcial,
        help="Niños que se vacunaron en algunas dosis pero aún tienen otras pendientes",
    )
    m4.metric(
        "➕ Nuevos en padrón",
        total_nuevos,
        help="Niños presentes en el reporte nuevo pero no en el anterior",
    )

    st.divider()

    # ── Filtros ───────────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filtros")

    # Vacunas disponibles en los archivos
    all_dose_cols = [c for c in DOSE_COLS if c in set(get_dose_cols_in(df_a)) | set(get_dose_cols_in(df_b))]

    f1, f2, f3 = st.columns(3)
    with f1:
        cat_opciones = {
            "Todos": None,
            "✅ Se vacunaron":    "se_vacuno",
            "❌ Siguen faltando": "sigue_faltando",
            "⚠️ Parcial":        "parcial",
        }
        cat_sel_label = st.selectbox("Mostrar", list(cat_opciones.keys()))
        cat_sel = cat_opciones[cat_sel_label]

    with f2:
        vacuna_sel = st.multiselect(
            "Filtrar por vacuna",
            options=all_dose_cols,
            help="Deja vacío para ver todas las vacunas.",
        )

    with f3:
        eess_options = sorted({r['EESS'] for r in results if r['EESS'] and r['EESS'] != 'nan'})
        eess_sel = st.multiselect("Filtrar por EESS", eess_options)

    # ── Tabla de resultados ───────────────────────────────────────────────────
    st.markdown("### 📋 Detalle de niños")

    df_det = to_dataframe(results, dose_filter=vacuna_sel or None, cat_filter=cat_sel)

    # Filtro adicional por EESS
    if eess_sel:
        df_det = df_det[df_det['EESS'].isin(eess_sel)]

    if df_det.empty:
        st.warning("No hay registros con los filtros aplicados.")
    else:
        st.caption(f"Mostrando **{len(df_det):,}** registros")
        st.dataframe(
            df_det,
            use_container_width=True,
            hide_index=True,
            height=460,
            column_config={
                "RIS":                  st.column_config.TextColumn("RIS",                width="medium"),
                "Zona Sanitaria":       st.column_config.TextColumn("Zona Sanitaria",     width="medium"),
                "EESS":                 st.column_config.TextColumn("EESS",               width="medium"),
                "DNI":                  st.column_config.TextColumn("DNI",                width="small"),
                "Nombres":              st.column_config.TextColumn("Nombres",            width="large"),
                "Prioridad actual":     st.column_config.TextColumn("Prioridad actual",   width="medium"),
                "Categoría":            st.column_config.TextColumn("Categoría",          width="medium"),
                "Vacunas administradas":st.column_config.TextColumn("Vacunas administradas", width="large"),
                "Vacunas pendientes":   st.column_config.TextColumn("Vacunas pendientes", width="large"),
            },
        )

    # ── Resumen por EESS ──────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🏥 Resumen por EESS")

    resumen_rows = []
    eess_groups: dict = {}
    for r in results:
        eess = r['EESS']
        if eess not in eess_groups:
            eess_groups[eess] = {'vac': 0, 'falta': 0, 'parcial': 0, 'nuevo': 0}
        if r['categoria'] == 'nuevo':
            eess_groups[eess]['nuevo'] += 1
        elif r['se_vacuno'] and r['sigue_faltando']:
            eess_groups[eess]['parcial'] += 1
        elif r['se_vacuno']:
            eess_groups[eess]['vac'] += 1
        elif r['sigue_faltando']:
            eess_groups[eess]['falta'] += 1

    for eess, s in sorted(eess_groups.items()):
        resumen_rows.append({
            'EESS':                eess,
            '✅ Se vacunaron':     s['vac'],
            '⚠️ Parcial':         s['parcial'],
            '❌ Siguen faltando':  s['falta'],
            '➕ Nuevos':           s['nuevo'],
            'Total':               sum(s.values()),
        })

    df_resumen = pd.DataFrame(resumen_rows)
    if not df_resumen.empty:
        st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.divider()
    col_btn, col_cap = st.columns([1, 3])
    with col_btn:
        if st.button("📥 Generar Excel comparación", use_container_width=True):
            with st.spinner("Generando Excel..."):
                df_all = to_dataframe(results)   # sin filtros para exportar todo
                excel_bytes = _export_excel(df_resumen, df_all)
            fecha = date.today().strftime("%Y%m%d")
            st.download_button(
                label="⬇️ Descargar comparación",
                data=excel_bytes,
                file_name=f"comparacion_{ris_b}_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with col_cap:
        st.caption(
            f"El Excel incluye 2 hojas: 'Resumen' por EESS y "
            f"'Detalle completo' con los {len(results):,} registros."
        )

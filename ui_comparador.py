# -*- coding: utf-8 -*-
"""ui_comparador.py — Pestaña de comparación de dos padrones por RIS."""

import io
from datetime import date

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from comparador import CATEGORIAS, compare_reports, summary_by_ris
from processor import build_all


# ── Helpers internos ──────────────────────────────────────────────────────────

def _fecha_corte(df: pd.DataFrame) -> str:
    if "FECHA_CORTE_PADRON_N" in df.columns:
        val = df["FECHA_CORTE_PADRON_N"].iloc[0]
        return str(val) if pd.notna(val) else "—"
    return "—"


def _changes_to_df(changes: list) -> pd.DataFrame:
    rows = [
        {
            "RIS":               c["Red"],
            "Zona Sanitaria":    c["Microred"],
            "EESS":              c["EESS"],
            "DNI":               c["DNI"],
            "Nombres":           c["Nombres"],
            "Categoría":         CATEGORIAS.get(c["categoria"], c["categoria"]),
            "Cambios vacunales": c["detalle"],
        }
        for c in changes
    ]
    return (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(
            columns=["RIS", "Zona Sanitaria", "EESS", "DNI", "Nombres",
                     "Categoría", "Cambios vacunales"]
        )
    )


def _export_excel(df_summary: pd.DataFrame, df_detail: pd.DataFrame) -> bytes:
    wb = Workbook()
    _fill_sheet(wb.active, "Resumen por RIS", df_summary)
    _fill_sheet(wb.create_sheet("Detalle cambios"), "Detalle cambios", df_detail)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_sheet(ws, title: str, df: pd.DataFrame) -> None:
    ws.title = title
    hfill = PatternFill(start_color="1A6FA8", end_color="1A6FA8", fill_type="solid")
    hfont = Font(bold=True, color="FFFFFF")
    for col_i, h in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=col_i, value=h)
        cell.fill      = hfill
        cell.font      = hfont
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for row_i, row in enumerate(df.itertuples(index=False), 2):
        for col_i, val in enumerate(row, 1):
            c = ws.cell(row=row_i, column=col_i, value=val)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    for col in ws.columns:
        length = max(
            (max((len(ln) for ln in str(cell.value or "").split("\n")), default=0)
             for cell in col),
            default=0,
        )
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(length + 2, 50)

    ws.freeze_panes = "A2"


# ── Pestaña principal ─────────────────────────────────────────────────────────

def render_comparison_tab() -> None:
    st.subheader("🔄 Comparar dos reportes de vacunación")
    st.caption(
        "Sube el padrón **antiguo** y el **nuevo** para ver qué cambió "
        "en la situación vacunal, agrupado por RIS."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        file_a = st.file_uploader(
            "📂 Padrón ANTIGUO (referencia)",
            type=["xlsx"],
            key="comp_a",
            help="El reporte descargado anteriormente (ej. ayer).",
        )
    with col_b:
        file_b = st.file_uploader(
            "📂 Padrón NUEVO (más reciente)",
            type=["xlsx"],
            key="comp_b",
            help="El reporte descargado hoy o el más reciente.",
        )

    if not file_a or not file_b:
        st.info("Carga ambos padrones para ver la comparación.")
        return

    try:
        with st.spinner("Procesando padrón antiguo..."):
            df_a, patients_a = build_all(file_a.read())
        with st.spinner("Procesando padrón nuevo..."):
            df_b, patients_b = build_all(file_b.read())
    except ValueError as e:
        st.error(str(e))
        return

    fc_a, fc_b = _fecha_corte(df_a), _fecha_corte(df_b)
    st.success(
        f"**Padrón A (antiguo):** {len(df_a):,} pacientes — corte: {fc_a} &nbsp;|&nbsp; "
        f"**Padrón B (nuevo):** {len(df_b):,} pacientes — corte: {fc_b}"
    )

    changes = compare_reports(patients_a, patients_b)

    if not changes:
        st.info("No se detectaron cambios entre los dos padrones.")
        return

    # ── Métricas globales ─────────────────────────────────────────────────────
    total_vac   = sum(1 for c in changes if c["categoria"] == "nuevo_vacunado")
    total_new   = sum(1 for c in changes if c["categoria"] == "nuevo_padron")
    total_ret   = sum(1 for c in changes if c["categoria"] == "retirado_padron")
    total_otros = sum(1 for c in changes if c["categoria"] == "otro_cambio")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Nuevos vacunados",  total_vac,
              help="Pasaron de Pendiente/Incumplió a Aplicada entre los dos reportes")
    m2.metric("➕ Nuevos en padrón", total_new,
              help="DNI presente en el padrón nuevo pero no en el antiguo")
    m3.metric("➖ Retirados",        total_ret,
              help="DNI presente en el padrón antiguo pero no en el nuevo")
    m4.metric("🔄 Otros cambios",    total_otros,
              help="Cambios de estado que no son nuevas vacunaciones (ej. Pendiente → Incumplió)")

    st.divider()

    # ── Resumen por RIS ───────────────────────────────────────────────────────
    st.markdown("### Resumen por RIS")
    df_summary = summary_by_ris(changes)
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.divider()

    # ── Filtros + detalle ─────────────────────────────────────────────────────
    st.markdown("### Detalle de cambios")

    redes = sorted({c["Red"] for c in changes})
    cat_options = list(CATEGORIAS.values())
    cat_key_by_label = {v: k for k, v in CATEGORIAS.items()}

    f1, f2 = st.columns(2)
    with f1:
        ris_filter = st.multiselect("Filtrar por RIS", redes)
    with f2:
        cat_filter = st.selectbox("Filtrar por categoría", ["Todas"] + cat_options)

    filtered = changes
    if ris_filter:
        filtered = [c for c in filtered if c["Red"] in set(ris_filter)]
    if cat_filter != "Todas":
        cat_key = cat_key_by_label[cat_filter]
        filtered = [c for c in filtered if c["categoria"] == cat_key]

    df_detail = _changes_to_df(filtered)

    if df_detail.empty:
        st.warning("No hay registros con los filtros aplicados.")
    else:
        st.dataframe(
            df_detail,
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "RIS":               st.column_config.TextColumn("RIS",            width="medium"),
                "Zona Sanitaria":    st.column_config.TextColumn("Zona Sanitaria", width="medium"),
                "EESS":              st.column_config.TextColumn("EESS",           width="medium"),
                "DNI":               st.column_config.TextColumn("DNI",            width="small"),
                "Nombres":           st.column_config.TextColumn("Nombres",        width="medium"),
                "Categoría":         st.column_config.TextColumn("Categoría",      width="medium"),
                "Cambios vacunales": st.column_config.TextColumn("Cambios vacunales", width="large"),
            },
        )

    # ── Exportar ──────────────────────────────────────────────────────────────
    st.divider()
    col_btn, col_cap = st.columns([1, 3])
    with col_btn:
        if st.button("📥 Generar Excel de comparación", use_container_width=True):
            with st.spinner("Generando Excel..."):
                excel_bytes = _export_excel(df_summary, _changes_to_df(changes))
            fecha = date.today().strftime("%Y%m%d")
            st.download_button(
                label="⬇️ Descargar comparación",
                data=excel_bytes,
                file_name=f"comparacion_vacunas_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with col_cap:
        st.caption(
            "El Excel incluye 2 hojas: 'Resumen por RIS' y 'Detalle cambios' "
            f"con todos los {len(changes):,} registros (sin filtro)."
        )

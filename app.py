# -*- coding: utf-8 -*-
"""Dashboard de vacunación — NTS N° 196-MINSA/DGIESP-2022"""

import streamlit as st
import pandas as pd

from auth import require_auth
from processor import build_all
from ui_filters import render_filters, apply_patient_filters
from ui_table import render_patient_table
from exporter import generate_excel
from ui_comparador import render_comparison_tab

st.set_page_config(
    page_title="Sistema de Vacunación",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

require_auth()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏥 Dashboard de Vacunación")
st.caption("NTS N° 196-MINSA/DGIESP-2022 | RM 884-2022-MINSA")

# ── Botón de cierre de sesión ─────────────────────────────────────────────────
with st.sidebar:
    if st.button("🚪 Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Dashboard", "🔄 Comparar reportes"])

# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────
with tab1:
    uploaded = st.file_uploader(
        "📂 Cargar padrón Excel (reporte..xlsx)",
        type=["xlsx"],
        help="Arrastra el archivo o haz clic para seleccionarlo.",
    )

    if not uploaded:
        st.info("Carga el padrón Excel para comenzar.")
    else:
        file_bytes = uploaded.read()
        try:
            df, all_processed = build_all(file_bytes)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        # ── Info del padrón ───────────────────────────────────────────────────
        fecha_corte = df["FECHA_CORTE_PADRON_N"].iloc[0] if "FECHA_CORTE_PADRON_N" in df.columns else "—"
        st.sidebar.markdown(f"**Fecha de corte:** {fecha_corte}")
        st.sidebar.markdown(f"**Total en padrón:** {len(df):,} pacientes")

        # ── Filtros + tabla ───────────────────────────────────────────────────
        filters   = render_filters(df)
        processed = apply_patient_filters(all_processed, filters)
        render_patient_table(processed)

        # ── Leyenda ───────────────────────────────────────────────────────────
        with st.expander("📋 Leyenda — ¿Qué significa cada valor?", expanded=False):
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("##### Estado de cada dosis (en la tabla)")
                st.markdown("""
| Valor | Significado |
|-------|-------------|
| `28/12/2024` | Vacuna aplicada en esa fecha |
| `28/12/2024 (tardía)` | Aplicada, pero fuera de la ventana ideal según NTS |
| `Pendiente` | Aún no se ha vacunado y ya le corresponde |
| `Incumplió` | Pasó la ventana ideal sin vacunarse — se puede recuperar |
| `Vencida` | Ya superó el límite de edad — ya no se puede aplicar |
| `Error reg.` | La etiqueta registrada es incorrecta (ej. "1ra" en vez de "DU") |
| `N/C` | No corresponde a la edad o grupo de este niño |
| Fecha futura | Aún no tiene la edad — fecha programada según NTS |
""")

            with col_b:
                st.markdown("##### Columna Prioridad")
                st.markdown("""
| Prioridad | Acción requerida |
|-----------|-----------------|
| 🔴 Corregir registro | Hay un error en la etiqueta de una vacuna — corregir en el sistema de origen |
| ❌ Recuperar | El niño no fue vacunado en el momento correcto, pero aún puede recuperarse |
| ⚠️ Vacunar | Tiene dosis pendientes dentro del plazo normal |
| ✅ Completo | Todas las vacunas están al día según la NTS |
""")

                st.markdown("##### Columna Vacunas a atender")
                st.markdown("""
Lista las vacunas que requieren acción inmediata
(pendientes, incumplidas o con error de registro).
Úsala junto con el filtro **"Acción requerida"** del sidebar
para obtener listados específicos por tipo de atención.
""")

        # ── Exportar ──────────────────────────────────────────────────────────
        st.divider()
        col_exp, col_info = st.columns([1, 3])
        with col_exp:
            if st.button("📥 Generar reporte Excel", use_container_width=True):
                with st.spinner("Generando Excel..."):
                    excel_bytes = generate_excel(processed)
                st.download_button(
                    label="⬇️ Descargar reporte",
                    data=excel_bytes,
                    file_name=f"reporte_vacunas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        with col_info:
            st.caption(
                f"El reporte incluye {len(processed):,} pacientes en 2 hojas: "
                f"'Completo' y 'Pendientes'. La edad se calcula al día de hoy."
            )

# ── Tab 2: Comparar reportes ──────────────────────────────────────────────────
with tab2:
    render_comparison_tab()

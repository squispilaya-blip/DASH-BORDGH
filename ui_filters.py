import streamlit as st
import pandas as pd
from vaccine_logic import patient_has_pending, patient_action_priority, ACTION_LABELS, ERROR_DU, INCUMPLIO, PENDIENTE

# Grupos etarios definidos en NTS N°196-MINSA/DGIESP-2022
# Incluye ≥ 5 años para cubrir dT y Amarílica
AGE_GROUPS = ["< 1 año", "1 año", "2 años", "3 años", "4 años", "5 años", "≥ 6 años"]


def render_filters(df: pd.DataFrame) -> dict:
    """
    Renderiza filtros en el sidebar con cascada Red → Microred → EESS.

    - Seleccionar Red restringe las opciones de Microred a las de esa Red.
    - Seleccionar Microred restringe las opciones de EESS a las de esa Microred.
    - Cada filtro puede usarse de forma independiente.
    """
    st.sidebar.header("🔍 Filtros")

    # ── RIS ───────────────────────────────────────────────────────────────────
    redes = sorted(df["RED"].dropna().unique().tolist())
    red_sel = st.sidebar.multiselect("RIS", redes)

    # ── Zona Sanitaria (cascada desde RIS) ───────────────────────────────────
    if red_sel:
        microred_options = sorted(
            df[df["RED"].isin(red_sel)]["MICRORED"].dropna().unique().tolist()
        )
    else:
        microred_options = sorted(df["MICRORED"].dropna().unique().tolist())
    microred_sel = st.sidebar.multiselect("Zona Sanitaria", microred_options)

    # ── EESS (cascada desde Zona Sanitaria, luego desde RIS, luego todo) ─────
    if microred_sel:
        eess_options = sorted(
            df[df["MICRORED"].isin(microred_sel)]["EESS_ATN"].dropna().unique().tolist()
        )
    elif red_sel:
        eess_options = sorted(
            df[df["RED"].isin(red_sel)]["EESS_ATN"].dropna().unique().tolist()
        )
    else:
        eess_options = sorted(df["EESS_ATN"].dropna().unique().tolist())
    eess_sel = st.sidebar.multiselect("EESS", eess_options)

    # ── Otros filtros ─────────────────────────────────────────────────────────
    sexos = sorted(df["SEXO"].dropna().unique().tolist())
    grupo_sel  = st.sidebar.multiselect("Grupo etario", AGE_GROUPS)
    sexo_sel   = st.sidebar.multiselect("Sexo", sexos)
    dni_txt    = st.sidebar.text_input("DNI (búsqueda exacta)")
    nombre_txt = st.sidebar.text_input("Nombre (búsqueda parcial)")

    # ── Filtro por acción requerida ───────────────────────────────────────────
    st.sidebar.markdown("---")
    accion_sel = st.sidebar.multiselect(
        "Acción requerida",
        options=[
            ACTION_LABELS[ERROR_DU],
            ACTION_LABELS[INCUMPLIO],
            ACTION_LABELS[PENDIENTE],
            ACTION_LABELS["OK"],
        ],
        help="Filtra por el tipo de atención que necesita el paciente",
    )

    return {
        "red":             red_sel,
        "microred":        microred_sel,
        "eess":            eess_sel,
        "grupo":           grupo_sel,
        "sexo":            sexo_sel,
        "dni":             dni_txt.strip(),
        "nombre":          nombre_txt.strip().lower(),
        "accion":          accion_sel,
    }


def apply_patient_filters(patients: list, filters: dict) -> list:
    """
    Filtra la lista de pacientes procesados según los filtros del sidebar.
    Opera sobre la lista en memoria — no requiere el DataFrame original.
    """
    result = patients

    if filters["red"]:
        red_set = set(filters["red"])
        result = [p for p in result if p["Red"] in red_set]

    if filters["microred"]:
        micro_set = set(filters["microred"])
        result = [p for p in result if p["Microred"] in micro_set]

    if filters["eess"]:
        eess_set = set(filters["eess"])
        result = [p for p in result if p["EESS"] in eess_set]

    if filters["grupo"]:
        grupo_set = set(filters["grupo"])
        result = [p for p in result if p["Grupo"] in grupo_set]

    if filters["sexo"]:
        sexo_set = set(filters["sexo"])
        result = [p for p in result if p["Sexo"] in sexo_set]

    if filters["dni"]:
        result = [p for p in result if filters["dni"] in p["DNI"]]

    if filters["nombre"]:
        result = [p for p in result if filters["nombre"] in p["Nombres"].lower()]

    if filters["accion"]:
        accion_set = set(filters["accion"])
        result = [p for p in result if patient_action_priority(p["vaccines"]) in accion_set]

    return result

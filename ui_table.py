import streamlit as st
import pandas as pd
from vaccine_logic import (
    format_dose_cell, format_single_dose,
    patient_pending_list, patient_action_priority,
    ACTION_LABELS, ERROR_DU, INCUMPLIO, PENDIENTE,
)

# ── Columnas individuales por dosis (orden NTS N°196) ─────────────────────────
# (encabezado_columna, clave_vacuna, índice_dosis_base0 | None=especial)
DOSE_COLUMNS = [
    # Nacimiento
    ("BCG",       "BCG",                  0),
    ("HVB",       "HVB",                  0),
    # 2 meses — esquema base
    ("1° Penta",  "PENTAVALENTE",          0),
    ("2° Penta",  "PENTAVALENTE",          1),
    ("3° Penta",  "PENTAVALENTE",          2),
    ("1° IPV",    "IPV",                   0),
    ("2° IPV",    "IPV",                   1),
    ("3° IPV",    "IPV",                   2),
    ("Ref. IPV",  "IPV",                   3),
    ("1° Rota",   "ROTAVIRUS",             0),
    ("2° Rota",   "ROTAVIRUS",             1),
    ("1° Neumo",  "NEUMOCOCO",             0),
    ("2° Neumo",  "NEUMOCOCO",             1),
    ("3° Neumo",  "NEUMOCOCO",             2),
    ("1° HiB",    "HiB",                   0),
    ("2° HiB",    "HiB",                   1),
    ("3° HiB",    "HiB",                   2),
    ("Ref. HiB",  "HiB",                   3),
    # Influenza (lógica especial — puede tener 1 o 2 resultados)
    ("Inf.Ped",   "INFLUENZA PEDIATRICA",  None),
    ("Inf.Adu",   "INFLUENZA ADULTO",      None),
    # 12 – 15 meses
    ("1° SPR",    "SPR",                   0),
    ("2° SPR",    "SPR",                   1),
    ("Varicela",  "VARICELA",              0),
    ("Hep.A",     "HEPATITIS A",           0),
    ("Amaril.",   "AMARILICA",             0),
    # 18 meses – 7 años
    ("1° DPT",    "DPT",                   0),
    ("2° DPT",    "DPT",                   1),
    ("APO",       "APO",                   0),
    ("1° dT",     "dT",                    0),
    ("2° dT",     "dT",                    1),
    ("3° dT",     "dT",                    2),
]

_VAX_COLS = [h for h, _, __ in DOSE_COLUMNS]


# ── Construcción del DataFrame ────────────────────────────────────────────────

def build_display_df(processed_patients: list) -> pd.DataFrame:
    rows = []
    for p in processed_patients:
        row = {
            "Prioridad":         patient_action_priority(p["vaccines"]),
            "Vacunas a atender": patient_pending_list(p["vaccines"]) or "—",
            "DNI":               p["DNI"],
            "Nombres":           p["Nombres"],
            "Sexo":              p["Sexo"],
            "F.Nacimiento":      p["F_Nacimiento"],
            "Edad":              p["Edad"],
            "Grupo":             p["Grupo"],
            "RIS":               p["Red"],
            "Zona Sanitaria":    p["Microred"],
            "EESS":              p["EESS"],
        }
        for col_header, vax_key, dose_idx in DOSE_COLUMNS:
            results = p["vaccines"].get(vax_key, [])
            if dose_idx is None:
                # Influenza: mostrar líneas múltiples si aplica
                row[col_header] = format_dose_cell(results)
            elif dose_idx < len(results):
                row[col_header] = format_single_dose(results[dose_idx])
            else:
                row[col_header] = "N/C"
        rows.append(row)
    return pd.DataFrame(rows)


# ── Métricas desglosadas ──────────────────────────────────────────────────────

def render_summary(processed_patients: list) -> None:
    total     = len(processed_patients)
    errores   = sum(1 for p in processed_patients
                    if patient_action_priority(p["vaccines"]) == ACTION_LABELS[ERROR_DU])
    recuperar = sum(1 for p in processed_patients
                    if patient_action_priority(p["vaccines"]) == ACTION_LABELS[INCUMPLIO])
    vacunar   = sum(1 for p in processed_patients
                    if patient_action_priority(p["vaccines"]) == ACTION_LABELS[PENDIENTE])
    completos = total - errores - recuperar - vacunar

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total)
    c2.metric("🔴 Corregir registro", errores,
              help="Vacuna registrada con etiqueta incorrecta (ej. '1ra' en lugar de 'DU')")
    c3.metric("❌ Recuperar", recuperar,
              help="Incumplió la ventana ideal, pero aún puede vacunarse")
    c4.metric("⚠️ Vacunar", vacunar,
              help="Dosis pendiente dentro del plazo normal")
    c5.metric("✅ Completo", completos)


# ── Tabla principal ───────────────────────────────────────────────────────────

def render_patient_table(processed_patients: list) -> None:
    if not processed_patients:
        st.warning("No hay pacientes con los filtros aplicados.")
        return

    render_summary(processed_patients)
    st.divider()

    display_df = build_display_df(processed_patients)

    col_config = {
        "Prioridad":         st.column_config.TextColumn("Prioridad",         width="medium"),
        "Vacunas a atender": st.column_config.TextColumn("Vacunas a atender", width="large"),
        "DNI":               st.column_config.TextColumn("DNI",               width="small"),
        "Nombres":           st.column_config.TextColumn("Nombres",           width="medium"),
        "F.Nacimiento":      st.column_config.TextColumn("F.Nac.",            width="small"),
        "Edad":              st.column_config.TextColumn("Edad",              width="small"),
        "Grupo":             st.column_config.TextColumn("Grupo",             width="small"),
    }
    # Columnas de vacunas: ancho automático según contenido
    for col_header in _VAX_COLS:
        col_config[col_header] = st.column_config.TextColumn(col_header, width="medium")

    st.dataframe(
        display_df,
        use_container_width=True,
        height=700,
        column_config=col_config,
        hide_index=True,
    )

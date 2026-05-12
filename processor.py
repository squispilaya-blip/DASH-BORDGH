# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st

from parser import (
    load_excel, parse_doses, format_age_from_birth,
    age_days_from_birth, get_age_group, VACCINE_COLUMNS,
)
from vaccine_logic import get_vaccine_status


@st.cache_data(show_spinner="Cargando y procesando padrón...")
def build_all(file_bytes: bytes) -> tuple[pd.DataFrame, list]:
    """
    Carga el Excel, calcula columnas derivadas y procesa todos los pacientes.

    Retorna:
        df             — DataFrame con columnas derivadas (_edad_str, _edad_days, _grupo)
        all_processed  — Lista de dicts de pacientes con estados de vacunas

    Nota NTS: las fechas de dosis en el futuro representan dosis programadas
    aún no administradas. Se tratan correctamente como PENDIENTE según la
    NTS N°196-MINSA/DGIESP-2022 (no se cuentan como APLICADA).
    """
    df = load_excel(file_bytes)
    df["_edad_str"]  = df["NINO_FECNAC"].apply(format_age_from_birth)
    df["_edad_days"] = df["NINO_FECNAC"].apply(age_days_from_birth)
    df["_grupo"]     = df["NINO_FECNAC"].apply(get_age_group)

    all_processed = []
    for _, row in df.iterrows():
        age_d      = int(row["_edad_days"])
        birth_date = row["NINO_FECNAC"]
        vaccines = {
            col: get_vaccine_status(col, parse_doses(row.get(col)), age_d, birth_date)
            for col in VACCINE_COLUMNS
        }
        all_processed.append({
            "DNI":          str(row["DNI"]),
            "Nombres":      str(row["NOMBRES"]),
            "Sexo":         str(row["SEXO"]),
            "F_Nacimiento": row["NINO_FECNAC"].strftime("%d/%m/%Y"),
            "Edad":         row["_edad_str"],
            "Grupo":        row["_grupo"],
            "Red":          str(row["RED"]),
            "Microred":     str(row["MICRORED"]),
            "EESS":         str(row["EESS_ATN"]),
            "vaccines":     vaccines,
        })

    return df, all_processed

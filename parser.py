"""
parser.py — Módulo de carga y parseo del padrón de vacunación.

Funciones principales:
- load_excel: carga el archivo Excel desde bytes y normaliza columnas.
- parse_doses: parsea el string de dosis de una celda de vacuna.
- age_days_from_birth: días de vida desde la fecha de nacimiento.
- calculate_age_parts: (años, meses, días) usando relativedelta.
- format_age: formatea (años, meses, días) como "Xa Xm Xd".
- format_age_from_birth: formato de edad a partir de la fecha de nacimiento.
- get_age_group: grupo etario en años (< 1 año, 1 año, …, 4 años).
"""

import re
import io
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pandas as pd

VACCINE_COLUMNS = [
    # Nacimiento
    "BCG", "HVB",
    # 2 meses — esquema base
    "PENTAVALENTE", "IPV", "ROTAVIRUS", "NEUMOCOCO", "HiB",
    # 6 meses
    "INFLUENZA PEDIATRICA", "INFLUENZA ADULTO",
    # 12 – 15 meses
    "SPR", "VARICELA", "HEPATITIS A", "AMARILICA",
    # 18 meses – 7 años
    "DPT", "APO", "dT",
]

INFO_COLUMNS = [
    "TIPO", "DNI", "NOMBRES", "SEXO", "NINO_FECNAC",
    "RED", "MICRORED", "RENAES_ATN", "EESS_ATN", "FECHA_CORTE_PADRON_N",
]


def parse_doses(cell_value) -> list:
    """
    Parsea el valor de una celda de vacuna.

    Ejemplos:
        '1ra (29/05/2023), 2da (30/07/2023)' → [('1ra', date(2023,5,29)), ...]
        'DU (29/12/2024)'                     → [('DU', date(2024,12,29))]

    Retorna lista vacía si el valor es None, NaN o string vacío.
    """
    # Rechazar None, NaN (float) y strings vacíos/blancos
    if cell_value is None:
        return []
    if isinstance(cell_value, float):
        # cubre float('nan') y cualquier otro float
        return []
    if not isinstance(cell_value, str) or not cell_value.strip():
        return []

    # [\w-]+ captura etiquetas compuestas como "1er-R" además de "1ra", "DU", "DA"
    pattern = r'([\w-]+)\s*\((\d{2}/\d{2}/\d{4})\)'
    matches = re.findall(pattern, cell_value)
    result = []
    today = date.today()
    for label, date_str in matches:
        try:
            d = datetime.strptime(date_str, "%d/%m/%Y").date()
            if d > today:
                continue  # ignorar fechas futuras — dato incorrecto en el padrón
            result.append((label.strip(), d))
        except ValueError:
            pass
    return result


def age_days_from_birth(birth_date: date) -> int:
    """Días de vida desde la fecha de nacimiento hasta hoy."""
    return (date.today() - birth_date).days


def calculate_age_parts(birth_date: date) -> tuple:
    """Retorna (años, meses, días) usando relativedelta."""
    rd = relativedelta(date.today(), birth_date)
    return rd.years, rd.months, rd.days


def format_age(years: int, months: int, days: int) -> str:
    """Formatea componentes de edad como '3a 2m 15d'."""
    return f"{years}a {months}m {days}d"


def format_age_from_birth(birth_date: date) -> str:
    """Retorna la edad formateada a partir de la fecha de nacimiento."""
    y, m, d = calculate_age_parts(birth_date)
    return format_age(y, m, d)


def get_age_group(birth_date: date) -> str:
    """
    Clasifica al paciente en un grupo etario basado en días de vida.

    Grupos:
        < 365 días  → '< 1 año'
        365–729     → '1 año'
        730–1094    → '2 años'
        1095–1459   → '3 años'
        1460–1824   → '4 años'
        1825–2189   → '5 años'
        2190+       → '≥ 6 años'

    Los grupos ≥ 5 años cubren vacunas dT (desde 7 años) y Amarílica
    (hasta 59 años) contempladas en la NTS N°196-MINSA/DGIESP-2022.
    """
    days = age_days_from_birth(birth_date)
    if days < 0:
        return "< 1 año"  # fecha de nacimiento futura — dato incorrecto
    if days < 365:
        return "< 1 año"
    elif days < 730:
        return "1 año"
    elif days < 1095:
        return "2 años"
    elif days < 1460:
        return "3 años"
    elif days < 1825:
        return "4 años"
    elif days < 2190:
        return "5 años"
    else:
        return "≥ 6 años"


def load_excel(file_content: bytes) -> pd.DataFrame:
    """
    Carga el padrón Excel desde bytes.

    - Hoja: "Consulta2"
    - Normaliza NINO_FECNAC y FECHA_CORTE_PADRON_N a date.
    - Descarta columnas de fórmulas Excel ('Edad_A', 'EDAD ACTUAL').
    - Lee DNI como string para preservar ceros a la izquierda.
    - Elimina filas sin fecha de nacimiento válida.
    """
    try:
        df = pd.read_excel(
            io.BytesIO(file_content),
            sheet_name="Consulta2",
            engine="openpyxl",
            dtype={"DNI": str},
        )
    except Exception as exc:
        raise ValueError(
            "El archivo debe contener la hoja 'Consulta2'. "
            f"Verifica que estás cargando el padrón correcto. ({exc})"
        ) from exc

    # Descartar columnas de fórmulas Excel que no se evalúan
    for col in ["Edad_A", "EDAD ACTUAL"]:
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    df["NINO_FECNAC"] = pd.to_datetime(df["NINO_FECNAC"], errors="coerce").dt.date
    df["FECHA_CORTE_PADRON_N"] = pd.to_datetime(
        df["FECHA_CORTE_PADRON_N"], errors="coerce"
    ).dt.date

    # Eliminar filas sin fecha de nacimiento válida
    df = df[df["NINO_FECNAC"].notna()].copy()
    df.reset_index(drop=True, inplace=True)
    return df

# -*- coding: utf-8 -*-
"""
comparador_exportado.py — Comparación de dos reportes Excel exportados
del dashboard de vacunación.

Los archivos de entrada son reportes ya procesados (no el padrón crudo),
con columnas de dosis individuales como 'BCG', '1° Penta', 'Varicela', etc.
"""

import io
import re
import datetime
import pandas as pd

# ── Columnas de dosis en el orden del reporte exportado ──────────────────────
DOSE_COLS = [
    'BCG', 'HVB',
    '1° Penta', '2° Penta', '3° Penta',
    '1° IPV',   '2° IPV',   '3° IPV',   'Ref. IPV',
    '1° Rota',  '2° Rota',
    '1° Neumo', '2° Neumo', '3° Neumo',
    '1° HiB',   '2° HiB',   '3° HiB',   'Ref. HiB',
    'Inf.Ped',  'Inf.Adu',
    '1° SPR',   '2° SPR',
    'Varicela', 'Hep.A', 'Amaril.',
    '1° DPT',   '2° DPT',
    'APO',
]

# ── Estados internos ──────────────────────────────────────────────────────────
ST_APLICADA      = 'APLICADA'
ST_PENDIENTE     = 'PENDIENTE'
ST_INCUMPLIO     = 'INCUMPLIÓ'
ST_FUERA_EDAD    = 'FUERA DE EDAD'
ST_NO_APLICA     = 'NO APLICA AÚN'
ST_NO_CORRESPONDE = 'N/C'
ST_ERROR         = 'ERROR'

NEEDS_VACCINE = {ST_PENDIENTE, ST_INCUMPLIO, ST_ERROR}
IS_APPLIED    = {ST_APLICADA}


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_status(val) -> str:
    """
    Determina el estado vacunal a partir del valor de una celda
    del reporte exportado.

    Valores posibles:
      '✅ 08/04/2026'            → APLICADA
      '🕐 08/04/2026 (tardía)'   → APLICADA
      '⚠️ Pendiente · ...'       → PENDIENTE
      '❌ Incumplió · ...'       → INCUMPLIÓ
      '🚫 Vencida'               → FUERA DE EDAD
      '🔴 Error reg. ...'        → ERROR
      '— ...' / datetime / fecha → NO APLICA AÚN
      'N/C'                      → N/C
    """
    if val is None:
        return ST_NO_CORRESPONDE
    if isinstance(val, float):
        return ST_NO_CORRESPONDE if pd.isna(val) else ST_NO_APLICA
    if isinstance(val, (datetime.datetime, datetime.date)):
        return ST_NO_APLICA

    s = str(val).strip()
    if not s or s in ('nan', 'None', 'NaN'):
        return ST_NO_CORRESPONDE

    # Aplicada (emojis verdes)
    if s.startswith('✅') or s.startswith('🕐'):
        return ST_APLICADA

    # Error de registro
    if '🔴' in s or 'Error reg' in s:
        return ST_ERROR

    # Incumplió
    if '❌' in s or 'Incumplió' in s:
        return ST_INCUMPLIO

    # Fuera de edad
    if '🚫' in s or 'Vencida' in s:
        return ST_FUERA_EDAD

    # Pendiente
    if '⚠️' in s or 'Pendiente' in s:
        return ST_PENDIENTE

    # No corresponde
    if s in ('N/C', 'N/A'):
        return ST_NO_CORRESPONDE

    # No aplica aún (fecha programada o "—")
    if s.startswith('—') or s == '—':
        return ST_NO_APLICA

    # Cadena de solo fecha "dd/mm/yyyy" (fecha programada exportada como texto)
    if re.match(r'^\d{2}/\d{2}/\d{4}$', s):
        return ST_NO_APLICA

    # Texto del tipo "DA anual: 08/01/2026" → dosis aplicada
    if re.search(r'\d{2}/\d{2}/\d{4}', s):
        return ST_APLICADA

    return ST_NO_CORRESPONDE


def load_reporte(file_bytes: bytes) -> pd.DataFrame:
    """
    Carga un reporte Excel exportado desde el dashboard.

    Espera cualquier hoja (sheet_name=0) con columnas:
    DNI, Nombres, RIS, Zona Sanitaria, EESS, Prioridad + columnas de dosis.
    """
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, dtype={'DNI': str})
    if 'DNI' in df.columns:
        df['DNI'] = df['DNI'].astype(str).str.strip()
    return df


def get_dose_cols_in(df: pd.DataFrame) -> list[str]:
    """Devuelve las columnas de dosis presentes en el DataFrame."""
    return [c for c in DOSE_COLS if c in df.columns]


def compare_reportes(df_a: pd.DataFrame, df_b: pd.DataFrame) -> list[dict]:
    """
    Compara dos reportes exportados por DNI.

    Devuelve una lista de dicts, uno por paciente relevante:
        DNI, Nombres, RIS, Zona Sanitaria, EESS, Prioridad,
        se_vacuno         — bool: al menos 1 dosis pasó de PENDIENTE/INCUMPLIÓ → APLICADA
        sigue_faltando    — bool: al menos 1 dosis sigue en PENDIENTE/INCUMPLIÓ en el nuevo reporte
        vacunas_administradas — list[str]: dosis recién vacunadas
        vacunas_pendientes    — list[str]: dosis que siguen pendientes
        categoria         — 'se_vacuno' | 'sigue_faltando' | 'parcial' | 'nuevo' | 'retirado'
        en_a, en_b        — bool: presencia en cada reporte
    """
    # Columnas de dosis: unión de ambos reportes en el orden de DOSE_COLS
    cols_a = set(get_dose_cols_in(df_a))
    cols_b = set(get_dose_cols_in(df_b))
    dose_cols = [c for c in DOSE_COLS if c in cols_a | cols_b]

    dict_a = {str(r['DNI']).strip(): r for _, r in df_a.iterrows() if pd.notna(r.get('DNI'))}
    dict_b = {str(r['DNI']).strip(): r for _, r in df_b.iterrows() if pd.notna(r.get('DNI'))}
    all_dnis = sorted(set(dict_a) | set(dict_b))

    results = []
    for dni in all_dnis:
        in_a = dni in dict_a
        in_b = dni in dict_b
        row_a = dict_a.get(dni)
        row_b = dict_b.get(dni)
        ref   = row_b if row_b is not None else row_a  # datos descriptivos del paciente

        base = {
            'DNI':           dni,
            'Nombres':       str(ref.get('Nombres', '')),
            'RIS':           str(ref.get('RIS', '')),
            'Zona Sanitaria': str(ref.get('Zona Sanitaria', '')),
            'EESS':          str(ref.get('EESS', '')),
            'Prioridad':     str(row_b.get('Prioridad', '') if row_b is not None else ''),
            'en_a': in_a,
            'en_b': in_b,
        }

        # Paciente nuevo (solo en B)
        if in_b and not in_a:
            pendientes = [c for c in dose_cols if parse_status(row_b.get(c)) in NEEDS_VACCINE]
            base.update({
                'se_vacuno': False,
                'sigue_faltando': bool(pendientes),
                'vacunas_administradas': [],
                'vacunas_pendientes': pendientes,
                'categoria': 'nuevo',
            })
            results.append(base)
            continue

        # Paciente retirado (solo en A)
        if in_a and not in_b:
            base.update({
                'se_vacuno': False,
                'sigue_faltando': False,
                'vacunas_administradas': [],
                'vacunas_pendientes': [],
                'categoria': 'retirado',
            })
            results.append(base)
            continue

        # Paciente en ambos reportes — comparar dosis
        administradas = []
        pendientes    = []
        for col in dose_cols:
            st_a = parse_status(row_a.get(col))
            st_b = parse_status(row_b.get(col))
            if st_a in NEEDS_VACCINE and st_b in IS_APPLIED:
                administradas.append(col)
            if st_b in NEEDS_VACCINE:
                pendientes.append(col)

        se_vacuno      = bool(administradas)
        sigue_faltando = bool(pendientes)

        # Solo incluir pacientes con algo relevante
        if not se_vacuno and not sigue_faltando:
            continue

        if se_vacuno and sigue_faltando:
            categoria = 'parcial'
        elif se_vacuno:
            categoria = 'se_vacuno'
        else:
            categoria = 'sigue_faltando'

        base.update({
            'se_vacuno':            se_vacuno,
            'sigue_faltando':       sigue_faltando,
            'vacunas_administradas': administradas,
            'vacunas_pendientes':   pendientes,
            'categoria':            categoria,
        })
        results.append(base)

    return results


def to_dataframe(results: list[dict], dose_filter: list[str] | None = None,
                 cat_filter: str | None = None) -> pd.DataFrame:
    """
    Una fila por niño. Una columna por vacuna con su estado individual.

    Columnas fijas  : RIS, Zona Sanitaria, EESS, DNI, Nombres,
                      Prioridad actual, Categoría
    Columnas de dosis (dinámicas, en orden de DOSE_COLS):
        '✅ Vacunado'  — pasó de PENDIENTE/INCUMPLIÓ → APLICADA en este periodo
        '❌ Pendiente' — sigue pendiente en el segundo reporte
        ''             — no aplica / no tiene ese estado relevante

    dose_filter — muestra solo esas columnas de vacuna (None = todas las presentes)
    cat_filter  — 'se_vacuno' | 'sigue_faltando' | 'parcial' | None (todos)
    """
    BASE_COLS = ['RIS', 'Zona Sanitaria', 'EESS', 'DNI', 'Nombres',
                 'Prioridad actual', 'Categoría']

    rows = []
    for r in results:
        if cat_filter and r['categoria'] not in _cat_keys(cat_filter):
            continue

        administradas = set(r.get('vacunas_administradas', []))
        pendientes    = set(r.get('vacunas_pendientes',    []))
        all_relevant  = administradas | pendientes

        # Filtrar por vacuna específica
        if dose_filter:
            if not all_relevant.intersection(dose_filter):
                continue
        elif not all_relevant:
            # Niños sin dosis relevantes (nuevo sin pendientes, retirado)
            rows.append({
                'RIS':              r['RIS'],
                'Zona Sanitaria':   r['Zona Sanitaria'],
                'EESS':             r['EESS'],
                'DNI':              r['DNI'],
                'Nombres':          r['Nombres'],
                'Prioridad actual': r['Prioridad'],
                'Categoría':        _cat_label(r['categoria']),
            })
            continue

        row: dict = {
            'RIS':              r['RIS'],
            'Zona Sanitaria':   r['Zona Sanitaria'],
            'EESS':             r['EESS'],
            'DNI':              r['DNI'],
            'Nombres':          r['Nombres'],
            'Prioridad actual': r['Prioridad'],
            'Categoría':        _cat_label(r['categoria']),
        }

        # Una columna por dosis, en el orden estándar de DOSE_COLS
        doses_to_check = dose_filter if dose_filter else DOSE_COLS
        for dose in doses_to_check:
            if dose in administradas:
                row[dose] = '✅ Vacunado'
            elif dose in pendientes:
                row[dose] = '❌ Pendiente'
            # Si no aplica → la celda queda vacía (NaN → '' tras fillna)

        rows.append(row)

    if not rows:
        return pd.DataFrame(columns=BASE_COLS)

    df = pd.DataFrame(rows)

    # Rellenar NaN con '' en columnas de dosis
    dose_cols_in_df = [c for c in DOSE_COLS if c in df.columns]
    if dose_cols_in_df:
        df[dose_cols_in_df] = df[dose_cols_in_df].fillna('')
        # Sin filtro específico: eliminar columnas de dosis completamente vacías
        if not dose_filter:
            empty = [c for c in dose_cols_in_df if (df[c] == '').all()]
            df = df.drop(columns=empty)

    return df


def _cat_keys(label: str) -> set[str]:
    """Mapea label de UI → claves internas de categoría."""
    return {
        'se_vacuno':      {'se_vacuno', 'parcial'},
        'sigue_faltando': {'sigue_faltando', 'parcial'},
        'parcial':        {'parcial'},
    }.get(label, {'se_vacuno', 'sigue_faltando', 'parcial', 'nuevo', 'retirado'})


def _cat_label(cat: str) -> str:
    return {
        'se_vacuno':      '✅ Se vacunó',
        'sigue_faltando': '❌ Sigue faltando',
        'parcial':        '⚠️ Parcial (vacunó + falta)',
        'nuevo':          '➕ Nuevo en padrón',
        'retirado':       '➖ Retirado del padrón',
    }.get(cat, cat)


# ── Informe estadístico ───────────────────────────────────────────────────────

def build_summary_df(df_a: pd.DataFrame, df_b: pd.DataFrame,
                     results: list[dict]) -> pd.DataFrame:
    """
    Genera un resumen estadístico detallado por EESS con totales RIS.

    Columnas resultantes:
      RIS | EESS
      Total Reporte A (1er corte)   — niños en el primer archivo
      Total Reporte B (2do corte)   — niños en el segundo archivo
      Vacunados en el periodo       — cambiaron de PENDIENTE/INCUMPLIÓ → APLICADA
                                      (incluye los "parciales")
      Parcialmente vacunados        — vacunaron algunas dosis, aún faltan otras
      Nuevos niños ingresados       — aparecen en B pero no en A
      No vacunados en el periodo    — siguen con dosis pendientes sin vacunarse
      Retirados del padrón          — estaban en A pero no en B
    """
    def _eess_counts(df: pd.DataFrame) -> dict:
        if 'EESS' not in df.columns:
            return {}
        return df.groupby('EESS', sort=False).size().to_dict()

    counts_a = _eess_counts(df_a)
    counts_b = _eess_counts(df_b)

    # Mapa EESS → RIS (preferir df_b, luego df_a)
    ris_by_eess: dict[str, str] = {}
    for df in (df_a, df_b):
        if 'EESS' in df.columns and 'RIS' in df.columns:
            for _, row in df[['EESS', 'RIS']].drop_duplicates().iterrows():
                ris_by_eess[str(row['EESS'])] = str(row['RIS'])

    # Estadísticas por EESS desde los resultados de comparación
    stats: dict[str, dict] = {}
    for r in results:
        eess = str(r['EESS'])
        if eess not in stats:
            stats[eess] = {
                'vacunados': 0, 'parciales': 0,
                'nuevos': 0, 'no_vacunados': 0, 'retirados': 0,
            }
        cat = r['categoria']
        if cat == 'se_vacuno':
            stats[eess]['vacunados'] += 1
        elif cat == 'parcial':
            stats[eess]['vacunados'] += 1
            stats[eess]['parciales'] += 1
        elif cat == 'nuevo':
            stats[eess]['nuevos'] += 1
        elif cat == 'sigue_faltando':
            stats[eess]['no_vacunados'] += 1
        elif cat == 'retirado':
            stats[eess]['retirados'] += 1

    all_eess = sorted(
        set(list(counts_a) + list(counts_b) + list(stats)),
        key=lambda e: (ris_by_eess.get(e, ''), e)
    )

    rows = []
    for eess in all_eess:
        s = stats.get(eess, {
            'vacunados': 0, 'parciales': 0,
            'nuevos': 0, 'no_vacunados': 0, 'retirados': 0,
        })
        rows.append({
            'RIS':                           ris_by_eess.get(eess, ''),
            'EESS':                          eess,
            'Total Reporte A (1er corte)':   counts_a.get(eess, 0),
            'Total Reporte B (2do corte)':   counts_b.get(eess, 0),
            'Vacunados en el periodo':       s['vacunados'],
            'Parcialmente vacunados':        s['parciales'],
            'Nuevos niños ingresados':       s['nuevos'],
            'No vacunados en el periodo':    s['no_vacunados'],
            'Retirados del padrón':          s['retirados'],
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        num_cols = [
            'Total Reporte A (1er corte)', 'Total Reporte B (2do corte)',
            'Vacunados en el periodo', 'Parcialmente vacunados',
            'Nuevos niños ingresados', 'No vacunados en el periodo',
            'Retirados del padrón',
        ]
        total_row: dict = {'RIS': 'TOTAL GENERAL', 'EESS': '—'}
        for col in num_cols:
            total_row[col] = int(df[col].sum())
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    return df

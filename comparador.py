# -*- coding: utf-8 -*-
"""
comparador.py — Lógica de comparación entre dos padrones de vacunación.

Identifica por DNI:
  - nuevo_vacunado:  pasó de PENDIENTE/INCUMPLIÓ → APLICADA entre reportes
  - nuevo_padron:    DNI presente en B pero no en A
  - retirado_padron: DNI presente en A pero no en B
  - otro_cambio:     cualquier otro cambio de estado vacunal
"""

from collections import defaultdict

import pandas as pd

from parser import VACCINE_COLUMNS
from vaccine_logic import APLICADA, APLICADA_TARDIA, PENDIENTE, INCUMPLIO

_MEJORADO_DESDE = {PENDIENTE, INCUMPLIO}
_MEJORADO_HACIA = {APLICADA, APLICADA_TARDIA}

_STATUS_LABEL = {
    APLICADA:              "Aplicada",
    APLICADA_TARDIA:       "Aplicada (tardía)",
    PENDIENTE:             "Pendiente",
    INCUMPLIO:             "Incumplió",
    "FUERA DE EDAD":       "Fuera de edad",
    "NO APLICA AÚN":       "No aplica aún",
    "NO CORRESPONDE":      "No corresponde",
    "ERROR: DEBE SER DU":  "Error registro",
}

CATEGORIAS = {
    "nuevo_vacunado":  "✅ Nuevos vacunados",
    "nuevo_padron":    "➕ Nuevos en padrón",
    "retirado_padron": "➖ Retirados del padrón",
    "otro_cambio":     "🔄 Otros cambios",
}


def compare_reports(patients_a: list, patients_b: list) -> list:
    """
    Compara dos listas de pacientes procesados usando DNI como clave.

    Cada elemento retornado es un dict con:
        DNI, Nombres, Red, Microred, EESS,
        categoria: uno de las claves de CATEGORIAS
        vacunas_cambiadas: list[dict] con {vacuna, label, estado_anterior, estado_nuevo}
        detalle: str resumen legible de los cambios
    """
    dict_a = {p["DNI"]: p for p in patients_a}
    dict_b = {p["DNI"]: p for p in patients_b}
    all_dnis = sorted(set(dict_a) | set(dict_b))
    changes = []

    for dni in all_dnis:
        in_a = dni in dict_a
        in_b = dni in dict_b

        if in_b and not in_a:
            changes.append(_entry(dict_b[dni], "nuevo_padron", []))
            continue

        if in_a and not in_b:
            changes.append(_entry(dict_a[dni], "retirado_padron", []))
            continue

        dose_changes = _diff_vaccines(dict_a[dni]["vaccines"], dict_b[dni]["vaccines"])
        if not dose_changes:
            continue

        has_vaccination = any(
            c["estado_anterior"] in _MEJORADO_DESDE and c["estado_nuevo"] in _MEJORADO_HACIA
            for c in dose_changes
        )
        categoria = "nuevo_vacunado" if has_vaccination else "otro_cambio"
        changes.append(_entry(dict_b[dni], categoria, dose_changes))

    return changes


def summary_by_ris(changes: list) -> pd.DataFrame:
    """Resumen de cambios agrupado por RIS (una fila por Red)."""
    cols = list(CATEGORIAS.values())
    stats: dict = defaultdict(lambda: dict.fromkeys(cols, 0))

    for c in changes:
        ris   = c["Red"]
        label = CATEGORIAS.get(c["categoria"], "🔄 Otros cambios")
        stats[ris][label] += 1

    rows = [
        {"RIS": ris, **s, "Total": sum(s.values())}
        for ris, s in sorted(stats.items())
    ]
    return (
        pd.DataFrame(rows)
        if rows
        else pd.DataFrame(columns=["RIS"] + cols + ["Total"])
    )


# ── Helpers privados ──────────────────────────────────────────────────────────

def _entry(patient: dict, categoria: str, dose_changes: list) -> dict:
    detalle = "; ".join(
        f"{c['vacuna']} ({c['label']}): "
        f"{_STATUS_LABEL.get(c['estado_anterior'], c['estado_anterior'] or '—')} → "
        f"{_STATUS_LABEL.get(c['estado_nuevo'], c['estado_nuevo'] or '—')}"
        for c in dose_changes
    ) or "—"
    return {
        "DNI":               patient["DNI"],
        "Nombres":           patient["Nombres"],
        "Red":               patient["Red"],
        "Microred":          patient["Microred"],
        "EESS":              patient["EESS"],
        "categoria":         categoria,
        "vacunas_cambiadas": dose_changes,
        "detalle":           detalle,
    }


def _diff_vaccines(vax_a: dict, vax_b: dict) -> list:
    """Compara dosis vacuna por vacuna y retorna solo las que cambiaron."""
    dose_changes = []
    for vcol in VACCINE_COLUMNS:
        doses_a = vax_a.get(vcol, [])
        doses_b = vax_b.get(vcol, [])
        for i in range(max(len(doses_a), len(doses_b))):
            da = doses_a[i] if i < len(doses_a) else None
            db = doses_b[i] if i < len(doses_b) else None
            sa = da["status"] if da else None
            sb = db["status"] if db else None
            if sa != sb:
                dose_changes.append({
                    "vacuna":          vcol,
                    "label":           (db or da)["label"],
                    "estado_anterior": sa,
                    "estado_nuevo":    sb,
                })
    return dose_changes

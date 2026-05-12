# -*- coding: utf-8 -*-
from datetime import date, timedelta
from typing import Optional

# ─── Constantes de estado ────────────────────────────────────────────────────
APLICADA       = "APLICADA"
PENDIENTE      = "PENDIENTE"
FUERA_EDAD     = "FUERA DE EDAD"
NO_APLICA_AUN  = "NO APLICA AÚN"
NO_CORRESPONDE = "NO CORRESPONDE"
ERROR_DU        = "ERROR: DEBE SER DU"
APLICADA_TARDIA = "APLICADA TARDÍA"
INCUMPLIO       = "INCUMPLIÓ"

# Íconos para la tabla del dashboard
STATUS_ICONS = {
    APLICADA:        "✅",
    APLICADA_TARDIA: "🕐",
    PENDIENTE:       "⚠️",
    INCUMPLIO:       "❌",
    FUERA_EDAD:      "🚫",
    NO_APLICA_AUN:   "—",
    NO_CORRESPONDE:  "N/A",
    ERROR_DU:        "🔴",
}

# Colores de fondo para Excel exportado (hex sin #)
STATUS_COLORS = {
    APLICADA:        "C6EFCE",   # verde claro — vacunado a tiempo
    APLICADA_TARDIA: "FFD966",   # dorado — vacunado fuera de ventana ideal
    PENDIENTE:       "FFEB9C",   # amarillo — por vacunar (aún en ventana)
    INCUMPLIO:       "FFC7CE",   # rosa-rojo — incumplió ventana ideal
    FUERA_EDAD:      "FFCC99",   # naranja — sin posibilidad de recuperación
    NO_APLICA_AUN:   "FFFFFF",   # blanco
    NO_CORRESPONDE:  "F2F2F2",   # gris claro
    ERROR_DU:        "FF0000",   # rojo — error de registro
}

# ─── Umbrales de edad en días ─────────────────────────────────────────────────
M2  = 60;   M4  = 120;  M6  = 182;  M7  = 213;  M8  = 243
M12 = 365;  M15 = 456;  M18 = 547;  M23 = 700
Y2  = 730;  Y3  = 1095; Y4  = 1460; Y5  = 1825; Y7  = 2555

# ─── Esquema NTS N°196-MINSA/DGIESP-2022 ─────────────────────────────────────
# seq:      número de dosis (1-based)
# label:    etiqueta esperada según norma
# min_days: edad mínima en días — también representa la FECHA PROGRAMADA según NTS
# max_days: edad máxima en días (None = sin límite superior)
# is_du:    True si la vacuna es de dosis única (etiqueta correcta: "DU")
SCHEME = {
    # NTS §6.1.1.1: DU al nacer. Si no recibió en el 1er año → administrar hasta
    # los 5 años cumplidos, previo descarte de tuberculosis (pág. 9).
    # ideal_max_days: ventana ideal según NTS (al nacer, dentro de las primeras 24h)
    # max_days: hasta cuándo la NTS permite recuperar la dosis
    "BCG": [
        {"seq": 1, "label": "DU", "min_days": 0, "ideal_max_days": 1, "max_days": Y5, "is_du": True},
    ],
    "HVB": [
        {"seq": 1, "label": "DU", "min_days": 0, "ideal_max_days": 1, "max_days": 7,  "is_du": True},
    ],
    "PENTAVALENTE": [
        {"seq": 1, "label": "1ra",   "min_days": M2,       "max_days": Y7,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M4,       "max_days": Y7,     "is_du": False},
        {"seq": 3, "label": "3ra",   "min_days": M6,       "max_days": Y7,     "is_du": False},
    ],
    "IPV": [
        {"seq": 1, "label": "1ra",   "min_days": M2,       "max_days": Y4,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M4,       "max_days": Y4,     "is_du": False},
        {"seq": 3, "label": "3ra",   "min_days": M6,       "max_days": Y4,     "is_du": False},
        {"seq": 4, "label": "DA",    "min_days": M18,      "max_days": None,   "is_du": False},
    ],
    "ROTAVIRUS": [
        {"seq": 1, "label": "1ra",   "min_days": M2,       "max_days": M8,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M4,       "max_days": M8,     "is_du": False},
    ],
    "NEUMOCOCO": [
        {"seq": 1, "label": "1ra",   "min_days": M2,       "max_days": Y4,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M4,       "max_days": M23,    "is_du": False},
        {"seq": 3, "label": "3ra",   "min_days": M12,      "max_days": None,   "is_du": False},
    ],
    "SPR": [
        {"seq": 1, "label": "1ra",   "min_days": M12,      "max_days": Y5,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M18,      "max_days": Y5,     "is_du": False},
    ],
    # NTS §6.1.1.11: "podrán recibirla hasta los 4 años" = antes del 5° cumpleaños
    # (4a 11m 29d = 1824 días). Y4=1460 era incorrecto: marcaba FUERA_EDAD desde
    # los 4 años 1 día. (pág. 20)
    "VARICELA": [
        {"seq": 1, "label": "DU",    "min_days": M12,      "max_days": Y5 - 1, "is_du": True},
    ],
    "HEPATITIS A": [
        {"seq": 1, "label": "DU",    "min_days": M15,      "max_days": Y5,     "is_du": True},
    ],
    "AMARILICA": [
        {"seq": 1, "label": "DU",    "min_days": M15,      "max_days": 59*365, "is_du": True},
    ],
    "DPT": [
        {"seq": 1, "label": "1er R", "min_days": M18,      "max_days": Y7,     "is_du": False},
        {"seq": 2, "label": "2do R", "min_days": Y4,       "max_days": Y7,     "is_du": False},
    ],
    "APO": [
        {"seq": 1, "label": "DA",    "min_days": Y4,       "max_days": Y5,     "is_du": False},
    ],
    "dT": [
        {"seq": 1, "label": "1ra",   "min_days": Y7,       "max_days": None,   "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": Y7 + 60,  "max_days": None,   "is_du": False},
        {"seq": 3, "label": "3ra",   "min_days": Y7 + 180, "max_days": None,   "is_du": False},
    ],
    "HiB": [
        {"seq": 1, "label": "1ra",   "min_days": M2,       "max_days": Y7,     "is_du": False},
        {"seq": 2, "label": "2da",   "min_days": M4,       "max_days": Y7,     "is_du": False},
        {"seq": 3, "label": "3ra",   "min_days": M6,       "max_days": Y7,     "is_du": False},
        {"seq": 4, "label": "DA",    "min_days": M18,      "max_days": Y7,     "is_du": False},
    ],
}


def _dose_status(dose_def: dict, parsed_doses: list, age_days: int,
                 birth_date: Optional[date] = None) -> dict:
    """
    Calcula el estado de una sola dosis esperada.

    Incluye scheduled_date (fecha programada según NTS calculada desde nacimiento)
    y days_late (días de retraso si fue aplicada; negativo = anticipada).
    """
    seq = dose_def["seq"]

    # Fecha programada = fecha de nacimiento + días de edad mínima según NTS
    scheduled_date = (
        birth_date + timedelta(days=dose_def["min_days"]) if birth_date else None
    )

    ideal_max = dose_def.get("ideal_max_days")

    base = {
        "seq":            seq,
        "label":          dose_def["label"],
        "applied_date":   None,
        "applied_label":  None,
        "scheduled_date": scheduled_date,
        "days_late":      None,
        "max_days":       dose_def.get("max_days"),
        "ideal_max_days": ideal_max,
    }

    if len(parsed_doses) >= seq:
        applied_label, applied_date = parsed_doses[seq - 1]
        days_late = (
            (applied_date - scheduled_date).days if scheduled_date else None
        )
        if dose_def["is_du"] and applied_label.upper() != "DU":
            return {**base, "status": ERROR_DU,
                    "applied_date": applied_date, "applied_label": applied_label,
                    "days_late": days_late}
        # Aplicada fuera de la ventana ideal → APLICADA TARDÍA
        if ideal_max is not None and birth_date is not None:
            applied_age = (applied_date - birth_date).days
            if applied_age > ideal_max:
                return {**base, "status": APLICADA_TARDIA,
                        "applied_date": applied_date, "applied_label": applied_label,
                        "days_late": days_late}
        return {**base, "status": APLICADA,
                "applied_date": applied_date, "applied_label": applied_label,
                "days_late": days_late}

    if age_days < dose_def["min_days"]:
        return {**base, "status": NO_APLICA_AUN}

    max_d = dose_def.get("max_days")
    if max_d is not None and age_days > max_d:
        return {**base, "status": FUERA_EDAD}

    # Ya pasó la ventana ideal pero aún dentro de la ventana de recuperación
    if ideal_max is not None and age_days > ideal_max:
        return {**base, "status": INCUMPLIO}

    return {**base, "status": PENDIENTE}


def _influenza_status(column: str, parsed_doses: list, age_days: int,
                      birth_date: Optional[date] = None) -> list:
    """Lógica especial para influenza pediátrica y adulto."""
    current_year = date.today().year
    applied_years = {d.year for _, d in parsed_doses}
    has_current   = current_year in applied_years

    def _sched(min_days: int) -> Optional[date]:
        return birth_date + timedelta(days=min_days) if birth_date else None

    def _annual_sched() -> date:
        # Campaña anual de influenza en Perú: aproximadamente abril de cada año
        return date(current_year, 4, 1)

    def _annual_entry() -> dict:
        dt      = next((d for _, d in parsed_doses if d.year == current_year), None)
        lbl     = next((l for l, d in parsed_doses if d.year == current_year), None)
        st_     = APLICADA if has_current else PENDIENTE
        sched   = _annual_sched()
        dl      = (dt - sched).days if (dt and sched) else None
        return {
            "seq": 1, "label": "DA anual", "status": st_,
            "applied_date": dt, "applied_label": lbl,
            "scheduled_date": sched, "days_late": dl,
        }

    _empty = {"applied_date": None, "applied_label": None, "days_late": None}
    _na = {"seq": 1, "label": "—", "status": NO_APLICA_AUN,
           "scheduled_date": _sched(M6), **_empty}
    _nc = {"seq": 1, "label": "—", "status": NO_CORRESPONDE,
           "scheduled_date": None, **_empty}

    if column == "INFLUENZA PEDIATRICA":
        if age_days < M6:
            return [_na]
        elif age_days < M12:      # 6–11 meses: 2 dosis pediátricas (pág. 27 NTS)
            results = []
            for seq, lbl, min_d in [(1, "1ra", M6), (2, "2da", M7)]:
                sched = _sched(min_d)
                if len(parsed_doses) >= seq:
                    al, ad = parsed_doses[seq - 1]
                    dl = (ad - sched).days if sched else None
                    results.append({
                        "seq": seq, "label": lbl, "status": APLICADA,
                        "applied_date": ad, "applied_label": al,
                        "scheduled_date": sched, "days_late": dl,
                    })
                else:
                    results.append({
                        "seq": seq, "label": lbl, "status": PENDIENTE,
                        "applied_date": None, "applied_label": None,
                        "scheduled_date": sched, "days_late": None,
                    })
            return results
        elif age_days < Y3:       # 1 año – 2 años 11m: dosis anual pediátrica
            return [_annual_entry()]
        else:                     # ≥ 3 años → corresponde Influenza Adulto
            return [_nc]

    elif column == "INFLUENZA ADULTO":
        if age_days < Y3:         # < 3 años → corresponde Influenza Pediátrica
            return [_nc]
        else:                     # ≥ 3 años: dosis anual adulto
            return [_annual_entry()]

    return []


def get_vaccine_status(column: str, parsed_doses: list, age_days: int,
                       birth_date: Optional[date] = None) -> list:
    """
    Retorna lista de dicts con el estado de cada dosis esperada.

    Cada dict: {seq, label, status, applied_date, applied_label,
                scheduled_date, days_late}

    scheduled_date: fecha en que debería aplicarse según NTS (birth_date + min_days).
    days_late:      días de retraso al aplicar (negativo = anticipada).
    """
    if column in ("INFLUENZA PEDIATRICA", "INFLUENZA ADULTO"):
        return _influenza_status(column, parsed_doses, age_days, birth_date)

    scheme = SCHEME.get(column, [])
    return [_dose_status(d, parsed_doses, age_days, birth_date) for d in scheme]


def _days_to_age_str(days: int) -> str:
    """Convierte días a texto legible: '7 días', '8 meses', '5 años'."""
    if days < 30:
        return f"{days} días"
    elif days < 365:
        return f"{round(days / 30.4)} meses"
    else:
        return f"{round(days / 365)} años"


def format_dose_cell(dose_results: list) -> str:
    """
    Texto corto por dosis para la celda de la tabla.
    Cada dosis ocupa una línea: etiqueta + fecha o estado breve.

    Ejemplos:
      1ra: 28/02/2024          ← aplicada
      2da: 28/04/2024 (tardía) ← aplicada fuera de ventana ideal
      3ra: Pendiente           ← falta aplicar
      DU:  Incumplió           ← pasó la ventana ideal, puede recuperarse
      DU:  Vencida             ← ya no puede aplicarse
      DA:  15/06/2025          ← fecha programada (aún no corresponde)
      DU:  Error de registro   ← etiqueta incorrecta en el padrón
    """
    if not dose_results:
        return "—"
    lines = []
    for r in dose_results:
        lbl    = r["label"]
        status = r["status"]
        sched  = r.get("scheduled_date")
        adate  = r.get("applied_date")

        if status == APLICADA:
            lines.append(f"{lbl}: {adate.strftime('%d/%m/%Y')}")

        elif status == APLICADA_TARDIA:
            lines.append(f"{lbl}: {adate.strftime('%d/%m/%Y')} (tardía)")

        elif status == PENDIENTE:
            lines.append(f"{lbl}: Pendiente")

        elif status == INCUMPLIO:
            lines.append(f"{lbl}: Incumplió")

        elif status == FUERA_EDAD:
            lines.append(f"{lbl}: Vencida")

        elif status == NO_APLICA_AUN:
            if sched:
                lines.append(f"{lbl}: {sched.strftime('%d/%m/%Y')}")
            else:
                lines.append(f"{lbl}: —")

        elif status == ERROR_DU:
            lines.append(f"{lbl}: Error de registro")

        else:
            lines.append("—")

    return "\n".join(lines)


def format_single_dose(dose_result: dict) -> str:
    """Texto con ícono para una sola dosis en columna individual de la tabla."""
    status = dose_result["status"]
    icon   = STATUS_ICONS.get(status, "")
    adate  = dose_result.get("applied_date")
    sched  = dose_result.get("scheduled_date")
    if status == APLICADA:
        return f"{icon} {adate.strftime('%d/%m/%Y')}" if adate else f"{icon} Aplicada"
    elif status == APLICADA_TARDIA:
        return f"{icon} {adate.strftime('%d/%m/%Y')} (tardía)" if adate else f"{icon} Tardía"
    elif status == PENDIENTE:
        fecha = sched.strftime("%d/%m/%Y") if sched else ""
        return f"{icon} Pendiente · {fecha}" if fecha else f"{icon} Pendiente"
    elif status == INCUMPLIO:
        fecha = sched.strftime("%d/%m/%Y") if sched else ""
        return f"{icon} Incumplió · {fecha}" if fecha else f"{icon} Incumplió"
    elif status == FUERA_EDAD:
        return f"{icon} Vencida"
    elif status == NO_APLICA_AUN:
        return sched.strftime("%d/%m/%Y") if sched else "N/C"
    elif status == ERROR_DU:
        lbl = dose_result.get("applied_label", "?")
        return f'{icon} Error reg. · "{lbl}"≠"DU"'
    elif status == NO_CORRESPONDE:
        return "N/C"
    return "N/C"


def format_dose_detail(dose_results: list) -> str:
    """
    Texto explicativo completo por dosis — usado en el panel de detalle y en Excel.

    Cada línea incluye la razón del estado según NTS:
      ✅  aplicada — fecha y puntualidad
      🕐  aplicada tardía — fuera de la ventana ideal
      ⚠️  pendiente — cuándo debió/debe vacunarse
      ❌  incumplió — ventana ideal superada, recuperación posible
      🚫  fuera de edad — ya no puede recuperarse
      🔴  error DU — etiqueta incorrecta en el padrón
      —   aún no corresponde — fecha programada próxima
    """
    if not dose_results:
        return "—"
    today = date.today()
    lines = []
    for r in dose_results:
        icon      = STATUS_ICONS.get(r["status"], "?")
        sched     = r.get("scheduled_date")
        sched_str = sched.strftime("%d/%m/%Y") if sched else None

        if r["status"] == APLICADA:
            days_late = r.get("days_late")
            if days_late is None or sched is None:
                timeliness = ""
            elif days_late < 0:
                timeliness = f" ({abs(days_late)}d antes de lo programado)"
            elif days_late == 0:
                timeliness = ""
            elif days_late <= 30:
                timeliness = f" ({days_late}d después de lo programado)"
            else:
                timeliness = f" (⚠ {days_late}d tarde — revisar registro)"
            lines.append(
                f"{icon} {r['applied_label']}: "
                f"{r['applied_date'].strftime('%d/%m/%Y')}{timeliness}"
            )

        elif r["status"] == APLICADA_TARDIA:
            ideal_max = r.get("ideal_max_days")
            ideal_str = "las primeras 24 horas de vida" if ideal_max == 1 else _days_to_age_str(ideal_max)
            lines.append(
                f"{icon} {r['applied_label']}: {r['applied_date'].strftime('%d/%m/%Y')} "
                f"— Aplicada tardíamente (a los {r['days_late']} días de vida). "
                f"La NTS indica vacunar dentro de {ideal_str}."
            )

        elif r["status"] == INCUMPLIO:
            ideal_max = r.get("ideal_max_days")
            ideal_str = "las primeras 24 horas de vida" if ideal_max == 1 else _days_to_age_str(ideal_max)
            max_d = r.get("max_days")
            recovery_str = ""
            if sched is not None and max_d is not None:
                recovery_deadline = sched + timedelta(days=max_d)
                recovery_str = f" Recuperación posible hasta el {recovery_deadline.strftime('%d/%m/%Y')}."
            lines.append(
                f"{icon} {r['label']} — Incumplió. "
                f"Debió vacunarse dentro de {ideal_str}.{recovery_str}"
            )

        elif r["status"] == ERROR_DU:
            lines.append(
                f"{icon} Se registró '{r['applied_label']}' el "
                f"{r['applied_date'].strftime('%d/%m/%Y')}, "
                f"pero esta vacuna es de Dosis Única (DU) según NTS. "
                f"Corregir etiqueta en el padrón."
            )

        elif r["status"] == PENDIENTE:
            if sched:
                if sched < today:
                    diff = (today - sched).days
                    lines.append(
                        f"{icon} {r['label']} NO aplicada. "
                        f"Debió vacunarse el {sched_str} "
                        f"(hace {diff} días — atrasada)."
                    )
                else:
                    diff = (sched - today).days
                    lines.append(
                        f"{icon} {r['label']} pendiente. "
                        f"Fecha programada: {sched_str} "
                        f"(en {diff} días)."
                    )
            else:
                lines.append(
                    f"{icon} {r['label']} pendiente — "
                    f"ya corresponde vacunarse según la NTS."
                )

        elif r["status"] == NO_APLICA_AUN:
            if sched_str:
                lines.append(f"— {r['label']}: aún no corresponde. Programada: {sched_str}.")
            else:
                lines.append(f"— {r['label']}: aún no corresponde por edad.")

        elif r["status"] == FUERA_EDAD:
            max_d = r.get("max_days")
            if max_d is not None:
                limite = _days_to_age_str(max_d)
                lines.append(
                    f"{icon} {r['label']} — No se vacunó dentro del plazo. "
                    f"La NTS establece un máximo de {limite} para esta dosis."
                )
            else:
                lines.append(f"{icon} {r['label']} — Superó el límite de edad según NTS.")

        else:
            lines.append(f"{icon} {r['status']}")

    return "\n".join(lines)


_NEEDS_ATTENTION = {PENDIENTE, ERROR_DU, INCUMPLIO}

# Etiquetas de acción para el dashboard
ACTION_LABELS = {
    ERROR_DU:  "🔴 Corregir registro",
    INCUMPLIO: "❌ Recuperar",
    PENDIENTE: "⚠️ Vacunar",
    "OK":      "✅ Completo",
}


def patient_action_priority(vaccine_results: dict) -> str:
    """
    Retorna la acción más urgente del paciente:
    ERROR_DU > INCUMPLIÓ > PENDIENTE > OK
    """
    statuses = {r["status"] for results in vaccine_results.values() for r in results}
    for s in (ERROR_DU, INCUMPLIO, PENDIENTE):
        if s in statuses:
            return ACTION_LABELS[s]
    return ACTION_LABELS["OK"]


def patient_has_pending(vaccine_results: dict) -> bool:
    """True si el paciente tiene al menos una dosis PENDIENTE o ERROR_DU."""
    return any(
        r["status"] in _NEEDS_ATTENTION
        for results in vaccine_results.values()
        for r in results
    )


def patient_has_overdue(vaccine_results: dict) -> bool:
    """True si el paciente tiene al menos una dosis PENDIENTE con fecha ya vencida."""
    today = date.today()
    return any(
        r["status"] == PENDIENTE
        and r.get("scheduled_date") is not None
        and r["scheduled_date"] < today
        for results in vaccine_results.values()
        for r in results
    )


def patient_pending_list(vaccine_results: dict) -> str:
    """Retorna nombres de vacunas con dosis PENDIENTE o ERROR_DU separados por coma."""
    pending = [
        col for col, results in vaccine_results.items()
        if any(r["status"] in _NEEDS_ATTENTION for r in results)
    ]
    return ", ".join(pending) if pending else ""


def patient_next_appointment(vaccine_results: dict) -> Optional[date]:
    """
    Retorna la fecha más relevante para la próxima atención:
    - Si hay dosis PENDIENTE atrasada: la más antigua (más urgente).
    - Si no: la próxima dosis NO_APLICA_AUN aún no llegada.
    """
    today   = date.today()
    overdue = []
    upcoming = []
    for results in vaccine_results.values():
        for r in results:
            sched = r.get("scheduled_date")
            if not sched:
                continue
            if r["status"] == PENDIENTE:
                (overdue if sched < today else upcoming).append(sched)
            elif r["status"] == NO_APLICA_AUN and sched >= today:
                upcoming.append(sched)
    if overdue:
        return min(overdue)
    return min(upcoming) if upcoming else None


def worst_status_color(dose_results: list) -> str:
    """
    Retorna el color hex para la celda según el peor estado de las dosis.
    Orden de prioridad: ERROR_DU > FUERA_EDAD > PENDIENTE > APLICADA > NO_CORRESPONDE > NO_APLICA_AUN
    """
    if not dose_results:
        return STATUS_COLORS[NO_APLICA_AUN]
    statuses = [r["status"] for r in dose_results]
    for priority_status in (ERROR_DU, INCUMPLIO, FUERA_EDAD, PENDIENTE, APLICADA_TARDIA):
        if priority_status in statuses:
            return STATUS_COLORS[priority_status]
    if all(s == APLICADA for s in statuses):
        return STATUS_COLORS[APLICADA]
    if all(s == NO_CORRESPONDE for s in statuses):
        return STATUS_COLORS[NO_CORRESPONDE]
    return STATUS_COLORS[NO_APLICA_AUN]

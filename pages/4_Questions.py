# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login, sidebar_logout_bottom

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

import os, re, json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# =========================
# PAGE
# =========================
st.title("🤖 Questions (réponse en phrases) — strava_import")
sidebar_logout_bottom(sb)

user = st.session_state.get("user")
if not user:
    st.stop()

# =========================
# Chargement: toute la table (toutes colonnes)
# =========================
TABLE = "strava_import"

def snake(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(s).strip().lower())

def dtype_str(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series): return "integer"
    if pd.api.types.is_float_dtype(series):   return "float"
    if pd.api.types.is_bool_dtype(series):    return "boolean"
    if pd.api.types.is_datetime64_any_dtype(series): return "timestamp"
    return "text"

def load_table_df() -> pd.DataFrame:
    q = sb.table(TABLE).select("*").eq("user_id", user["id"])
    res = q.execute()
    df = pd.DataFrame(res.data or [])
    if df.empty: return df
    rename = {c: snake(c) for c in df.columns}
    df = df.rename(columns=rename)
    # cast datetime
    for c in df.columns:
        if any(k in c for k in ["date","time","start","end","_at","_ts"]):
            try: df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
            except Exception: pass
    # enrichir iso/week/mois/jour
    time_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if time_cols:
        t = time_cols[0]
        iso = df[t].dt.isocalendar()
        if "iso_year" not in df.columns: df["iso_year"] = iso.year
        if "iso_week" not in df.columns: df["iso_week"] = iso.week.astype("Int64")
        if "month" not in df.columns:    df["month"] = df[t].dt.month
        if "date_only" not in df.columns: df["date_only"] = df[t].dt.date.astype("string")
    return df

df = load_table_df()
if df.empty:
    st.write("Je n’ai trouvé aucune activité dans ta table pour cet utilisateur.")
    st.stop()

schema_detected = [{"name": c, "type": dtype_str(df[c])} for c in df.columns]
NUMERIC_COLS = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

# =========================
# Synonymes FR massifs -> colonnes existantes
# =========================
RAW_ALIASES: Dict[str, List[str]] = {
    "distance": ["distance", "km", "kilometres", "kilomètres", "kilométrage", "kms", "total km", "distance totale"],
    "moving_time": ["moving_time", "temps en mouvement", "temps actif", "temps roulant"],
    "elapsed_time": ["elapsed_time", "temps total", "durée totale", "durée", "temps écoulé"],
    "average_speed": ["average_speed", "vitesse moyenne", "vitesse", "kmh", "km/h", "moyenne kmh"],
    "max_speed": ["max_speed", "vitesse maximale", "vitesse max", "pointe de vitesse"],
    "average_heart_rate": ["average_heart_rate", "fc moyenne", "fréquence cardiaque moyenne", "bpm moyen", "pouls moyen"],
    "max_heart_rate": ["max_heart_rate", "fc max", "fréquence cardiaque max", "bpm max", "pouls max"],
    "elevation_gain": ["elevation_gain", "d+", "denivele positif", "dénivelé positif", "gain altitude", "montée", "dplus"],
    "elevation_loss": ["elevation_loss", "d-", "denivele negatif", "dénivelé négatif", "perte altitude", "descente", "dmoins"],
    "elevation_low": ["elevation_low", "altitude min", "alt min", "altitude minimale"],
    "elevation_high": ["elevation_high", "altitude max", "alt max", "altitude maximale"],
    "max_grade": ["max_grade", "pente max", "pente maximale", "pourcentage max"],
    "average_grade": ["average_grade", "pente moyenne", "pourcentage moyen"],
    "relative_effort": ["relative_effort", "effort relatif", "effort", "rpe"],
    "calories": ["calories", "kcal", "cal", "dépense calorique"],
    "athlete_weight": ["athlete_weight", "poids athlète", "poids corps", "poids"],
    "bike_weight": ["bike_weight", "poids vélo"],
    "activity_type": ["activity_type", "type", "sport", "discipline", "activité"],
    "activity_name": ["activity_name", "nom activité", "titre activité", "nom"],
    "activity_description": ["activity_description", "description", "note", "commentaire"],
    "activity_date": ["activity_date", "date", "jour", "date activité"],
    "filename": ["filename", "fichier", "nom de fichier"],
    # rythme si dispo
    "avg_pace_min_per_km": ["avg_pace_min_per_km", "allure moyenne", "allure", "min/km", "min par km"],
    # clés de regroupement temporel
    "iso_week": ["iso_week", "semaine", "num semaine", "sem"],
    "iso_year": ["iso_year", "année", "an", "year"],
    "month": ["month", "mois"],
    "date_only": ["date_only", "jour (date)", "date simple"]
}
ALIASES: Dict[str, List[str]] = {col: [s for s in syns if col in df.columns]
                                 for col, syns in RAW_ALIASES.items() if col in df.columns}
SYN_TO_COL: Dict[str, str] = {}
for col, syns in ALIASES.items():
    for s in syns:
        SYN_TO_COL[s.lower()] = col

def normalize_question_with_aliases(q: str) -> str:
    qn = " " + q.lower() + " "
    syns_sorted = sorted(SYN_TO_COL.keys(), key=len, reverse=True)
    for syn in syns_sorted:
        pattern = r"(?<![a-z0-9_])" + re.escape(syn) + r"(?![a-z0-9_])"
        qn = re.sub(pattern, SYN_TO_COL[syn], qn, flags=re.IGNORECASE)
    return qn.strip()

# =========================
# UI minimale: juste la question + une réponse texte
# =========================
txt_raw = st.text_input("Pose ta question (FR) :", placeholder="Ex: d+ moyen par semaine cette année")
go = st.button("Envoyer")
if not (txt_raw and go):
    st.stop()

txt = normalize_question_with_aliases(txt_raw)

# =========================
# LLM planificateur (JSON) — puis réponse en PHRASES
# =========================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = """Tu es un planificateur analytique pour des données d'entraînement.
Tu renvoies UNIQUEMENT un JSON valide (aucun texte autour).

Format strict:
{
  "metric": { "op": "<sum|avg|max|min|count>", "column": "<colonne ou 'count'>" },
  "filters": {
    "year": 2025 | 2024 | null,
    "weeks": { "from": 10, "to": 20 } | null,
    "month": 1..12 | null,
    "where": [
      { "column": "<col>", "op": "<=|>=|=|!=|contains>", "value": "<valeur>" }
    ] | []
  },
  "group_by": "week" | "month" | "day" | "none",
  "natural_language_goal": "<paraphrase courte>"
}

Règles:
- Utilise les colonnes disponibles. sum/avg/max/min sur numériques, sinon count.
- “semaines X à Y” -> weeks={from:X,to:Y} et group_by="week".
- “cette année” -> year = année courante.
- “par mois” -> group_by="month" ; “par jour” -> group_by="day".
- where[] pour activity_type = run, etc.
"""

def call_llm_plan(question: str) -> Optional[Dict[str, Any]]:
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=[
                {"role":"system","content":SYSTEM_PROMPT},
                {"role":"user","content":json.dumps({"table":"strava_import","columns":schema_detected}, ensure_ascii=False)},
                {"role":"user","content":question}
            ],
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception:
        return None

MONTHS = {
    "janvier":1,"février":2,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,
    "août":8,"aout":8,"septembre":9,"octobre":10,"novembre":11,"décembre":12,"decembre":12
}

def regex_fallback(q: str) -> Dict[str, Any]:
    ql = q.lower()
    op = "avg" if re.search(r"\bmoyenn?e?\b", ql) else ("max" if "max" in ql else ("min" if "min" in ql else ("count" if "nombre" in ql or "compte" in ql else "sum")))
    col = None
    for c in df.columns:
        if re.search(rf"(?<![a-z0-9_]){re.escape(c)}(?![a-z0-9_])", ql):
            col = c; break
    if col is None:
        for pref in ["distance","elevation_gain","average_speed","average_heart_rate","moving_time","elapsed_time","calories","avg_pace_min_per_km"]:
            if pref in df.columns: col = pref; break
        if col is None:
            col = NUMERIC_COLS[0] if NUMERIC_COLS else df.columns[0]
    weeks = None
    m = re.search(r"semaines?\s+(\d+)\s*[à\-]\s*(\d+)", ql)
    if m: weeks = {"from": int(m.group(1)), "to": int(m.group(2))}
    year = date.today().year if "cette année" in ql else (int(m2.group(1)) if (m2 := re.search(r"(20\d{2})", ql)) else None)
    month = None
    if (m3 := re.search(r"(janvier|février|fevrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|décembre|decembre)", ql)):
        month = MONTHS[m3.group(1).replace("û","u")]
    where = []
    if "activity_type" in df.columns:
        if " type = run" in f" {ql} " or " activity_type = run" in ql:
            where.append({"column":"activity_type","op":"=","value":"run"})
    group_by = "week" if weeks else ("month" if "par mois" in ql else ("day" if "par jour" in ql else "none"))
    return {
        "metric": {"op": op, "column": col},
        "filters": {"year": year, "weeks": weeks, "month": month, "where": where},
        "group_by": group_by,
        "natural_language_goal": q
    }

plan = call_llm_plan(txt) or regex_fallback(txt)

# Sécuriser/normaliser la colonne choisie
def resolve_column(col: Optional[str]) -> Optional[str]:
    if not col: return None
    if col in df.columns: return col
    col_lc = col.lower()
    if col_lc in SYN_TO_COL and SYN_TO_COL[col_lc] in df.columns:
        return SYN_TO_COL[col_lc]
    col_sn = snake(col_lc)
    if col_sn in df.columns: return col_sn
    return NUMERIC_COLS[0] if NUMERIC_COLS else (df.columns[0] if len(df.columns) else None)

if "metric" in plan:
    plan["metric"]["column"] = resolve_column(plan.get("metric", {}).get("column"))

# =========================
# Exécution calculs (aucun affichage brut)
# =========================
def apply_filters(dd: pd.DataFrame, plan: Dict[str, Any]) -> Tuple[pd.DataFrame, Optional[str]]:
    out = dd.copy()
    F = plan.get("filters") or {}

    if F.get("year") is not None and "iso_year" in out.columns:
        out = out[out["iso_year"] == int(F["year"])]

    if F.get("month") is not None:
        if "month" in out.columns:
            out = out[out["month"] == int(F["month"])]
        else:
            tcol = next((c for c in out.columns if pd.api.types.is_datetime64_any_dtype(out[c])), None)
            if tcol: out = out[out[tcol].dt.month == int(F["month"])]

    if (w := F.get("weeks")) and "iso_week" in out.columns:
        out = out[(out["iso_week"] >= int(w["from"])) & (out["iso_week"] <= int(w["to"]))]

    for cond in F.get("where", []) or []:
        col, op, val = cond.get("column"), cond.get("op"), cond.get("value")
        if not col or col not in out.columns: continue
        s = out[col]
        if pd.api.types.is_numeric_dtype(s):
            try: val_cast = float(val)
            except: continue
        elif pd.api.types.is_bool_dtype(s):
            val_cast = str(val).lower() in ("true","1","yes","oui")
        elif pd.api.types.is_datetime64_any_dtype(s):
            try: val_cast = pd.to_datetime(val, utc=True)
            except: continue
        else:
            val_cast = str(val)
        if op == "=": out = out[s == val_cast]
        elif op == "!=": out = out[s != val_cast]
        elif op == ">=" and pd.api.types.is_numeric_dtype(s): out = out[s >= val_cast]
        elif op == "<=" and pd.api.types.is_numeric_dtype(s): out = out[s <= val_cast]
        elif op == "contains": out = out[s.astype(str).str.contains(str(val), case=False, na=False)]

    gby = plan.get("group_by","none")
    if gby == "week" and "iso_week" in out.columns: key = "iso_week"
    elif gby == "month" and "month" in out.columns: key = "month"
    elif gby == "day" and "date_only" in out.columns: key = "date_only"
    else: key = None
    return out, key

def aggregate(dd: pd.DataFrame, plan: Dict[str, Any], key: Optional[str]) -> Tuple[pd.DataFrame, str, str]:
    metric = (plan.get("metric") or {})
    op = (metric.get("op") or "sum").lower()
    col = metric.get("column") or (NUMERIC_COLS[0] if NUMERIC_COLS else dd.columns[0])

    needs_num = op in ("sum","avg","max","min")
    if needs_num and (col not in dd.columns or not pd.api.types.is_numeric_dtype(dd[col])):
        op = "count"

    if key is not None:
        g = dd.groupby(key)
        if op == "sum": out = g[col].sum(numeric_only=True)
        elif op == "avg": out = g[col].mean(numeric_only=True)
        elif op == "max": out = g[col].max(numeric_only=True)
        elif op == "min": out = g[col].min(numeric_only=True)
        elif op == "count": out = g[col].count()
        else: out = g[col].sum(numeric_only=True)
        result = out.reset_index().rename(columns={col: f"{op}_{col}", key: "group"})
        return result, "group", f"{op}_{col}"
    else:
        if op == "sum": val = dd[col].sum(numeric_only=True)
        elif op == "avg": val = dd[col].mean(numeric_only=True)
        elif op == "max": val = dd[col].max(numeric_only=True)
        elif op == "min": val = dd[col].min(numeric_only=True)
        elif op == "count": val = dd[col].count()
        else: val = dd[col].sum(numeric_only=True)
        return pd.DataFrame({"metric":[f"{op}_{col}"], "value":[val]}), "metric", "value"

df_filt, group_key = apply_filters(df, plan)
if df_filt.empty:
    st.write("Aucun enregistrement ne correspond à ta demande après application des filtres.")
    st.stop()

result, x, y = aggregate(df_filt, plan, group_key)

# =========================
# Rédaction de la réponse (phrases seulement)
# =========================
def fmt_num(v: Any) -> str:
    try:
        if pd.isna(v): return "—"
        if isinstance(v, (int,)) or float(v).is_integer():
            return f"{float(v):,.0f}".replace(",", " ").replace("\xa0"," ")
        return f"{float(v):,.2f}".replace(",", " ").replace("\xa0"," ")
    except Exception:
        return str(v)

def describe_filters(F: Dict[str, Any]) -> str:
    parts = []
    if F.get("year") is not None: parts.append(f"année {F['year']}")
    if F.get("month") is not None: parts.append(f"mois {int(F['month'])}")
    if F.get("weeks"): parts.append(f"semaines {F['weeks']['from']} à {F['weeks']['to']}")
    if F.get("where"):
        wh = []
        for c in F["where"]:
            if c.get("column") and c.get("op") and c.get("value") is not None:
                wh.append(f"{c['column']} {c['op']} {c['value']}")
        if wh: parts.append("filtre: " + ", ".join(wh))
    return (" (" + "; ".join(parts) + ")") if parts else ""

def verbalize(plan: Dict[str, Any], result: pd.DataFrame, x: str, y: str) -> str:
    metric = plan.get("metric", {})
    op = (metric.get("op") or "sum").lower()
    col = metric.get("column") or "valeur"
    F = plan.get("filters") or {}
    gby = plan.get("group_by","none")

    if x in ("metric","value"):  # agrégat unique
        val = result.iloc[0][y]
        return f"{op} de **{col}**{describe_filters(F)} : {fmt_num(val)}."
    else:
        # groupé: on donne un résumé concis + quelques points
        n = len(result)
        # ordonner par groupe si possible
        try:
            res_sorted = result.sort_values(by=x)
        except Exception:
            res_sorted = result
        head = res_sorted.head(8)
        pairs = ", ".join([f"{str(row[x])}: {fmt_num(row[y])}" for _, row in head.iterrows()])
        more = "" if n <= len(head) else f" … et {n - len(head)} autres."
        label = "par semaine" if gby=="week" else ("par mois" if gby=="month" else "par jour")
        return f"{op} de **{col}** {label}{describe_filters(F)} — {pairs}{more}"

# Affichage final: PHRASES UNIQUEMENT
response_text = verbalize(plan, result, x, y)
st.markdown(response_text)

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
import plotly.express as px

st.title("🤖 Questions (langage courant) — `strava_import`")

sidebar_logout_bottom(sb)

user = st.session_state.get("user")
if not user:
    st.stop()

# =========================================
# 1) Charger 100% des colonnes de la table
# =========================================
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
    # snake_case gentil
    rename = {c: snake(c) for c in df.columns}
    df = df.rename(columns=rename)
    # cast datetime où pertinent
    for c in df.columns:
        if any(k in c for k in ["date","time","start","end","_at","_ts"]):
            try:
                df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
            except Exception:
                pass
    # enrichir iso_week / iso_year / month / date_only si on a une datetime
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
    st.info("Pas de données visibles dans `strava_import` pour cet utilisateur.")
    st.stop()

schema_detected = [{"name": c, "type": dtype_str(df[c])} for c in df.columns]
NUMERIC_COLS = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

# =========================================
# 2) Dictionnaire d'ALIAS (énormément de synonymes FR)
#    -> on filtre pour ne garder que les colonnes qui existent VRAIMENT
# =========================================
RAW_ALIASES: Dict[str, List[str]] = {
    # Distance
    "distance": [
        "distance", "km", "kilometres", "kilomètres", "kilométrage", "kilo", "kms", "km total",
        "distance totale", "tot km", "total km", "metrage", "parcours total"
    ],
    # Temps
    "moving_time": [
        "moving_time", "temps en mouvement", "temps de déplacement", "temps actif",
        "temps couru", "temps roulant", "temps bougé"
    ],
    "elapsed_time": [
        "elapsed_time", "temps total", "durée totale", "durée", "temps écoulé", "temps complet"
    ],
    # Vitesse/Allure
    "average_speed": [
        "average_speed", "vitesse moyenne", "vitesse", "kmh", "km/h", "moyenne kmh", "vitesse en kmh",
        "allure moyenne (vitesse)", "allure (vitesse)"
    ],
    "max_speed": ["max_speed", "vitesse maximale", "vitesse max", "pointe de vitesse"],
    # Fréquence cardiaque
    "average_heart_rate": [
        "average_heart_rate", "fc moyenne", "fréquence cardiaque moyenne", "bpm moyen",
        "pouls moyen", "fcmoy", "heart rate avg"
    ],
    "max_heart_rate": [
        "max_heart_rate", "fc max", "fréquence cardiaque max", "bpm max", "pouls max", "hr max"
    ],
    # Dénivelé
    "elevation_gain": [
        "elevation_gain", "d+", "denivele positif", "dénivelé positif", "gain altitude",
        "montée", "cumule d+", "elev gain", "dplus"
    ],
    "elevation_loss": [
        "elevation_loss", "d-", "denivele negatif", "dénivelé négatif", "perte altitude",
        "descente", "cumule d-", "elev loss", "dmoins"
    ],
    "elevation_low": ["elevation_low", "altitude min", "altitude minimale", "alt min", "alt basse"],
    "elevation_high": ["elevation_high", "altitude max", "altitude maximale", "alt max", "alt haute"],
    # Pente
    "max_grade": ["max_grade", "pente max", "pente maximale", "pourcentage max"],
    "average_grade": ["average_grade", "pente moyenne", "pourcentage moyen"],
    # Effort / calories
    "relative_effort": ["relative_effort", "effort relatif", "effort", "ressenti effort", "rpe"],
    "calories": ["calories", "kcal", "cal", "dépense calorique", "calorie"],
    # Poids / matos
    "athlete_weight": ["athlete_weight", "poids athlète", "poids corps", "poids"],
    "bike_weight": ["bike_weight", "poids vélo", "poids du vélo"],
    # Type / méta
    "activity_type": ["activity_type", "type", "sport", "discipline", "activité", "mode"],
    "activity_name": ["activity_name", "nom activité", "titre activité", "nom"],
    "activity_description": ["activity_description", "description", "note", "commentaire"],
    "activity_date": ["activity_date", "date", "jour", "date activité"],
    "filename": ["filename", "fichier", "nom de fichier"],
    "commute": ["commute", "trajet domicile travail", "vélotaf", "déplacement utilitaire"],
    # Vitesses/rythmes alternatifs (si présents)
    "average_speed_kmh": ["average_speed_kmh", "vitesse moyenne kmh", "kmh moyen"],
    "avg_pace_min_per_km": [
        "avg_pace_min_per_km", "allure moyenne", "allure", "min par km", "min/km", "pace"
    ],
    # ISO / date dérivées
    "iso_week": ["iso_week", "semaine", "num semaine", "sem"],
    "iso_year": ["iso_year", "année", "an", "year"],
    "month": ["month", "mois"],
    "date_only": ["date_only", "jour (date)", "jour calendrier", "date simple"]
}

# Filtrer les alias pour ne conserver que les colonnes existantes
ALIASES: Dict[str, List[str]] = {
    col: [syn for syn in syns if (col in df.columns)]
    for col, syns in RAW_ALIASES.items() if col in df.columns
}

# Construire un index synonyme -> colonne (regex safe)
SYN_TO_COL: Dict[str, str] = {}
for col, syns in ALIASES.items():
    for s in syns:
        # normalise clé synonyme pour matcher plus tard
        SYN_TO_COL[s.lower()] = col

# =========================================
# 3) Pré-traitement de la question avec alias
#    - remplace les synonymes par les noms de colonnes existants
# =========================================
def normalize_question_with_aliases(q: str) -> str:
    qn = " " + q.lower() + " "
    # remplacements prudents par limites de mots
    # on trie les synonymes par longueur décroissante pour éviter "km" avant "km/h"
    syns_sorted = sorted(SYN_TO_COL.keys(), key=len, reverse=True)
    for syn in syns_sorted:
        pattern = r"(?<![a-z0-9_])" + re.escape(syn) + r"(?![a-z0-9_])"
        col = SYN_TO_COL[syn]
        qn = re.sub(pattern, col, qn, flags=re.IGNORECASE)
    return qn.strip()

# =========================================
# 4) UI
# =========================================
examples = [
    "distance totale en 2024",
    "fc moyenne semaines 10 à 20 en 2025",
    "d+ moyen par semaine cette année",
    "vitesse max en août 2025",
    "nombre d'activités par mois en 2024",
    "allure moyenne par semaine où type = run en 2025",  # sera mappé vers avg_pace_min_per_km si présent, sinon average_speed
]
with st.expander("💡 Exemples (clique pour remplir)"):
    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}"):
            st.session_state["question_txt"] = ex

txt_raw = st.text_input("Pose ta question en FR :", key="question_txt", placeholder="Ex: d+ moyen par semaine cette année")
run = st.button("Analyser")
if not (txt_raw and run):
    st.stop()

txt = normalize_question_with_aliases(txt_raw)

# =========================================
# 5) LLM planificateur (JSON strict) + alias exposés
# =========================================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

SCHEMA_DOC = {
    "table": TABLE,
    "columns": schema_detected,
    "aliases": [
        {"column": col, "synonyms": syns} for col, syns in ALIASES.items()
    ],
    "notes": [
        "Les synonymes ci-dessus sont déjà remplacés dans la question avant appel.",
        "Groupements possibles: week (iso_week), month (month), day (date_only).",
        "Filtres: year (iso_year), weeks {from,to}, month (1-12), where[] pour conditions libres.",
        "Si une colonne demandée n’existe pas, privilégie les colonnes les plus proches présentes dans le schéma."
    ]
}

SYSTEM_PROMPT = """Tu es un planificateur analytique. 
Langue: Français. Tu NE renvoies que du JSON VALIDE (sans texte autour).

Format strict:
{
  "metric": { "op": "<sum|avg|max|min|count>", "column": "<nom_colonne_exact_ou_count>" },
  "filters": {
    "year": 2025 | 2024 | null,
    "weeks": { "from": 10, "to": 20 } | null,
    "month": 1..12 | null,
    "where": [
      { "column": "<col>", "op": "<=|>=|=|contains|=|!=>", "value": "<valeur>" }
    ] | []
  },
  "group_by": "week" | "month" | "day" | "none",
  "chart": "line" | "bar" | "none",
  "natural_language_goal": "<paraphrase courte>"
}

Règles:
- Utilise les colonnes du schéma fourni. Si la question contient déjà un nom de colonne (remplacé via alias), respecte-le.
- sum/avg/max/min exigent une colonne numérique; sinon bascule sur count.
- “semaines X à Y” -> weeks={from:X,to:Y} et group_by="week".
- “cette année” -> year = année courante.
- “par mois” -> group_by="month" ; “par jour” -> group_by="day".
- where[] permet des filtres libres (ex: activity_type = run).
- chart: "line" si group_by != "none", sinon "bar".
"""

def call_llm_plan(question: str, schema_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
                {"role":"user","content":json.dumps(schema_doc, ensure_ascii=False)},
                {"role":"user","content":question}
            ],
        )
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        st.warning(f"LLM indisponible ou JSON invalide ({e}). On tente un fallback.")
        return None

# =========================================
# 6) Fallback regex simple (après alias)
# =========================================
MONTHS = {
    "janvier":1,"février":2,"fevrier":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,
    "août":8,"aout":8,"septembre":9,"octobre":10,"novembre":11,"décembre":12,"decembre":12
}

def regex_fallback(q: str) -> Dict[str, Any]:
    ql = q.lower()
    op = "avg" if re.search(r"\bmoyenn?e?\b", ql) else ("max" if "max" in ql else ("min" if "min" in ql else ("count" if "nombre" in ql or "compte" in ql else "sum")))
    # colonne: chercher d'abord match exact sur df après alias
    col = None
    for c in df.columns:
        if re.search(rf"(?<![a-z0-9_]){re.escape(c)}(?![a-z0-9_])", ql):
            col = c; break
    if col is None:
        # defaults pertinents
        for pref in ["distance","elevation_gain","average_speed","average_heart_rate","calories","moving_time","elapsed_time","avg_pace_min_per_km"]:
            if pref in df.columns:
                col = pref; break
        if col is None:
            col = NUMERIC_COLS[0] if NUMERIC_COLS else df.columns[0]

    weeks = None
    m = re.search(r"semaines?\s+(\d+)\s*[à\-]\s*(\d+)", ql)
    if m: weeks = {"from": int(m.group(1)), "to": int(m.group(2))}
    year = date.today().year if "cette année" in ql else (int(m2.group(1)) if (m2 := re.search(r"(20\d{2})", ql)) else None)
    month = None
    if (m3 := re.search(r"(janvier|février|fevrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|décembre|decembre)", ql)):
        month = MONTHS[m3.group(1).replace("û","u")]

    # where: type = run / activity_type = run / etc.
    where = []
    for c in ["activity_type","activity_name","activity_description","filename","commute"]:
        if c in df.columns:
            m4 = re.search(rf"{c}\s*=\s*([a-z0-9_\-]+)", ql)
            if m4:
                where.append({"column": c, "op": "=", "value": m4.group(1)})

    group_by = "week" if weeks else ("month" if "par mois" in ql else ("day" if "par jour" in ql else "none"))
    chart = "line" if group_by!="none" else "bar"

    return {
        "metric": {"op": op, "column": col},
        "filters": {"year": year, "weeks": weeks, "month": month, "where": where},
        "group_by": group_by,
        "chart": chart,
        "natural_language_goal": q
    }

plan = call_llm_plan(txt, SCHEMA_DOC) or regex_fallback(txt)

# Si le LLM renvoie une colonne qui n'existe pas, on utilise les alias pour corriger
def resolve_plan_column(col: Optional[str]) -> Optional[str]:
    if not col:
        return None
    if col in df.columns:
        return col
    # tente un mapping via alias (sur clés exactes)
    col_lc = col.lower()
    if col_lc in SYN_TO_COL:
        mapped = SYN_TO_COL[col_lc]
        if mapped in df.columns:
            return mapped
    # tentative de rapprochement simple snake
    col_sn = snake(col_lc)
    if col_sn in df.columns:
        return col_sn
    # dernier recours: première numérique
    return NUMERIC_COLS[0] if NUMERIC_COLS else (df.columns[0] if len(df.columns) else None)

if "metric" in plan:
    plan["metric"]["column"] = resolve_plan_column(plan.get("metric", {}).get("column"))

with st.expander("🧭 Plan interprété (après alias)"):
    st.json(plan)

# =========================================
# 7) Exécution (filtres + groupby + agrégats)
# =========================================
def apply_filters(dd: pd.DataFrame, plan: Dict[str, Any]) -> Tuple[pd.DataFrame, Optional[str]]:
    out = dd.copy()
    filters = plan.get("filters") or {}

    # année via iso_year
    if filters.get("year") is not None and "iso_year" in out.columns:
        out = out[out["iso_year"] == int(filters["year"])]

    # mois via month ou via datetime
    if filters.get("month") is not None:
        if "month" in out.columns:
            out = out[out["month"] == int(filters["month"])]
        else:
            time_col = next((c for c in out.columns if pd.api.types.is_datetime64_any_dtype(out[c])), None)
            if time_col:
                out = out[out[time_col].dt.month == int(filters["month"])]

    # semaines via iso_week
    if (w := filters.get("weeks")) and "iso_week" in out.columns:
        out = out[(out["iso_week"] >= int(w["from"])) & (out["iso_week"] <= int(w["to"]))]

    # where libres
    for cond in filters.get("where", []) or []:
        col, op, val = cond.get("column"), cond.get("op"), cond.get("value")
        if not col or col not in out.columns: continue
        s = out[col]
        # cast val
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
        # opérateur
        if op == "=": out = out[s == val_cast]
        elif op == "!=": out = out[s != val_cast]
        elif op == ">=" and pd.api.types.is_numeric_dtype(s): out = out[s >= val_cast]
        elif op == "<=" and pd.api.types.is_numeric_dtype(s): out = out[s <= val_cast]
        elif op == "contains": out = out[s.astype(str).str.contains(str(val), case=False, na=False)]

    # clé de groupement potentielle
    gby = plan.get("group_by","none")
    key = None
    if gby == "week" and "iso_week" in out.columns: key = "iso_week"
    elif gby == "month" and "month" in out.columns: key = "month"
    elif gby == "day" and "date_only" in out.columns: key = "date_only"

    return out, key

def aggregate(dd: pd.DataFrame, plan: Dict[str, Any], key: Optional[str]) -> Tuple[pd.DataFrame, str, str]:
    metric = (plan.get("metric") or {})
    op = (metric.get("op") or "sum").lower()
    col = metric.get("column") or (NUMERIC_COLS[0] if NUMERIC_COLS else dd.columns[0])

    # sécurité sur le type
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

# =========================================
# 8) RUN
# =========================================
try:
    plan_llm = call_llm_plan(txt, SCHEMA_DOC)
    plan = plan_llm or regex_fallback(txt)
    # Re-résolution de colonne si besoin (après LLM)
    if "metric" in plan:
        plan["metric"]["column"] = resolve_plan_column(plan.get("metric", {}).get("column"))

    with st.expander("🧭 Plan interprété (avec alias)"):
        st.json(plan)

    df_filt, group_key = apply_filters(df, plan)
    if df_filt.empty:
        st.warning("Aucun enregistrement après filtres.")
        st.stop()

    result, x, y = aggregate(df_filt, plan, group_key)
    st.dataframe(result, use_container_width=True)

    chart_kind = plan.get("chart","none")
    if chart_kind != "none":
        title = plan.get("natural_language_goal","Résultat")
        if x in ("metric","value"):
            fig = px.bar(result, x=x, y=y, title=title)
        else:
            if chart_kind == "line":
                fig = px.line(result, x=x, y=y, markers=True, title=title)
            else:
                fig = px.bar(result, x=x, y=y, title=title)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("ℹ️ Alias utilisés & schéma"):
        st.write({"aliases": ALIASES})
        st.write("Colonnes & types:", schema_detected)

except Exception as e:
    st.exception(e)

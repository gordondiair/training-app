# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login, sidebar_logout_bottom

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

# =========================
# Imports
# =========================
import os, re, json
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests  # ← on utilise l’API REST OpenAI (pas de SDK)

from utils_ui import inject_base_css, hero, section, stat_cards, callout, app_footer
inject_base_css()


# =========================
# PAGE
# =========================
st.set_page_config(page_title="🤖 Questions — strava_import", layout="wide")
st.title("🤖 Questions (réponse en phrases) — strava_import")
sidebar_logout_bottom(sb)

user = st.session_state.get("user")
if not user:
    st.stop()

# =========================
# Clé OpenAI : chargement + vérifs hors-ligne
# =========================
def _detect_key_source() -> str:
    if "OPENAI_API_KEY" in st.secrets and st.secrets.get("OPENAI_API_KEY"):
        return "st.secrets"
    if os.getenv("OPENAI_API_KEY"):
        return "env"
    return "absent"

def _validate_key_format(k: str) -> Dict[str, Any]:
    if not k:
        return {"present": False, "prefix_ok": False, "length_ok": False, "charset_ok": False}
    prefix_ok = bool(re.match(r"^(sk|oa|opai|sess)-", k))
    length_ok = len(k) >= 30
    charset_ok = bool(re.match(r"^[A-Za-z0-9\-\_\~]+$", k))
    return {"present": True, "prefix_ok": prefix_ok, "length_ok": length_ok, "charset_ok": charset_ok}

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
key_source = _detect_key_source()
key_checks = _validate_key_format(OPENAI_API_KEY)

with st.expander("🔐 État de la clé OpenAI (aucun appel réseau)"):
    st.write("- Source détectée :", f"`{key_source}`")
    st.write("- Clé présente :", "✅" if key_checks["present"] else "❌")
    if key_checks["present"]:
        masked = (OPENAI_API_KEY[:4] + "…" + OPENAI_API_KEY[-4:]) if len(OPENAI_API_KEY) >= 10 else "…"
        st.write("- Aperçu masqué :", masked)
        st.write("- Préfixe attendu ('sk-', 'oa-', etc.) :", "✅" if key_checks["prefix_ok"] else "⚠️")
        st.write("- Longueur raisonnable (≥30) :", "✅" if key_checks["length_ok"] else "⚠️")
        st.write("- Caractères autorisés :", "✅" if key_checks["charset_ok"] else "⚠️")
        if not all([key_checks["prefix_ok"], key_checks["length_ok"], key_checks["charset_ok"]]):
            st.info("Ces vérifications sont locales. Pour confirmer la validité côté OpenAI, utilise le test ci-dessous.")

# =========================
# Helpers
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
    if df.empty:
        return df
    rename = {c: snake(c) for c in df.columns}
    df = df.rename(columns=rename)
    for c in df.columns:
        if any(k in c for k in ["date","time","start","end","_at","_ts"]):
            try:
                df[c] = pd.to_datetime(df[c], errors="coerce", utc=True)
            except Exception:
                pass
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
    st.markdown("Je n’ai trouvé aucune activité dans ta table `strava_import` pour cet utilisateur.")
    st.stop()

NUMERIC_COLS = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

# =========================
# Synonymes FR -> colonnes existantes (utilisé par l'agent)
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
    "avg_pace_min_per_km": ["avg_pace_min_per_km", "allure moyenne", "allure", "min/km", "min par km"],
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

def resolve_column(col: Optional[str]) -> Optional[str]:
    if not col:
        return NUMERIC_COLS[0] if NUMERIC_COLS else (df.columns[0] if len(df.columns) else None)
    if col in df.columns:
        return col
    col_lc = col.lower()
    if col_lc in SYN_TO_COL and SYN_TO_COL[col_lc] in df.columns:
        return SYN_TO_COL[col_lc]
    col_sn = snake(col_lc)
    if col_sn in df.columns:
        return col_sn
    return NUMERIC_COLS[0] if NUMERIC_COLS else (df.columns[0] if len(df.columns) else None)

# =========================
# Filtres + agrégations
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
        try:
            out = out[(out["iso_week"] >= int(w["from"])) & (out["iso_week"] <= int(w["to"]))]
        except Exception:
            pass

    for cond in F.get("where", []) or []:
        col, op, val = cond.get("column"), cond.get("op"), cond.get("value")
        if not col or col not in out.columns:
            continue
        s = out[col]
        if pd.api.types.is_numeric_dtype(s):
            try: val_cast = float(val)
            except: 
                continue
        elif pd.api.types.is_bool_dtype(s):
            val_cast = str(val).lower() in ("true","1","yes","oui")
        elif pd.api.types.is_datetime64_any_dtype(s):
            try: val_cast = pd.to_datetime(val, utc=True)
            except: 
                continue
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
        g = dd.groupby(key, dropna=False)
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

# =========================
# Mémoire légère (filtres implicites)
# =========================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_filters" not in st.session_state:
    st.session_state.agent_filters = {"year": None, "type": None}

# =========================
# UI — Saisie question
# =========================
txt = st.text_input("Pose ta question :", placeholder="Ex: d+ moyen par semaine cette année, pour les runs")
go = st.button("Envoyer")

if not (txt and go):
    # Petit test en ligne (optionnel) dans ce cas-ci aussi
    with st.expander("🧪 Test réel de l'API (optionnel)"):
        st.caption("Appel minimal pour confirmer la clé côté OpenAI (aucun SDK requis).")
        if st.button("▶️ Lancer un mini-appel API"):
            if not OPENAI_API_KEY:
                st.error("Aucune clé détectée.")
            else:
                try:
                    r = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [{"role": "user", "content": "Réponds UNIQUEMENT: OK"}],
                            "max_tokens": 2,
                            "temperature": 0
                        },
                        timeout=20,
                    )
                    if r.status_code == 200:
                        content = (r.json()["choices"][0]["message"]["content"] or "").strip()
                        st.success(f"Réponse API: {content!r}  → ✅ clé opérationnelle")
                    else:
                        st.error(f"Erreur API ({r.status_code}) → {r.text[:400]}")
                except Exception as e:
                    st.error(f"Échec de l'appel API → {e}")
    st.stop()

# =========================
# Agent via API REST OpenAI (function calling)
# =========================
def tool_list_columns() -> Dict[str, Any]:
    return {"columns": [{"name": c, "type": dtype_str(df[c])} for c in df.columns]}

def tool_aggregate_dataframe(filters: Optional[Dict[str, Any]], group_by: str, op: str, column: str) -> Dict[str, Any]:
    F = {"year": st.session_state.agent_filters.get("year"),
         "month": None, "weeks": None, "where": []}
    if filters:
        for k, v in filters.items():
            if v is not None:
                F[k] = v

    if st.session_state.agent_filters.get("type") and "activity_type" in df.columns:
        F["where"] = (F.get("where") or []) + [{"column":"activity_type","op":"=","value":st.session_state.agent_filters["type"]}]

    col = resolve_column(column)
    dd, group_key = apply_filters(df, {"filters":F, "group_by":group_by})
    if dd.empty:
        return {"empty": True}

    res, x, y = aggregate(dd, {"metric":{"op":op,"column":col},"group_by":group_by}, group_key)

    if x in ("metric","value"):
        val = res.iloc[0][y]
        return {
            "empty": False,
            "mode": "single",
            "label": f"{op}_{col}",
            "value": None if pd.isna(val) else float(val),
            "filters": F,
            "group_by": group_by
        }
    else:
        rows = []
        for _, row in res.iterrows():
            rows.append({"group": str(row[x]), "value": None if pd.isna(row[y]) else float(row[y])})
        return {
            "empty": False,
            "mode": "grouped",
            "rows": rows,
            "metric": f"{op}_{col}",
            "filters": F,
            "group_by": group_key or "none"
        }

# Mise à jour mémoire implicite
txt_low = txt.lower()
if "run" in txt_low or "course" in txt_low:
    st.session_state.agent_filters["type"] = "run"
if "cette année" in txt_low:
    st.session_state.agent_filters["year"] = date.today().year
m = re.search(r"(20\d{2})", txt_low)
if m:
    st.session_state.agent_filters["year"] = int(m.group(1))

if not OPENAI_API_KEY:
    st.markdown("Je ne peux pas répondre pour l’instant : clé OpenAI absente.")
    st.stop()

SYSTEM = """
Tu es un analyste d'entraînement. Tu réponds en français, de façon claire et naturelle.
- Quand un calcul est nécessaire, appelle la fonction aggregate_dataframe avec des filtres raisonnables (par ex. activity_type='run' si la question parle de course), puis explique le résultat simplement (phrases).
- Si tu ignores les colonnes disponibles, appelle list_columns.
- N'invente pas de colonnes.
- Reste concis et utile. Pas de tableaux sauf si l'utilisateur le demande explicitement.
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_columns",
            "description": "Retourne la liste des colonnes et leurs types détectés.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "aggregate_dataframe",
            "description": "Agrège le DataFrame avec filtres implicites/explicites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "properties": {
                            "year": {"type":"integer", "nullable": True},
                            "weeks": {"type":"object","properties":{
                                "from":{"type":"integer"}, "to":{"type":"integer"}
                            }, "nullable": True},
                            "month": {"type":"integer","minimum":1,"maximum":12,"nullable": True},
                            "where": {"type":"array","items":{
                                "type":"object",
                                "properties": {
                                    "column":{"type":"string"},
                                    "op":{"type":"string","enum":["<=",">=","=","!=","contains"]},
                                    "value": {}
                                },
                                "required":["column","op","value"]
                            }}
                        }
                    },
                    "group_by": {"type":"string","enum":["week","month","day","none"]},
                    "op": {"type":"string","enum":["sum","avg","max","min","count"]},
                    "column": {"type":"string"}
                },
                "required":["op","column","group_by"]
            }
        }
    }
]

messages = [{"role":"system","content": SYSTEM}] + st.session_state.chat_history + [
    {"role":"user","content": txt}
]

def _openai_chat(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text[:500]}")
    return r.json()

# 1) Appel initial (avec outils)
resp = _openai_chat({
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "messages": messages,
    "tools": tools,
    "tool_choice": "auto"
})

final_text = None
first_choice = (resp.get("choices") or [{}])[0]
assistant_msg = first_choice.get("message") or {}
tool_calls = assistant_msg.get("tool_calls")

if tool_calls:
    # Ajoute le message assistant avec tool_calls
    messages.append({"role": "assistant", "content": assistant_msg.get("content", ""), "tool_calls": tool_calls})

    # Exécute chaque tool call
    for tc in tool_calls:
        fn_name = tc["function"]["name"]
        args = json.loads(tc["function"].get("arguments") or "{}")
        if fn_name == "list_columns":
            out = tool_list_columns()
        elif fn_name == "aggregate_dataframe":
            out = tool_aggregate_dataframe(**args)
        else:
            out = {"error": "unknown_tool"}

        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "name": fn_name,
            "content": json.dumps(out, ensure_ascii=False)
        })

    # 2) Appel de suivi (sans outils) pour la réponse finale
    resp2 = _openai_chat({
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "messages": messages
    })
    final_text = ((resp2.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
else:
    final_text = assistant_msg.get("content", "").strip()

# Mémorisation de l'échange
st.session_state.chat_history += [
    {"role":"user","content": txt},
    {"role":"assistant","content": final_text}
]

# =========================
# Affichage final — PHRASES UNIQUEMENT
# =========================
st.markdown(final_text)

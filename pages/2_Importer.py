# pages/02_Importer.py
import io
import re
import math
import unicodedata
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

import pandas as pd
import streamlit as st

from supa import get_client
from utils import require_login
from utils import sidebar_logout_bottom

st.set_page_config(page_title="Importer — Strava", layout="wide")

# =========================
# Helpers
# =========================
_NUMERIC_STR_RE = re.compile(r'^[+-]?\d+(\.\d+)?$')

def _looks_numeric_str(s: Any) -> bool:
    return isinstance(s, str) and _NUMERIC_STR_RE.match(s.strip()) is not None

def _coerce_numeric_str_any(s: Any):
    """Si s est '7.0'/'7'/'-3.50', renvoie int ou float. Sinon renvoie s inchangé."""
    if not _looks_numeric_str(s):
        return s
    try:
        f = float(s.strip())
    except Exception:
        return s
    # 7.0 -> 7
    if math.isfinite(f) and float(f).is_integer():
        return int(f)
    return f if math.isfinite(f) else None

def _snake(s: str) -> str:
    if s is None:
        return s
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.strip().lower()
    s = s.replace(".", "_").replace("-", "_").replace("/", "_").replace(" ", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s

def _to_bool(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in ("true","1","yes","y","vrai","oui"):
        return True
    if s in ("false","0","no","n","faux","non"):
        return False
    return None

def _to_int(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() == "":
        return None
    # S'il arrive en str "7.0", convertissons proprement
    x = _coerce_numeric_str_any(x)
    try:
        return int(x)
    except Exception:
        try:
            return int(float(str(x).strip()))
        except Exception:
            return None

def _to_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() == "":
        return None
    # Convertir "7.0" -> 7.0
    x = _coerce_numeric_str_any(x)
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None

def _to_time(s):
    """Renvoie 'HH:MM:SS' (JSON-safe) ou None."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return None
    txt = str(s).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(txt, fmt).time()
            return t.strftime("%H:%M:%S")
        except Exception:
            continue
    return None

def _to_timestamptz(s):
    """Renvoie ISO 8601 (UTC si pas de tz) ou None."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return None
    txt = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(txt, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            continue
    try:
        dt = pd.to_datetime(txt, utc=True)
        return dt.isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

def _json_safe_value(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except Exception:
        pass
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    return v

def _json_safe_row(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: _json_safe_value(v) for k, v in d.items()}

# =========================
# Schéma / Types
# =========================
TABLE_COLS = [
    "activity_id","activity_date","activity_name","activity_type","activity_description",
    "elapsed_time","distance","max_heart_rate","relative_effort","commute","activity_private_note",
    "activity_gear","filename","athlete_weight","bike_weight","elapsed_time_1","moving_time",
    "distance_1","max_speed","average_speed","elevation_gain","elevation_loss","elevation_low",
    "elevation_high","max_grade","average_grade","average_positive_grade","average_negative_grade",
    "max_cadence","average_cadence","max_heart_rate_1","average_heart_rate","max_watts",
    "average_watts","calories","max_temperature","average_temperature","relative_effort_1",
    "total_work","number_of_runs","uphill_time","downhill_time","other_time","perceived_exertion",
    "type_text","start_time","weighted_average_power","power_count","prefer_perceived_exertion",
    "perceived_relative_effort","commute_1","total_weight_lifted","from_upload","grade_adjusted_distance",
    "weather_observation_time","weather_condition","weather_temperature","apparent_temperature",
    "dewpoint","humidity","weather_pressure","wind_speed","wind_gust","wind_bearing",
    "precipitation_intensity","sunrise_time","sunset_time","moon_phase","bike_text","gear_text",
    "precipitation_probability","precipitation_type","cloud_cover","weather_visibility","uv_index",
    "weather_ozone","jump_count","total_grit","average_flow","flagged","average_elapsed_speed",
    "dirt_distance","newly_explored_distance","newly_explored_dirt_distance","activity_count",
    "total_steps","carbon_saved","pool_length","training_load","intensity",
    "average_grade_adjusted_pace","timer_time","total_cycles","recovery","with_pet","competition",
    "long_run","for_a_cause","media_text",
]

SPECIAL_HEADER_MAP = {
    "type": "type_text",
    "media": "media_text",
    "bike": "bike_text",
    "gear": "gear_text",
}

BOOL_COLS = {"commute","prefer_perceived_exertion","commute_1","from_upload","flagged","with_pet","competition","long_run","for_a_cause"}
INT_COLS  = {"elapsed_time","activity_id","uphill_time","downhill_time","other_time","power_count","perceived_relative_effort","relative_effort_1","number_of_runs","jump_count","total_cycles","timer_time","max_heart_rate_1","average_heart_rate","total_steps"}
TIME_COLS = {"start_time","sunrise_time","sunset_time"}
TS_COLS   = {"activity_date","weather_observation_time"}
FLOAT_COLS = set(TABLE_COLS) - BOOL_COLS - INT_COLS - TIME_COLS - TS_COLS - {
    "type_text","activity_name","activity_type","activity_description","activity_private_note",
    "activity_gear","filename","weather_condition","bike_text","gear_text","precipitation_type","media_text"
}
TEXT_COLS = set(TABLE_COLS) - (BOOL_COLS | INT_COLS | TIME_COLS | TS_COLS | FLOAT_COLS)

# Convertisseurs par colonne
CONVERTER_BY_COL: Dict[str, Any] = {}
for c in BOOL_COLS:  CONVERTER_BY_COL[c] = _to_bool
for c in INT_COLS:   CONVERTER_BY_COL[c] = _to_int
for c in FLOAT_COLS: CONVERTER_BY_COL[c] = _to_float
for c in TIME_COLS:  CONVERTER_BY_COL[c] = _to_time
for c in TS_COLS:    CONVERTER_BY_COL[c] = _to_timestamptz
for c in TEXT_COLS:  CONVERTER_BY_COL[c] = lambda x: None if (x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip()=="") else str(x)

# Tolerances doublons
D_TOL_KM   = 0.2
DPLUS_TOL  = 50.0
DMOINS_TOL = 50.0

# =========================
# Auth
# =========================
sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state["user"]

st.title("📥 Importer — Strava (CSV)")
sidebar_logout_bottom(sb)

# =========================
# UI
# =========================
st.markdown("Charge ton fichier **activities.csv** exporté depuis Strava.")
up = st.file_uploader("Déposer le CSV Strava", type=["csv"], accept_multiple_files=False)

global_action_col, apply_col = st.columns([3,1])
if "import_decisions" not in st.session_state:
    st.session_state.import_decisions = {}

# =========================
# DB I/O
# =========================
def fetch_existing_rows(min_dt_iso: str, max_dt_iso: str) -> List[Dict[str, Any]]:
    sel_cols = ["id","user_id","activity_id","activity_date","activity_name","activity_type","distance","elevation_gain","elevation_loss","moving_time"]
    q = (sb.table("strava_import")
            .select(",".join(sel_cols))
            .eq("user_id", user["id"])
            .gte("activity_date", min_dt_iso)
            .lte("activity_date", max_dt_iso)
            .order("activity_date", desc=False))
    res = q.execute()
    return res.data or []

def _finalize_payload(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    1) Conversion par colonne (bool/int/float/time/ts/text)
    2) Coercition universelle des chaînes numériques restantes
    3) Re-forçage INT: si valeur numérique non-entière envoyée en INT -> int(float(...))
    4) JSON safe
    """
    payload: Dict[str, Any] = {}
    for k in TABLE_COLS:
        conv = CONVERTER_BY_COL.get(k, lambda x: x)
        v = conv(row_dict.get(k, None))

        # (2) convertir toute chaîne "7.0" restante en nombre
        v = _coerce_numeric_str_any(v)

        # (3) pour les colonnes INT, si on a encore un float -> cast int
        if k in INT_COLS:
            if isinstance(v, float) and math.isfinite(v):
                v = int(v)
            elif isinstance(v, str) and _looks_numeric_str(v):
                try:
                    v = int(float(v))
                except Exception:
                    v = None

        payload[k] = v

    payload["user_id"] = user["id"]
    return _json_safe_row(payload)

def do_upserts(rows_insert: List[Dict[str, Any]], rows_replace: List[Tuple[int, Dict[str, Any]]], rows_combine: List[Tuple[int, Dict[str, Any]]]):
    if rows_insert:
        sb.table("strava_import").upsert(rows_insert, on_conflict="user_id,activity_id").execute()
    for db_id, payload in rows_replace:
        sb.table("strava_import").update(payload).eq("id", db_id).eq("user_id", user["id"]).execute()
    for db_id, payload in rows_combine:
        curr = sb.table("strava_import").select("*").eq("id", db_id).single().execute().data
        if not curr:
            continue
        to_set = {}
        for k, v in payload.items():
            if k in ("id","user_id","created_at","updated_at"):
                continue
            if k not in TABLE_COLS:
                continue
            if (curr.get(k) is None) and (v is not None and v != ""):
                to_set[k] = v
        if to_set:
            sb.table("strava_import").update(_json_safe_row(to_set)).eq("id", db_id).eq("user_id", user["id"]).execute()

# =========================
# Import
# =========================
if up:
    raw = up.read()
    df = pd.read_csv(io.BytesIO(raw))

    # headers
    df.columns = [_snake(c) for c in df.columns]
    df = df.rename(columns={k: v for k, v in SPECIAL_HEADER_MAP.items() if k in df.columns})

    # aligner colonnes
    for col in TABLE_COLS:
        if col not in df.columns:
            df[col] = None
    df = df[TABLE_COLS]

    # typage au niveau DF (facultatif)
    for c in df.columns:
        conv = CONVERTER_BY_COL.get(c)
        if conv:
            df[c] = df[c].map(conv)

    # convertir les chaînes numériques résiduelles (universel)
    for c in df.columns:
        df[c] = df[c].map(_coerce_numeric_str_any)

    # NaN -> None
    df = df.where(pd.notna(df), None)

    # fenêtre temporelle
    try:
        min_dt = pd.to_datetime(df["activity_date"]).min()
        max_dt = pd.to_datetime(df["activity_date"]).max()
        if pd.isna(min_dt) or pd.isna(max_dt):
            min_dt = pd.Timestamp.utcnow() - pd.Timedelta(days=3650)
            max_dt = pd.Timestamp.utcnow() + pd.Timedelta(days=1)
    except Exception:
        min_dt = pd.Timestamp.utcnow() - pd.Timedelta(days=3650)
        max_dt = pd.Timestamp.utcnow() + pd.Timedelta(days=1)

    existing = fetch_existing_rows(min_dt.isoformat(), max_dt.isoformat())

    def _date_only(ts):
        try:
            return pd.to_datetime(ts).date()
        except Exception:
            return None

    by_day: Dict[Any, List[Dict[str, Any]]] = {}
    for r in existing:
        d = _date_only(r.get("activity_date"))
        by_day.setdefault(d, []).append(r)

    # doublons
    rows_to_show = []
    duplicate_found = False
    for idx, row in df.iterrows():
        d_day = _date_only(row.get("activity_date"))
        dist_km_new = _to_float(row.get("distance")) or 0.0
        dplus_new   = _to_float(row.get("elevation_gain")) or 0.0
        dmoins_new  = _to_float(row.get("elevation_loss")) or 0.0

        candidates = by_day.get(d_day, [])
        match = None
        for cand in candidates:
            dist_km_old = _to_float(cand.get("distance")) or 0.0
            dplus_old   = _to_float(cand.get("elevation_gain")) or 0.0
            dmoins_old  = _to_float(cand.get("elevation_loss")) or 0.0
            if abs(dist_km_new - dist_km_old) <= D_TOL_KM and abs(dplus_new - dplus_old) <= DPLUS_TOL and abs(dmoins_new - dmoins_old) <= DMOINS_TOL:
                match = cand
                duplicate_found = True
                break

        rows_to_show.append((idx, row.to_dict(), match))

    # ===== Aucun doublon -> import silencieux =====
    if not duplicate_found:
        insert_payloads: List[Dict[str, Any]] = []
        for (_, new_row, _) in rows_to_show:
            payload = _finalize_payload(new_row)
            insert_payloads.append(payload)

        try:
            do_upserts(insert_payloads, [], [])
            st.success(f"Import terminé ✅  | Insérés: {len(insert_payloads)}")
            st.balloons()
            with st.expander("Aperçu (premières lignes importées)", expanded=False):
                st.dataframe(pd.DataFrame(insert_payloads).head(10))
        except Exception as e:
            # mini diagnostic utile
            st.error(f"Erreur pendant l'import : {e}")
            with st.expander("Diagnostic rapide"):
                bad_cols = []
                for k in TABLE_COLS:
                    # Cherche des valeurs texte numériques restantes
                    if any(_looks_numeric_str(x) for x in pd.Series([r.get(k) for _, r, _ in rows_to_show])):
                        bad_cols.append(k)
                st.write("Colonnes contenant encore des *chaînes* numériques potentielles :", bad_cols)

    # ===== Doublons -> UI décisions =====
    else:
        with st.expander("Aperçu rapide du parsing (premières lignes)", expanded=False):
            st.dataframe(df.head(10))

        st.subheader("Vérification des doublons et choix d’action")

        with global_action_col:
            st.write("Actions globales :")
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("Tout combiner"):
                for (i, _, m) in rows_to_show:
                    st.session_state.import_decisions[i] = "combine" if m else "insert"
            if c2.button("Tout remplacer"):
                for (i, _, m) in rows_to_show:
                    st.session_state.import_decisions[i] = "replace" if m else "insert"
            if c3.button("Tout ignorer"):
                for (i, _, m) in rows_to_show:
                    st.session_state.import_decisions[i] = "ignore"
            if c4.button("Tout insérer quand même"):
                for (i, _, m) in rows_to_show:
                    st.session_state.import_decisions[i] = "insert"

        st.markdown("---")

        insert_payloads: List[Dict[str, Any]] = []
        replace_payloads: List[Tuple[int, Dict[str, Any]]] = []
        combine_payloads: List[Tuple[int, Dict[str, Any]] ] = []

        for (i, new_row, existing_row) in rows_to_show:
            box = st.container(border=True)
            with box:
                left, right = st.columns([3,2])

                try:
                    date_lbl = pd.to_datetime(new_row.get("activity_date")).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_lbl = "?"

                with left:
                    st.markdown(f"### {new_row.get('activity_name') or 'Activité'} — {date_lbl}")
                    st.caption(f"Type: {new_row.get('activity_type') or '-'} | Distance: {new_row.get('distance')} km | D+: {new_row.get('elevation_gain')} m | D-: {new_row.get('elevation_loss')} m")
                with right:
                    default_choice = st.session_state.import_decisions.get(i) or ("replace" if existing_row else "insert")
                    choice = st.radio(
                        f"Action pour la ligne #{i}",
                        options=["combine","replace","ignore","insert"],
                        captions=["Compléter la ligne DB avec les infos manquantes du CSV",
                                  "Remplacer entièrement la ligne DB par le CSV",
                                  "Ignorer cette ligne",
                                  "Insérer une nouvelle ligne quand même"],
                        index=["combine","replace","ignore","insert"].index(default_choice),
                        key=f"choice_{i}",
                        horizontal=True
                    )
                    st.session_state.import_decisions[i] = choice

                if existing_row:
                    st.write("**Dans la base (potentiel doublon):**")
                    cdb1, cdb2, cdb3, cdb4 = st.columns(4)
                    cdb1.write(f"ID: `{existing_row['id']}`")
                    cdb2.write(f"Date: {existing_row.get('activity_date')}")
                    cdb3.write(f"Dist (km): {existing_row.get('distance')}")
                    cdb4.write(f"D+ / D-: {existing_row.get('elevation_gain')} / {existing_row.get('elevation_loss')}")
                else:
                    st.info("Aucune ligne existante trouvée pour cette date/valeurs.")

                st.write("**Ligne importée (CSV):**")
                cnp1, cnp2, cnp3, cnp4 = st.columns(4)
                cnp1.write(f"Activity ID: {new_row.get('activity_id')}")
                cnp2.write(f"Date: {new_row.get('activity_date')}")
                cnp3.write(f"Dist (km): {new_row.get('distance')}")
                cnp4.write(f"D+ / D-: {new_row.get('elevation_gain')} / {new_row.get('elevation_loss')}")

                payload = _finalize_payload(new_row)

                if choice == "insert" and not existing_row:
                    insert_payloads.append(payload)
                elif choice == "replace" and existing_row:
                    replace_payloads.append((existing_row["id"], payload.copy()))
                elif choice == "combine" and existing_row:
                    combine_payloads.append((existing_row["id"], payload))

                st.markdown("---")

        with apply_col:
            if st.button("Appliquer les actions", type="primary", use_container_width=True):
                try:
                    do_upserts(insert_payloads, replace_payloads, combine_payloads)
                    st.success(
                        f"Import terminé ✅  | Insérés: {len(insert_payloads)}  •  Remplacés: {len(replace_payloads)}  •  "
                        f"Combinés: {len(combine_payloads)}  •  Ignorés: {len(rows_to_show) - (len(insert_payloads)+len(replace_payloads)+len(combine_payloads))}"
                    )
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur pendant l'import : {e}")

else:
    st.info("Dépose un fichier CSV Strava pour commencer.")

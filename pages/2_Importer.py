# pages/2_Importer.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from supa import get_client
from utils import require_login

# ===== Config =====
st.set_page_config(page_title="Importer mes données", layout="wide")
KM_TOLERANCE = 0.3
ELEV_TOLERANCE = 40
TABLE = "journal"

# ===== Auth =====
sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state.get("user")
if not user:
    st.stop()

# Appel logout optionnel (si absent, on ignore)
try:
    from utils import sidebar_logout_bottom
    if callable(sidebar_logout_bottom):
        sidebar_logout_bottom()
except Exception:
    pass

st.title("📥 Importer mes données")

# ===== Helpers =====
def to_float(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return None
    try: return float(str(x).strip().replace(",", "."))
    except: return None

def to_int(x):
    v = to_float(x)
    return int(round(v)) if v is not None else None

def hhmmss_to_seconds(s):
    if s is None or (isinstance(s, float) and np.isnan(s)): return None
    s = str(s).strip()
    if ":" not in s:
        try: return int(float(s))
        except: return None
    try:
        parts = [int(p) for p in s.split(":")]
        if len(parts) == 3: h, m, s2 = parts
        elif len(parts) == 2: h, m, s2 = 0, parts[0], parts[1]
        else: return None
        return h*3600 + m*60 + s2
    except: return None

def parse_date_any(x):
    if pd.isna(x): return None
    s = str(x).strip()
    fmts = [
        "%Y-%m-%d","%d/%m/%Y","%Y-%m-%d %H:%M:%S","%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y","%m/%d/%Y %H:%M:%S","%Y-%m-%dT%H:%M:%S%z","%Y-%m-%dT%H:%M:%S"
    ]
    for f in fmts:
        try: return datetime.strptime(s, f).date().isoformat()
        except: pass
    try:
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        return None if pd.isna(dt) else dt.date().isoformat()
    except:
        return None

def load_db_rows_for_date(day_iso):
    res = sb.table(TABLE).select("*").eq("user_id", user["id"]).eq("date", day_iso).execute()
    return res.data or []

def is_similar(existing, imported):
    if existing.get("date") != imported.get("date"): return False
    def close(a,b,tol):
        if a is None or b is None: return False
        return abs(a-b) <= tol
    km_ok = close(to_float(existing.get("distance_course_km")), to_float(imported.get("distance_course_km")), KM_TOLERANCE)
    dplus_ok = close(to_float(existing.get("dplus_course_m")), to_float(imported.get("dplus_course_m")), ELEV_TOLERANCE)
    dmoins_ok = close(to_float(existing.get("dmoins_course_m")), to_float(imported.get("dmoins_course_m")), ELEV_TOLERANCE)
    return km_ok and (dplus_ok or dmoins_ok)

def combine_rows(existing, imported):
    merged = existing.copy()
    for k in ["distance_course_km","dplus_course_m","dmoins_course_m","temps_course_min"]:
        ev, iv = existing.get(k), imported.get(k)
        if (ev is None or ev == "" or (isinstance(ev, float) and np.isnan(ev))) and iv not in [None, ""]:
            merged[k] = iv
    return merged

# ===== Parsers =====
def parse_garmin_csv(df):
    cols = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n.lower() in cols: return cols[n.lower()]
        return None
    c_date  = pick("Date","Activity Date","Start Time")
    c_km    = pick("Distance","Distance (km)","Distance (KM)")
    c_gain  = pick("Elevation Gain","Elev Gain","Total Ascent","D+ (m)")
    c_loss  = pick("Elevation Loss","Elev Loss","Total Descent","D- (m)")
    c_time  = pick("Elapsed Time","Duration","Moving Time")
    out = []
    for _, r in df.iterrows():
        d   = parse_date_any(r.get(c_date)) if c_date else None
        km  = to_float(r.get(c_km)) if c_km else None
        # Sécurité : certains exports Garmin mettent la distance en mètres
        if km is not None and km > 200: km = km/1000.0
        dplus  = to_int(r.get(c_gain)) if c_gain else None
        dmoins = to_int(r.get(c_loss)) if c_loss else None
        sec    = hhmmss_to_seconds(r.get(c_time)) if c_time else None
        mins   = int(round(sec/60)) if sec is not None else None
        out.append({
            "date": d,
            "distance_course_km": km,
            "dplus_course_m": dplus,
            "dmoins_course_m": dmoins,
            "temps_course_min": mins,
        })
    df2 = pd.DataFrame(out)
    return df2.dropna(subset=["date","distance_course_km"]).reset_index(drop=True)

def parse_strava_csv(df):
    """Version km_only : Strava.Distance est déjà en kilomètres."""
    cols = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n.lower() in cols: return cols[n.lower()]
        return None

    c_type = pick("Activity Type","Type")
    if not c_type:
        st.error("Colonne 'Activity Type' (ou 'Type') introuvable dans le CSV Strava.")
        return pd.DataFrame(columns=["date","distance_course_km","dplus_course_m","dmoins_course_m","temps_course_min"])

    # Filtre uniquement RUN (inclut trail/virtual/etc.)
    df = df[df[c_type].astype(str).str.lower().str.contains("run")].copy()
    if df.empty:
        st.warning("Aucune activité de type 'run' trouvée dans le CSV Strava.")
        return pd.DataFrame(columns=["date","distance_course_km","dplus_course_m","dmoins_course_m","temps_course_min"])

    c_date = pick("Activity Date","Start Date Local","Start Date")
    c_dist = pick("Distance")
    c_gain = pick("Elevation Gain","Elev Gain","Total Ascent")
    c_loss = pick("Elevation Loss","Elev Loss","Total Descent")
    c_time = pick("Moving Time","Elapsed Time","Time")

    out = []
    for _, r in df.iterrows():
        d = parse_date_any(r.get(c_date)) if c_date else None

        # ---- KM ONLY ----
        km = to_float(r.get(c_dist)) if c_dist else None

        dplus  = to_int(r.get(c_gain)) if c_gain else None
        dmoins = to_int(r.get(c_loss)) if c_loss else None
        sec    = hhmmss_to_seconds(r.get(c_time)) if c_time else None
        mins   = int(round(sec/60)) if sec is not None else None

        out.append({
            "date": d,
            "distance_course_km": km,
            "dplus_course_m": dplus,
            "dmoins_course_m": dmoins,
            "temps_course_min": mins,
        })

    df2 = pd.DataFrame(out)
    return df2.dropna(subset=["date","distance_course_km"]).reset_index(drop=True)

# ===== Traitement : n’afficher QUE les doublons =====
def process_import(df_common, source_label):
    duplicate_decisions = []   # [(row, similar, choice)]
    to_insert_silent = []      # [row] (aucun affichage)

    for idx, row in df_common.iterrows():
        day = row["date"]
        existing_rows = load_db_rows_for_date(day)

        similar = None
        for ex in existing_rows:
            if is_similar(ex, row):
                similar = ex
                break

        if similar is None:
            to_insert_silent.append(row)   # pas d'affichage
            continue

        # ----- Seulement pour les doublons : afficher comparaison -----
        st.markdown("---")
        st.subheader(f"{source_label} • {day} — {row['distance_course_km']:.2f} km | D+ {row.get('dplus_course_m') or 0} m | D- {row.get('dmoins_course_m') or 0} m")
        st.info("🔁 Doublon potentiel : compare **DB (haut)** vs **Import (bas)**")

        with st.container(border=True):
            st.markdown("**Dans la base (existant)**")
            c1,c2,c3,c4 = st.columns([1,1,1,1.2])
            c1.write(f"**Date**\n{similar.get('date')}")
            c2.write(f"**Km**\n{similar.get('distance_course_km')}")
            c3.write(f"**D+ / D-**\n{similar.get('dplus_course_m')} / {similar.get('dmoins_course_m')}")
            c4.write(f"**Durée (min)**\n{similar.get('temps_course_min') or '-'}")

        with st.container(border=True):
            st.markdown("**Proposé (import)**")
            c1,c2,c3,c4 = st.columns([1,1,1,1.2])
            c1.write(f"**Date**\n{row['date']}")
            c2.write(f"**Km**\n{row['distance_course_km']}")
            c3.write(f"**D+ / D-**\n{row.get('dplus_course_m')} / {row.get('dmoins_course_m')}")
            c4.write(f"**Durée (min)**\n{row.get('temps_course_min') or '-'}")

        choice = st.radio(
            "Que faire ?",
            ["Ignorer", "Insérer (quand même)", "Remplacer (écraser la DB)", "Combiner (compléter l'existant)"],
            key=f"choice_{source_label}_{idx}",
            horizontal=True
        )
        duplicate_decisions.append((row, similar, choice))

    # ----- Application -----
    if (duplicate_decisions or to_insert_silent) and st.button("✅ Appliquer les décisions", key=f"apply_{source_label}"):
        n_ins, n_rep, n_comb, n_skip = 0,0,0,0

        # 1) Insérer silencieusement les nouvelles lignes sans doublon
        for row in to_insert_silent:
            payload = {
                "user_id": user["id"],
                "date": row["date"],
                "distance_course_km": row.get("distance_course_km"),
                "dplus_course_m": row.get("dplus_course_m"),
                "dmoins_course_m": row.get("dmoins_course_m"),
                "temps_course_min": row.get("temps_course_min"),
            }
            sb.table(TABLE).insert(payload).execute()
            n_ins += 1

        # 2) Traiter les doublons affichés
        for row, similar, choice in duplicate_decisions:
            if choice.startswith("Ignorer"):
                n_skip += 1
                continue
            if choice.startswith("Insérer"):
                payload = {
                    "user_id": user["id"],
                    "date": row["date"],
                    "distance_course_km": row.get("distance_course_km"),
                    "dplus_course_m": row.get("dplus_course_m"),
                    "dmoins_course_m": row.get("dmoins_course_m"),
                    "temps_course_min": row.get("temps_course_min"),
                }
                sb.table(TABLE).insert(payload).execute()
                n_ins += 1
            elif choice.startswith("Remplacer"):
                payload = {
                    "user_id": user["id"],
                    "date": row["date"],
                    "distance_course_km": row.get("distance_course_km"),
                    "dplus_course_m": row.get("dplus_course_m"),
                    "dmoins_course_m": row.get("dmoins_course_m"),
                    "temps_course_min": row.get("temps_course_min"),
                }
                sb.table(TABLE).update(payload).eq("id", similar["id"]).execute()
                n_rep += 1
            elif choice.startswith("Combiner"):
                merged = combine_rows(similar, row)
                payload = {
                    "user_id": user["id"],
                    "date": merged.get("date"),
                    "distance_course_km": merged.get("distance_course_km"),
                    "dplus_course_m": merged.get("dplus_course_m"),
                    "dmoins_course_m": merged.get("dmoins_course_m"),
                    "temps_course_min": merged.get("temps_course_min"),
                }
                sb.table(TABLE).update(payload).eq("id", similar["id"]).execute()
                n_comb += 1

        st.success(f"Import terminé : {n_ins} inséré(s), {n_rep} remplacé(s), {n_comb} combiné(s), {n_skip} ignoré(s).")

# ===== UI : Garmin / Strava =====
tab_garmin, tab_strava = st.tabs(["🟧 Garmin", "🟥 Strava"])

with tab_garmin:
    st.subheader("Importer depuis Garmin (CSV d’activités)")
    garmin_file = st.file_uploader("Déposez le CSV Garmin", type=["csv"], key="garmin_csv")
    if garmin_file is not None:
        try:
            df_raw = pd.read_csv(garmin_file)
        except UnicodeDecodeError:
            df_raw = pd.read_csv(garmin_file, encoding="latin1")
        df_common = parse_garmin_csv(df_raw)
        process_import(df_common, "Garmin")

with tab_strava:
    st.subheader("Importer depuis Strava (CSV global `activities.csv`)")
    strava_file = st.file_uploader("Déposez le CSV Strava", type=["csv"], key="strava_csv")
    if strava_file is not None:
        try:
            df_raw = pd.read_csv(strava_file)
        except UnicodeDecodeError:
            df_raw = pd.read_csv(strava_file, encoding="latin1")
        df_common = parse_strava_csv(df_raw)
        process_import(df_common, "Strava")

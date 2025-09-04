# --- Importer.py ---
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from supa import get_client
from utils import require_login, sidebar_logout_bottom

st.set_page_config(page_title="Importer mes données", layout="wide")

# --- Header commun ---
sb = get_client()
u = require_login(sb)  # bloque tant que l'utilisateur n'est pas connecté
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state.get("user")
if not user:
    st.stop()

sidebar_logout_bottom()

st.title("📥 Importer mes données")
st.caption("Choisissez Garmin ou Strava, importez le CSV, et traitez les doublons (ligne DB **au-dessus**, ligne import **en dessous**).")

# =========================
# Config & utilitaires
# =========================

# Seuils “ressemblent” pour km/D+/D-
KM_TOLERANCE = 0.3          # en km
ELEV_TOLERANCE = 40         # en mètres, pour D+ et D-
DATE_TZ = "local"           # on reste simple : date locale (jour civil)

# Nom de la table Supabase à adapter si besoin
TABLE = "sorties"  # ⚠️ utilisez votre nom de table réel

COMMON_COLUMNS = [
    "date",             # date (YYYY-MM-DD)
    "distance_km",      # float
    "d_plus_m",         # int ou None
    "d_moins_m",        # int ou None
    "duree_sec",        # int ou None
    "titre",            # str ou None
    "source",           # "garmin" ou "strava"
    "raw"               # dict brut de la ligne (pour debug)
]

def to_float(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    try:
        s = str(x).strip().replace(",", ".")
        return float(s)
    except:
        return None

def to_int(x):
    v = to_float(x)
    return int(round(v)) if v is not None else None

def hhmmss_to_seconds(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    s = str(s).strip()
    if ":" not in s:
        # parfois Strava met des secondes en entier
        try:
            return int(float(s))
        except:
            return None
    try:
        parts = s.split(":")
        parts = [int(p) for p in parts]
        if len(parts) == 3:
            h, m, s2 = parts
        elif len(parts) == 2:
            h, m, s2 = 0, parts[0], parts[1]
        else:
            return None
        return h*3600 + m*60 + s2
    except:
        return None

def parse_date_any(x):
    # On ne garde que la date (pas l'heure). Supporte plusieurs formats fréquents.
    if pd.isna(x):
        return None
    s = str(x).strip()
    fmts = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.date().isoformat()
        except:
            continue
    # Dernier essai via pandas
    try:
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        if pd.isna(dt):
            return None
        return dt.date().isoformat()
    except:
        return None

def load_db_rows_for_date(day_iso):
    # Récupère les lignes existantes pour l'utilisateur et la date
    res = sb.table(TABLE).select("*").eq("user_id", user["id"]).eq("date", day_iso).execute()
    data = res.data or []
    return data

def is_similar(existing, imported):
    # Conditions de doublon: même date, et km/D+/D- proches
    if existing.get("date") != imported.get("date"):
        return False
    def close(a, b, tol):
        if a is None or b is None:
            return False
        return abs(a - b) <= tol
    km_ok = close(to_float(existing.get("distance_km")), to_float(imported.get("distance_km")), KM_TOLERANCE)
    dplus_ok = close(to_float(existing.get("d_plus_m")), to_float(imported.get("d_plus_m")), ELEV_TOLERANCE)
    dmoins_ok = close(to_float(existing.get("d_moins_m")), to_float(imported.get("d_moins_m")), ELEV_TOLERANCE)
    return km_ok and (dplus_ok or dmoins_ok)

def combine_rows(existing, imported):
    # Compléter l'existant par les infos manquantes de l'import
    merged = existing.copy()
    for k in ["distance_km", "d_plus_m", "d_moins_m", "duree_sec", "titre"]:
        ev = existing.get(k)
        iv = imported.get(k)
        if (ev is None or ev == "" or (isinstance(ev, float) and np.isnan(ev))) and iv not in [None, ""]:
            merged[k] = iv
    # Garder trace de la source
    merged["source"] = existing.get("source") or imported.get("source")
    return merged

# =========================
# Parsing GARMIN
# =========================
def parse_garmin_csv(df):
    """
    Adaptez les noms de colonnes Garmin au besoin. On produit les COMMON_COLUMNS.
    Exemples fréquents Garmin (CSV export): 'Date', 'Distance', 'Elapsed Time', 'Elevation Gain', 'Elevation Loss', 'Activity Title'
    """
    possible = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n.lower() in possible:
                return possible[n.lower()]
        return None

    col_date   = pick("Date", "Activity Date", "Start Time")
    col_km     = pick("Distance", "Distance (km)", "Distance (KM)")
    col_gain   = pick("Elevation Gain", "Elev Gain", "D+ (m)", "Total Ascent")
    col_loss   = pick("Elevation Loss", "Elev Loss", "D- (m)", "Total Descent")
    col_time   = pick("Elapsed Time", "Duration", "Moving Time")
    col_title  = pick("Activity Title", "Title", "Name")

    out = []
    for _, r in df.iterrows():
        d = parse_date_any(r.get(col_date)) if col_date else None
        km = to_float(r.get(col_km)) if col_km else None
        dplus = to_int(r.get(col_gain)) if col_gain else None
        dmoins = to_int(r.get(col_loss)) if col_loss else None
        dur = hhmmss_to_seconds(r.get(col_time)) if col_time else None
        titre = str(r.get(col_title)).strip() if col_title and not pd.isna(r.get(col_title)) else None

        # Garmin met souvent la distance en km déjà. Si > 200 on suppose mètres -> km
        if km is not None and km > 200:
            km = km / 1000.0

        out.append({
            "date": d,
            "distance_km": km,
            "d_plus_m": dplus,
            "d_moins_m": dmoins,
            "duree_sec": dur,
            "titre": titre,
            "source": "garmin",
            "raw": dict(r)
        })
    return pd.DataFrame(out, columns=COMMON_COLUMNS)

# =========================
# Parsing STRAVA
# =========================
def parse_strava_csv(df):
    """
    Strava export 'activities.csv' (toutes activités).
    On filtre uniquement les 'Run' (insensible à la casse, inclut 'Trail Run', 'Virtual Run', etc.).
    Colonnes fréquentes :
      - 'Activity Date' ou 'Start Date Local' (date/heure)
      - 'Activity Type'
      - 'Activity Name'
      - 'Distance' (en mètres)
      - 'Elevation Gain' (m)
      - 'Elevation Loss' (m) [parfois absent]
      - 'Moving Time' (hh:mm:ss) ou 'Elapsed Time'
    """
    cols = {c.lower(): c for c in df.columns}
    def pick(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    col_type  = pick("Activity Type", "Type")
    if not col_type:
        st.error("Impossible de trouver la colonne 'Activity Type' (ou 'Type') dans le CSV Strava.")
        return pd.DataFrame(columns=COMMON_COLUMNS)

    # Filtre run
    df = df[df[col_type].astype(str).str.lower().str.contains("run")].copy()
    if df.empty:
        st.warning("Aucune activité de type 'run' trouvée dans ce fichier Strava.")
        return pd.DataFrame(columns=COMMON_COLUMNS)

    col_date  = pick("Activity Date", "Start Date Local", "Start Date")
    col_name  = pick("Activity Name", "Title", "Name")
    col_dist  = pick("Distance")
    col_gain  = pick("Elevation Gain", "Elev Gain", "Total Ascent")
    col_loss  = pick("Elevation Loss", "Elev Loss", "Total Descent")
    col_time  = pick("Moving Time", "Elapsed Time", "Time")

    out = []
    for _, r in df.iterrows():
        d = parse_date_any(r.get(col_date)) if col_date else None
        # Strava Distance typiquement en mètres
        dist_m = to_float(r.get(col_dist)) if col_dist else None
        km = dist_m/1000.0 if dist_m is not None else None

        dplus = to_int(r.get(col_gain)) if col_gain else None
        dmoins = to_int(r.get(col_loss)) if col_loss else None
        dur = hhmmss_to_seconds(r.get(col_time)) if col_time else None
        titre = str(r.get(col_name)).strip() if col_name and not pd.isna(r.get(col_name)) else None

        out.append({
            "date": d,
            "distance_km": km,
            "d_plus_m": dplus,
            "d_moins_m": dmoins,
            "duree_sec": dur,
            "titre": titre,
            "source": "strava",
            "raw": dict(r)
        })
    return pd.DataFrame(out, columns=COMMON_COLUMNS)

# =========================
# UI : deux onglets
# =========================
tab_garmin, tab_strava = st.tabs(["🟧 Garmin", "🟥 Strava"])

def process_import(df_common):
    # Nettoyage des lignes vides de date ou km
    df_common = df_common.dropna(subset=["date", "distance_km"]).reset_index(drop=True)

    # Pour chaque ligne importée, on cherche les potentiels doublons dans la DB
    decisions = []
    for idx, row in df_common.iterrows():
        day = row["date"]
        existing_rows = load_db_rows_for_date(day)

        # Chercher correspondance “similar”
        similar = None
        for ex in existing_rows:
            if is_similar(ex, row):
                similar = ex
                break

        st.markdown("---")
        st.subheader(f"📅 {day} — {row['distance_km']:.2f} km | D+ {row.get('d_plus_m') or 0} m | D- {row.get('d_moins_m') or 0} m | source: {row['source']}")

        if similar:
            st.info("🔁 **Doublon potentiel détecté** : comparez la ligne DB (haut) et la proposition importée (bas).")
            # Affichage DB en haut
            with st.container(border=True):
                st.markdown("**Dans la base (existant)**")
                c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
                c1.write(f"**Date**\n{similar.get('date')}")
                c2.write(f"**Km**\n{similar.get('distance_km')}")
                c3.write(f"**D+**\n{similar.get('d_plus_m')}")
                c4.write(f"**D-**\n{similar.get('d_moins_m')}")
                duree_txt = f"{int(similar.get('duree_sec') or 0)//60} min" if similar.get('duree_sec') else "-"
                c5.write(f"**Durée**\n{duree_txt}")
                st.write(f"**Titre** : {similar.get('titre') or '-'}")

            # Affichage IMPORT en dessous
            with st.container(border=True):
                st.markdown("**Proposé (import)**")
                c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
                c1.write(f"**Date**\n{row['date']}")
                c2.write(f"**Km**\n{row['distance_km']}")
                c3.write(f"**D+**\n{row['d_plus_m']}")
                c4.write(f"**D-**\n{row['d_moins_m']}")
                duree_txt2 = f"{int(row['duree_sec'])//60} min" if row["duree_sec"] else "-"
                c5.write(f"**Durée**\n{duree_txt2}")
                st.write(f"**Titre** : {row['titre'] or '-'}")

            choice = st.radio(
                "Que faire ?",
                ["Ignorer", "Insérer (quand même)", "Remplacer (écraser la DB)", "Combiner (compléter l'existant)"],
                key=f"choice_{idx}",
                horizontal=True
            )
            decisions.append((row, similar, choice))
        else:
            st.success("🆕 **Aucun doublon détecté** — vous pouvez insérer.")
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
                c1.write(f"**Date**\n{row['date']}")
                c2.write(f"**Km**\n{row['distance_km']}")
                c3.write(f"**D+**\n{row['d_plus_m']}")
                c4.write(f"**D-**\n{row['d_moins_m']}")
                duree_txt2 = f"{int(row['duree_sec'])//60} min" if row["duree_sec"] else "-"
                c5.write(f"**Durée**\n{duree_txt2}")
                st.write(f"**Titre** : {row['titre'] or '-'}")

            choice = st.radio(
                "Que faire ?",
                ["Ignorer", "Insérer (nouvelle ligne)"],
                key=f"choice_{idx}",
                horizontal=True
            )
            decisions.append((row, None, "Insérer (nouvelle ligne)" if "Insérer" in choice else "Ignorer"))

    # Bouton d’application
    if decisions:
        if st.button("✅ Appliquer les décisions"):
            n_ins, n_rep, n_comb, n_skip = 0, 0, 0, 0
            for row, similar, choice in decisions:
                if choice.startswith("Ignorer"):
                    n_skip += 1
                    continue
                if similar is None and choice.startswith("Insérer"):
                    payload = {k: row[k] for k in COMMON_COLUMNS if k != "raw"}
                    payload["user_id"] = user["id"]
                    sb.table(TABLE).insert(payload).execute()
                    n_ins += 1
                elif similar is not None and choice.startswith("Insérer (quand même)"):
                    payload = {k: row[k] for k in COMMON_COLUMNS if k != "raw"}
                    payload["user_id"] = user["id"]
                    sb.table(TABLE).insert(payload).execute()
                    n_ins += 1
                elif similar is not None and choice.startswith("Remplacer"):
                    # Remplacer toute la ligne existante par l'import
                    payload = {k: row[k] for k in COMMON_COLUMNS if k != "raw"}
                    payload["user_id"] = user["id"]
                    # Suppose que la PK est 'id'
                    sb.table(TABLE).update(payload).eq("id", similar["id"]).execute()
                    n_rep += 1
                elif similar is not None and choice.startswith("Combiner"):
                    merged = combine_rows(similar, row)
                    merged["user_id"] = user["id"]
                    sb.table(TABLE).update(merged).eq("id", similar["id"]).execute()
                    n_comb += 1
            st.success(f"Terminé : {n_ins} inséré(s), {n_rep} remplacé(s), {n_comb} combiné(s), {n_skip} ignoré(s).")
        else:
            st.caption("Sélectionnez vos choix pour chaque ligne puis cliquez sur **Appliquer les décisions**.")

# ------------- Onglet Garmin -------------
with tab_garmin:
    st.subheader("Importer depuis Garmin (CSV d’activités)")
    garmin_file = st.file_uploader("Déposez le CSV Garmin", type=["csv"], key="garmin_csv")
    if garmin_file is not None:
        try:
            df_garmin_raw = pd.read_csv(garmin_file)
        except UnicodeDecodeError:
            df_garmin_raw = pd.read_csv(garmin_file, encoding="latin1")
        st.write("Aperçu brut (Garmin):", df_garmin_raw.head())
        df_common = parse_garmin_csv(df_garmin_raw)
        if not df_common.empty:
            st.write("Préparation (schéma commun):", df_common.head())
            process_import(df_common)
        else:
            st.warning("Aucune ligne exploitable détectée pour Garmin.")

# ------------- Onglet Strava -------------
with tab_strava:
    st.subheader("Importer depuis Strava (CSV global 'activities.csv')")
    strava_file = st.file_uploader("Déposez le CSV Strava", type=["csv"], key="strava_csv")
    if strava_file is not None:
        try:
            df_strava_raw = pd.read_csv(strava_file)
        except UnicodeDecodeError:
            df_strava_raw = pd.read_csv(strava_file, encoding="latin1")
        st.write("Aperçu brut (Strava):", df_strava_raw.head())
        df_common = parse_strava_csv(df_strava_raw)
        if not df_common.empty:
            st.write("Préparation (schéma commun, uniquement *run*):", df_common.head())
            process_import(df_common)
        else:
            st.warning("Aucune ligne exploitable détectée pour Strava (ou aucune activité 'run').")

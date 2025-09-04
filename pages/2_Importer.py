import streamlit as st
import pandas as pd
import io, re
from datetime import datetime
from zoneinfo import ZoneInfo

from supa import get_client
from utils import require_login

st.set_page_config(page_title="Importer — Garmin → journal", layout="wide")

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state.get("user")
if not user: st.stop()

st.title("📥 Importer mes activités Garmin → journal")

st.markdown("""
Cette page importe un CSV **Garmin Connect (FR)** et remplit les colonnes *séance course* de ta table **journal** :
- `date` (obligatoire), `seance_course`, `distance_course_km`, `dplus_course_m`, `dmoins_course_m`,
- `temps_course_min`, `allure_course_min_km`,
- `fc_moyenne_course`, `ppm_course`, `calories_course`,
- (optionnel) `temperature_c`, `force_vent_course_kmh`, `direction_vent`, `meteo` si dispo (pas dans ton CSV actuel).
""")

# ---------- Helpers
def _guess_sep(sample: bytes) -> str:
    head = sample.decode(errors="ignore")
    return ';' if head.count(';') > head.count(',') else ','

def _to_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip().replace("’","").replace("'","")
    s = s.replace(",", ".")  # virgule FR → point
    s = re.sub(r"[^\d\.\-eE]", "", s)  # vire unités
    try: return float(s)
    except: return None

def _to_int_nonneg(x):
    v = _to_float(x)
    if v is None: return None
    try:
        iv = int(round(v))
        return iv if iv >= 0 else None
    except:
        return None

def _to_minutes_hms(x):
    """'hh:mm:ss' ou 'mm:ss' → minutes entières (arrondies). Si nombre brut: >120=secondes sinon=minutes."""
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip()
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", s):
        h,m,s2 = s.split(":"); return int(round((int(h)*3600+int(m)*60+int(s2))/60))
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        m,s2 = s.split(":");  return int(round((int(m)*60+int(s2))/60))
    v = _to_float(s)
    if v is None: return None
    return int(round(v/60)) if v>120 else int(round(v))

def _pace_to_min_per_km(x):
    """'mm:ss' (avec/sans 'min/km') → minutes décimales/km (ex: 5.53 pour 5:32)."""
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).lower().replace("min/km","").replace("/km","").strip()
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        m, s2 = s.split(":"); return round(int(m) + int(s2)/60, 2)
    v = _to_float(s); return round(v, 2) if v is not None else None

def _parse_date_only(x, tz="Europe/Zurich"):
    """'Date' Garmin FR peut porter date (évent. heure). On renvoie 'YYYY-MM-DD'."""
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip()
    fmts = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.date().isoformat()
        except:
            pass
    try:
        dt = pd.to_datetime(s, utc=False, errors="raise", dayfirst=True)
        return (dt.date().isoformat())
    except:
        return None

# ---------- Upload
uploaded = st.file_uploader("Glisser-déposer le CSV Garmin (FR) ici", type=["csv"])
if not uploaded:
    st.info("Dans Garmin Connect (FR) : **Rapports → Toutes les activités → Exporter CSV**, puis dépose-le ici.")
    st.stop()

sample = uploaded.getvalue()[:65536]
sep = _guess_sep(sample)

try:
    df = pd.read_csv(io.BytesIO(uploaded.getvalue()), sep=sep, engine="python", encoding="utf-8", dtype=str)
except Exception:
    df = pd.read_csv(io.BytesIO(uploaded.getvalue()), sep=sep, engine="python", encoding="latin-1", dtype=str)

st.subheader("Aperçu")
st.dataframe(df.head(30), use_container_width=True)

# ---------- Mapping (prérempli pour colonnes FR de ton CSV)
st.subheader("Mapping des colonnes")

cols = [""] + list(df.columns)
def idx(colname):  # renvoie l'index de 'colname' si présent, sinon 0
    try: return cols.index(colname)
    except ValueError: return 0

col_start    = st.selectbox("Date/Heure de début → `date` (obligatoire)", cols, index=idx("Date"))
col_type     = st.selectbox("Type d'activité → `seance_course`", cols, index=idx("Type d'activité"))
col_distance = st.selectbox("Distance (km) → `distance_course_km`", cols, index=idx("Distance"))
col_dplus    = st.selectbox("Ascension totale (m) → `dplus_course_m`", cols, index=idx("Ascension totale"))
col_dmoins   = st.selectbox("Descente totale (m) → `dmoins_course_m`", cols, index=idx("Descente totale"))

# Durée: tu as 'Durée', 'Temps écoulé' et 'Temps de déplacement' → choisis celui que tu préfères
col_duration = st.selectbox("Durée → `temps_course_min`", cols, index=idx("Temps écoulé"))

col_pace     = st.selectbox("Allure moyenne (mm:ss) → `allure_course_min_km`", cols, index=idx("Allure moyenne"))
col_hr       = st.selectbox("Fréquence cardiaque moyenne (bpm) → `fc_moyenne_course`", cols, index=idx("Fréquence cardiaque moyenne"))
col_cadence  = st.selectbox("Cadence de course moyenne (ppm) → `ppm_course`", cols, index=idx("Cadence de course moyenne"))
col_calories = st.selectbox("Calories → `calories_course`", cols, index=idx("Calories"))

if not col_start:
    st.error("La colonne **Date** est obligatoire pour alimenter `date`.")
    st.stop()

dry_run  = st.checkbox("Dry-run (ne rien écrire en base)", value=True)
dup_check = st.checkbox("Éviter les doublons (date + distance ±0.1 km + durée ±2 min)", value=True)

# ---------- Transformation
def rows_from_df(df: pd.DataFrame):
    rows, errors = [], []
    for i, r in df.iterrows():
        try:
            dte = _parse_date_only(r[col_start])
            if not dte: raise ValueError("date illisible")

            distance_km = _to_float(r[col_distance]) if col_distance else None
            duree_min   = _to_minutes_hms(r[col_duration]) if col_duration else None
            allure_min  = _pace_to_min_per_km(r[col_pace]) if col_pace else None

            row = {
                "user_id": user["id"],      # RLS ok
                "date": dte,                # obligatoire
                "seance_course": str(r[col_type]).strip() if col_type else None,

                "distance_course_km": distance_km,
                "dplus_course_m": _to_int_nonneg(r[col_dplus]) if col_dplus else None,
                "dmoins_course_m": _to_int_nonneg(r[col_dmoins]) if col_dmoins else None,
                "temps_course_min": duree_min,
                "allure_course_min_km": allure_min,

                "fc_moyenne_course": _to_int_nonneg(r[col_hr]) if col_hr else None,
                "ppm_course": _to_int_nonneg(r[col_cadence]) if col_cadence else None,
                "calories_course": _to_int_nonneg(r[col_calories]) if col_calories else None,
            }

            # bornes logiques (>=0) — température non gérée ici
            for key in ["distance_course_km","dplus_course_m","dmoins_course_m","temps_course_min",
                        "allure_course_min_km","fc_moyenne_course","ppm_course","calories_course"]:
                v = row.get(key)
                if isinstance(v, (int, float)) and v is not None and v < 0:
                    row[key] = None

            rows.append(row)
        except Exception as e:
            errors.append({"row_index": i, "error": str(e)})
    return rows, errors

rows, errors = rows_from_df(df)

c1, c2 = st.columns(2)
with c1: st.metric("Lignes prêtes", len(rows))
with c2: st.metric("Lignes en erreur", len(errors))
if errors:
    st.download_button("📄 Télécharger erreurs (CSV)",
                       pd.DataFrame(errors).to_csv(index=False).encode("utf-8"),
                       file_name="garmin_import_erreurs.csv")

st.divider()

# ---------- Déduplication app (date + distance ±0.1 + durée ±2)
def fetch_existing_fp(dates):
    if not dates: return set()
    fp = set(); step = 100
    for i in range(0, len(dates), step):
        subset = dates[i:i+step]
        q = (sb.table("journal")
               .select("date, distance_course_km, temps_course_min")
               .eq("user_id", user["id"])
               .in_("date", subset)
               .execute())
        for r in (q.data or []):
            d = r.get("date")
            dist = float(r["distance_course_km"]) if r.get("distance_course_km") is not None else None
            dur = int(r["temps_course_min"]) if r.get("temps_course_min") is not None else None
            fp.add((d, dist, dur))
    return fp

def q_dist(v): return None if v is None else round(v/0.1)*0.1
def q_dur(v):  return None if v is None else int(round(v/2)*2)

def normalize_fp(s):
    out=set()
    for (d,dist,dur) in s: out.add((d, q_dist(dist), q_dur(dur)))
    return out

filtered, dups = rows, []
if dup_check:
    dates = sorted({r["date"] for r in rows if r.get("date")})
    existing = normalize_fp(fetch_existing_fp(dates))
    keep, dropped = [], []
    for r in rows:
        key = (r["date"], q_dist(r.get("distance_course_km")), q_dur(r.get("temps_course_min")))
        if key in existing: dropped.append(r)
        else: keep.append(r)
    filtered, dups = keep, dropped

colA, colB = st.columns(2)
with colA: st.write(f"🧹 Lignes après filtre doublons : **{len(filtered)}**")
with colB:
    if dup_check: st.write(f"🔁 Doublons détectés (ignorés) : **{len(dups)}**")
if dups:
    st.download_button("📄 Exporter les doublons", pd.DataFrame(dups).to_csv(index=False).encode("utf-8"),
                       file_name="doublons_detectes.csv")

# ---------- Insertion
st.subheader("Insertion dans `journal`")
if st.button("✅ Valider l'import"):
    if dry_run:
        st.warning("Dry-run activé : rien n'a été écrit. Décoche Dry-run pour insérer.")
        st.stop()
    if not filtered:
        st.info("Aucune ligne à insérer.")
        st.stop()
    inserted = 0; batch_size = 500
    try:
        for i in range(0, len(filtered), batch_size):
            sb.table("journal").insert(filtered[i:i+batch_size]).execute()
            inserted += len(filtered[i:i+batch_size])
        st.success(f"Terminé : {inserted} lignes insérées dans `journal`.")
    except Exception as e:
        st.error(f"Erreur pendant l'insertion : {e}")
        if inserted:
            st.warning(f"{inserted} lignes ont été insérées avant l'erreur.")


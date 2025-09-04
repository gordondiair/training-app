import streamlit as st
import pandas as pd
import io, re
from datetime import datetime
from zoneinfo import ZoneInfo

from supa import get_client
from utils import require_login

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="Importer — Garmin → journal", layout="wide")

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state.get("user")
if not user: st.stop()

st.title("📥 Importer mes activités Garmin → journal")

st.markdown("""
Cette page importe un CSV **Garmin Connect (FR)** vers ta table **journal** (colonnes *séance course*).
- Doublon = **même date** ET **distance proche** ET **D+ proche** ET **D- proche**.
- Tu confirmes **un par un** les potentiels doublons détectés par rapport à ta base.
""")

# -------------------- HELPERS --------------------
def _guess_sep(sample: bytes) -> str:
    head = sample.decode(errors="ignore")
    return ';' if head.count(';') > head.count(',') else ','

def _to_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip().replace("’","").replace("'","").replace(",", ".")
    s = re.sub(r"[^\d\.\-eE]", "", s)
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
    """'hh:mm:ss' ou 'mm:ss' → minutes entières. Nombre brut: >120 = secondes sinon minutes."""
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
    """'Date' Garmin FR → YYYY-MM-DD"""
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip()
    fmts = ("%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.date().isoformat()
        except: pass
    try:
        dt = pd.to_datetime(s, utc=False, errors="raise", dayfirst=True)
        return dt.date().isoformat()
    except:
        return None

# -------------------- PARAMÈTRES DÉDUP --------------------
with st.sidebar:
    st.header("Tolérances doublons")
    tol_km = st.number_input("Tolérance distance (km)", min_value=0.0, max_value=2.0, value=0.10, step=0.05, format="%.2f")
    tol_m  = st.number_input("Tolérance D+ / D- (m)",   min_value=0,   max_value=500, value=15, step=5)

# -------------------- UPLOAD --------------------
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

st.subheader("Aperçu du fichier")
st.dataframe(df.head(30), use_container_width=True)

# -------------------- MAPPING (prérempli pour Garmin FR) --------------------
st.subheader("Mapping des colonnes")

cols = [""] + list(df.columns)
def idx(colname):
    try: return cols.index(colname)
    except ValueError: return 0

col_date     = st.selectbox("Date → `date` (obligatoire)", cols, index=idx("Date"))
col_type     = st.selectbox("Type d'activité → `seance_course`", cols, index=idx("Type d'activité"))
col_distance = st.selectbox("Distance (km) → `distance_course_km`", cols, index=idx("Distance"))
col_dplus    = st.selectbox("Ascension totale (m) → `dplus_course_m`", cols, index=idx("Ascension totale"))
col_dmoins   = st.selectbox("Descente totale (m) → `dmoins_course_m`", cols, index=idx("Descente totale"))
col_duration = st.selectbox("Durée → `temps_course_min`", cols, index=idx("Temps écoulé"))
col_pace     = st.selectbox("Allure moyenne (mm:ss) → `allure_course_min_km`", cols, index=idx("Allure moyenne"))
col_hr       = st.selectbox("Fréquence cardiaque moyenne (bpm) → `fc_moyenne_course`", cols, index=idx("Fréquence cardiaque moyenne"))
col_cadence  = st.selectbox("Cadence de course moyenne (ppm) → `ppm_course`", cols, index=idx("Cadence de course moyenne"))
col_calories = st.selectbox("Calories → `calories_course`", cols, index=idx("Calories"))

if not col_date:
    st.error("La colonne **Date** est obligatoire.")
    st.stop()

dry_run = st.checkbox("Dry-run (ne rien écrire en base)", value=True)

# -------------------- TRANSFORMATION --------------------
def build_rows(df: pd.DataFrame):
    rows, errors = [], []
    for i, r in df.iterrows():
        try:
            dte = _parse_date_only(r[col_date])
            if not dte: raise ValueError("date illisible")

            distance_km = _to_float(r[col_distance]) if col_distance else None
            duree_min   = _to_minutes_hms(r[col_duration]) if col_duration else None
            allure_min  = _pace_to_min_per_km(r[col_pace]) if col_pace else None
            dplus_m     = _to_int_nonneg(r[col_dplus]) if col_dplus else None
            dmoins_m    = _to_int_nonneg(r[col_dmoins]) if col_dmoins else None

            row = {
                "user_id": user["id"],
                "date": dte,
                "seance_course": str(r[col_type]).strip() if col_type else None,

                "distance_course_km": distance_km,
                "dplus_course_m": dplus_m,
                "dmoins_course_m": dmoins_m,
                "temps_course_min": duree_min,
                "allure_course_min_km": allure_min,

                "fc_moyenne_course": _to_int_nonneg(r[col_hr]) if col_hr else None,
                "ppm_course": _to_int_nonneg(r[col_cadence]) if col_cadence else None,
                "calories_course": _to_int_nonneg(r[col_calories]) if col_calories else None,
            }

            # Respect des checks >=0 (température non utilisée ici)
            for key in ["distance_course_km","dplus_course_m","dmoins_course_m",
                        "temps_course_min","allure_course_min_km",
                        "fc_moyenne_course","ppm_course","calories_course"]:
                v = row.get(key)
                if isinstance(v, (int, float)) and v is not None and v < 0:
                    row[key] = None

            rows.append(row)
        except Exception as e:
            errors.append({"row_index": i, "error": str(e)})
    return rows, errors

rows_in, errors = build_rows(df)

c1, c2 = st.columns(2)
with c1: st.metric("Lignes prêtes (après parsing)", len(rows_in))
with c2: st.metric("Lignes en erreur", len(errors))
if errors:
    st.download_button("📄 Télécharger erreurs (CSV)",
                       pd.DataFrame(errors).to_csv(index=False).encode("utf-8"),
                       file_name="garmin_import_erreurs.csv")

if not rows_in:
    st.stop()

# -------------------- RÉCUP DB pour les mêmes dates --------------------
dates_needed = sorted({r["date"] for r in rows_in if r.get("date")})
existing_by_date = {}
step = 100
for i in range(0, len(dates_needed), step):
    subset = dates_needed[i:i+step]
    q = (sb.table("journal")
            .select("id, created_at, date, distance_course_km, dplus_course_m, dmoins_course_m, temps_course_min, allure_course_min_km, fc_moyenne_course, ppm_course, calories_course, seance_course")
            .eq("user_id", user["id"])
            .in_("date", subset)
            .execute())
    for r in (q.data or []):
        d = r["date"]
        existing_by_date.setdefault(d, []).append(r)

# -------------------- DÉTECTION + VALIDATION MANUELLE des DOUBLONS --------------------
st.subheader("Vérification des potentiels doublons (vs. base)")

# On crée une clé stable par ligne d'import pour les widgets
def _import_key(idx, row):
    return f"import_{idx}_{row['date']}_{row.get('distance_course_km')}_{row.get('dplus_course_m')}_{row.get('dmoins_course_m')}"

potentiels = []   # éléments: {row_in, matches_db, decide_key}
to_insert = []    # sera rempli après décisions utilisateur

for idx, row in enumerate(rows_in):
    same_day = existing_by_date.get(row["date"], [])
    # Matches: abs distance <= tol_km ET abs d+ <= tol_m ET abs d- <= tol_m
    matches = []
    for ex in same_day:
        dist_db = ex.get("distance_course_km")
        dplus_db = ex.get("dplus_course_m")
        dmoins_db = ex.get("dmoins_course_m")
        # Convertir proprement
        try: dist_db = float(dist_db) if dist_db is not None else None
        except: dist_db = None
        try: dplus_db = int(dplus_db) if dplus_db is not None else None
        except: dplus_db = None
        try: dmoins_db = int(dmoins_db) if dmoins_db is not None else None
        except: dmoins_db = None

        ok = True
        # Distance doit exister des deux côtés
        if row.get("distance_course_km") is None or dist_db is None: ok = False
        if ok and abs(row["distance_course_km"] - dist_db) > tol_km: ok = False
        # d+ et d- doivent exister des deux côtés
        if ok and (row.get("dplus_course_m") is None or dplus_db is None): ok = False
        if ok and abs(row["dplus_course_m"] - dplus_db) > tol_m: ok = False
        if ok and (row.get("dmoins_course_m") is None or dmoins_db is None): ok = False
        if ok and abs(row["dmoins_course_m"] - dmoins_db) > tol_m: ok = False

        if ok:
            # on annote l'écart pour l'affichage
            matches.append({
                "id": ex["id"],
                "created_at": ex["created_at"],
                "date": ex["date"],
                "distance_course_km": dist_db,
                "dplus_course_m": dplus_db,
                "dmoins_course_m": dmoins_db,
                "temps_course_min": ex.get("temps_course_min"),
                "seance_course": ex.get("seance_course"),
                "diff_km": round(row["distance_course_km"] - dist_db, 3) if row.get("distance_course_km") is not None and dist_db is not None else None,
                "diff_dplus": (row["dplus_course_m"] - dplus_db) if row.get("dplus_course_m") is not None and dplus_db is not None else None,
                "diff_dmoins": (row["dmoins_course_m"] - dmoins_db) if row.get("dmoins_course_m") is not None and dmoins_db is not None else None,
            })

    if matches:
        potentiels.append({"idx": idx, "row_in": row, "matches_db": matches, "decide_key": _import_key(idx, row)})
    else:
        to_insert.append(row)  # aucun match → insertion d'office

if potentiels:
    st.warning(f"{len(potentiels)} potentiel(s) doublon(s) trouvé(s). Valide-les un par un ci-dessous.")
    for bloc in potentiels:
        r = bloc["row_in"]
        st.markdown("---")
        st.markdown(f"**Activité importée (DATE {r['date']})** — Dist: {r.get('distance_course_km')} km | D+: {r.get('dplus_course_m')} m | D-: {r.get('dmoins_course_m')} m | Durée: {r.get('temps_course_min')} min | Type: {r.get('seance_course')}")
        st.caption(f"Tolérances actuelles: ±{tol_km:.2f} km, ±{tol_m} m")

        dfm = pd.DataFrame(bloc["matches_db"])
        st.dataframe(dfm, use_container_width=True)

        choice = st.radio(
            "S'agit-il d'un doublon ? (si OUI → n'insère pas cette ligne importée)",
            options=["Oui, c'est un doublon (ignorer)", "Non, pas un doublon (insérer)"],
            index=0,
            key=bloc["decide_key"]
        )
        bloc["decision"] = choice

    # Appliquer décisions
    decided_insert = [b["row_in"] for b in potentiels if b.get("decision") == "Non, pas un doublon (insérer)"]
    to_insert.extend(decided_insert)

else:
    st.success("Aucun potentiel doublon détecté avec ces tolérances.")

st.info(f"✅ Lignes prêtes à l'insertion (après décisions): **{len(to_insert)}**")

# -------------------- INSERTION --------------------
st.subheader("Insertion dans `journal`")

if st.button("✅ Valider l'import"):
    if dry_run:
        st.warning("Dry-run activé : rien n'a été écrit. Décoche Dry-run pour insérer.")
        st.stop()
    if not to_insert:
        st.info("Aucune ligne à insérer.")
        st.stop()
    inserted = 0; batch_size = 500
    try:
        for i in range(0, len(to_insert), batch_size):
            sb.table("journal").insert(to_insert[i:i+batch_size]).execute()
            inserted += len(to_insert[i:i+batch_size])
        st.success(f"Terminé : {inserted} lignes insérées dans `journal`.")
    except Exception as e:
        st.error(f"Erreur pendant l'insertion : {e}")

import streamlit as st
import pandas as pd
import io, re
from datetime import datetime
from zoneinfo import ZoneInfo

from supa import get_client
from utils import require_login

# =============== PAGE SETUP ===============
st.set_page_config(page_title="Importer — Garmin → journal", layout="wide")

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
user = st.session_state.get("user")
if not user: st.stop()

st.title("📥 Importer mes activités Garmin → journal")

st.markdown("""
Cette page importe un CSV **Garmin Connect (FR)** vers ta table **journal** (colonnes *séance course*).

**Doublon =** même **date** **ET** distance proche (± tolérance) **ET** D+ proche (± tolérance) **ET** D− proche (± tolérance).

Pour chaque **potentiel doublon**, on affiche **l'existant en base (au-dessus)** puis **la ligne importée (en dessous)**, et tu choisis :
- **Oui — doublon** → on ignore l'import
- **Non — pas doublon** → on **insère** l'import
- **Combiner** → on **complète seulement les champs vides** de l’existant avec les infos de l’import
""")

# =============== HELPERS ===============
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
    except: return None

def _to_minutes_hms(x):
    """'hh:mm:ss' ou 'mm:ss' → minutes entières; nombre brut: >120 = secondes sinon minutes."""
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

def _parse_date_only(x):
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
    except: return None

# =============== TOLÉRANCES ===============
with st.sidebar:
    st.header("Tolérances (détection de doublons)")
    tol_km = st.number_input("Distance (± km)", min_value=0.0, max_value=2.0, value=0.10, step=0.05, format="%.2f")
    tol_m  = st.number_input("D+ / D− (± m)",   min_value=0,   max_value=500, value=15,   step=5)
    st.caption("Comparaisons effectuées uniquement si les deux côtés ont une valeur (non NULL).")

# =============== UPLOAD ===============
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

# =============== MAPPING (FR) ===============
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

# Champs du journal gérés ici (pour la combinaison)
FIELDS = [
    "seance_course",
    "distance_course_km",
    "dplus_course_m",
    "dmoins_course_m",
    "temps_course_min",
    "allure_course_min_km",
    "fc_moyenne_course",
    "ppm_course",
    "calories_course",
    "temperature_c",
    "force_vent_course_kmh",
    "direction_vent",
    "meteo",
]

# =============== TRANSFORMATION ===============
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

                # par défaut None (ton CSV actuel ne les a pas)
                "temperature_c": None,
                "force_vent_course_kmh": None,
                "direction_vent": None,
                "meteo": None,
            }

            # respect des bornes (>=0) — température peut être < 0
            for key in ["distance_course_km","dplus_course_m","dmoins_course_m",
                        "temps_course_min","allure_course_min_km",
                        "fc_moyenne_course","ppm_course","calories_course",
                        "force_vent_course_kmh"]:
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

# =============== RÉCUP DB (mêmes dates) ===============
dates_needed = sorted({r["date"] for r in rows_in if r.get("date")})
existing_by_date = {}
step = 100
for i in range(0, len(dates_needed), step):
    subset = dates_needed[i:i+step]
    q = (sb.table("journal")
            .select("id, created_at, date, " + ",".join(FIELDS))
            .eq("user_id", user["id"])
            .in_("date", subset)
            .execute())
    for r in (q.data or []):
        existing_by_date.setdefault(r["date"], []).append(r)

# =============== DÉTECTION + DÉCISION (VERTICALE) ===============
st.subheader("Potentiels doublons : décision **pair-à-pair** (EXISTANT au-dessus / IMPORT en dessous)")

def _pair_key(import_idx, import_row, existing_id):
    return f"dupdec_{import_idx}_{existing_id}_{import_row['date']}"

pairs = []        # (idx, import_row, existing_row, key)
to_insert = []    # import rows to insert
updates = {}      # existing_id -> patch (compléter sans écraser)

for idx, imp in enumerate(rows_in):
    same_day = existing_by_date.get(imp["date"], [])
    matched_any = False

    for ex in same_day:
        # valeurs DB pour comparer
        try: dist_db = float(ex.get("distance_course_km")) if ex.get("distance_course_km") is not None else None
        except: dist_db = None
        try: dplus_db = int(ex.get("dplus_course_m")) if ex.get("dplus_course_m") is not None else None
        except: dplus_db = None
        try: dmoins_db = int(ex.get("dmoins_course_m")) if ex.get("dmoins_course_m") is not None else None
        except: dmoins_db = None

        ok = True
        if imp.get("distance_course_km") is None or dist_db is None: ok = False
        if ok and abs(imp["distance_course_km"] - dist_db) > tol_km: ok = False
        if ok and (imp.get("dplus_course_m") is None or dplus_db is None): ok = False
        if ok and abs(imp["dplus_course_m"] - dplus_db) > tol_m: ok = False
        if ok and (imp.get("dmoins_course_m") is None or dmoins_db is None): ok = False
        if ok and abs(imp["dmoins_course_m"] - dmoins_db) > tol_m: ok = False

        if ok:
            matched_any = True
            pairs.append((idx, imp, ex, _pair_key(idx, imp, ex["id"])))

    if not matched_any:
        to_insert.append(imp)

chosen_insert_idx = set()  # évite double insert de la même ligne import si plusieurs paires

if pairs:
    st.warning(f"{len(pairs)} paire(s) à valider. Choisis une action pour chacune :")
    for (idx, imp, ex, key) in pairs:
        st.markdown("---")
        st.markdown(f"### Date {imp['date']} — Candidat doublon")

        # EXISTANT — AU-DESSUS
        st.markdown("**EXISTANT (en base)**")
        st.table(pd.DataFrame([{
            "id": ex["id"],
            "created_at": ex.get("created_at"),
            "date": ex.get("date"),
            "type": ex.get("seance_course"),
            "distance_km": ex.get("distance_course_km"),
            "dplus_m": ex.get("dplus_course_m"),
            "dmoins_m": ex.get("dmoins_course_m"),
            "durée_min": ex.get("temps_course_min"),
            "allure_min/km": ex.get("allure_course_min_km"),
            "FC_moy": ex.get("fc_moyenne_course"),
            "cadence_ppm": ex.get("ppm_course"),
            "calories": ex.get("calories_course"),
            "temperature_c": ex.get("temperature_c"),
            "vent_kmh": ex.get("force_vent_course_kmh"),
            "direction_vent": ex.get("direction_vent"),
            "meteo": ex.get("meteo"),
        }]))

        # IMPORT — EN DESSOUS
        st.markdown("**IMPORT (fichier)**")
        st.table(pd.DataFrame([{
            "date": imp.get("date"),
            "type": imp.get("seance_course"),
            "distance_km": imp.get("distance_course_km"),
            "dplus_m": imp.get("dplus_course_m"),
            "dmoins_m": imp.get("dmoins_course_m"),
            "durée_min": imp.get("temps_course_min"),
            "allure_min/km": imp.get("allure_course_min_km"),
            "FC_moy": imp.get("fc_moyenne_course"),
            "cadence_ppm": imp.get("ppm_course"),
            "calories": imp.get("calories_course"),
            "temperature_c": imp.get("temperature_c"),
            "vent_kmh": imp.get("force_vent_course_kmh"),
            "direction_vent": imp.get("direction_vent"),
            "meteo": imp.get("meteo"),
        }]))

        choice = st.radio(
            "Action à appliquer :",
            options=[
                "Oui — c'est un doublon (IGNORER l'import)",
                "Non — pas un doublon (INSÉRER l'import)",
                "🔗 Combiner (compléter l’existant avec les infos manquantes de l’import)"
            ],
            index=0,
            key=key
        )

        # Si Combiner → construire un patch "remplir les trous"
        if choice == "🔗 Combiner (compléter l’existant avec les infos manquantes de l’import)":
            patch = {}
            for f in FIELDS:
                cur = ex.get(f, None)
                new = imp.get(f, None)
                if (cur is None or cur == "") and (new is not None and new != ""):
                    patch[f] = new
            if patch:
                st.info(f"Champs complétés (id {ex['id']}) : {', '.join(patch.keys())}")
                # fusion si plusieurs imports ciblent le même existant
                if ex["id"] not in updates:
                    updates[ex["id"]] = patch
                else:
                    for k,v in patch.items():
                        if k not in updates[ex["id"]]:
                            updates[ex["id"]][k] = v
            else:
                st.warning("Aucun champ à compléter (l’existant est déjà rempli pour ces colonnes).")

    # Appliquer les décisions “INSÉRER”
    for (idx, imp, ex, key) in pairs:
        if st.session_state.get(key) == "Non — pas un doublon (INSÉRER l'import)" and idx not in chosen_insert_idx:
            to_insert.append(imp)
            chosen_insert_idx.add(idx)
else:
    st.success("Aucun potentiel doublon détecté avec ces tolérances.")

# =============== RÉCAP ===============
st.info(f"✅ Lignes prêtes à l'insertion : **{len(to_insert)}**")
st.info(f"🧩 Lignes existantes à compléter (patchs) : **{len(updates)}**")

if updates:
    with st.expander("Voir le détail des mises à jour prévues"):
        preview_rows = [{"id": rid, "maj_champs": ", ".join(patch.keys())} for rid, patch in updates.items()]
        st.table(pd.DataFrame(preview_rows))

# =============== ÉCRITURE DB ===============
st.subheader("Écrire en base `journal`")

if st.button("✅ Exécuter (insertions + mises à jour)"):
    if dry_run:
        st.warning("Dry-run activé : rien n'a été écrit. Décoche Dry-run pour exécuter.")
        st.stop()

    inserted = 0
    updated = 0
    try:
        # Insertions
        if to_insert:
            batch_size = 500
            for i in range(0, len(to_insert), batch_size):
                sb.table("journal").insert(to_insert[i:i+batch_size]).execute()
                inserted += len(to_insert[i:i+batch_size])

        # Mises à jour (complétion)
        for rid, patch in updates.items():
            if patch:
                sb.table("journal").update(patch).eq("id", rid).eq("user_id", user["id"]).execute()
                updated += 1

        st.success(f"Terminé : {inserted} ligne(s) insérée(s), {updated} ligne(s) mise(s) à jour.")
    except Exception as e:
        st.error(f"Erreur pendant l'écriture : {e}")

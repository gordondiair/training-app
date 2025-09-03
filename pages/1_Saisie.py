import streamlit as st
from datetime import date
from supa import get_client

st.title("🏠 Saisie — Journal")

# ---------- Styles globaux : bouton vert + checkbox verte
st.markdown("""
<style>
/* Tous les st.button en vert (fond) + texte blanc */
div.stButton > button {
  background-color:#16a34a !important; /* green-600 */
  color:white !important;
  border:1px solid #16a34a !important;
}
div.stButton > button:hover {
  background-color:#15803d !important; /* green-700 */
  border-color:#15803d !important;
}
/* Checkbox verte (navigateurs modernes) */
input[type="checkbox"]{ accent-color:#16a34a; }
</style>
""", unsafe_allow_html=True)

sb = get_client()
user = st.session_state.get("user")
if not user:
    st.stop()

# ---------- Utils
def _none_if_zero(x):
    try:
        return None if x == 0 or x == 0.0 else x
    except Exception:
        return None

def _pace_mmss_to_minutes(val: str):
    """
    'mm:ss' -> minutes décimales (float)
    Retourne (float|None, err|None)
    """
    if val is None:
        return None, None
    s = str(val).strip()
    if s == "":
        return None, None
    if ":" not in s:
        return None, "Format attendu mm:ss (ex: 6:36)"
    mm, ss = s.split(":", 1)
    if not (mm.isdigit() and ss.isdigit()):
        return None, "Utilise seulement des chiffres (mm:ss)"
    m = int(mm); s2 = int(ss)
    if s2 >= 60:
        return None, "Les secondes doivent être entre 0 et 59"
    return round(m + s2/60.0, 2), None

# ======================= BLOC UNIQUE =======================
with st.container(border=True):
    # Toggle tout en haut du bloc
    rest_day = st.checkbox(
        "Repos aujourd’hui",
        value=st.session_state.get("rest_day", False),
        key="rest_day",
    )

    # ---- Date
    st.subheader("Date")
    dt = st.date_input("Date", value=date.today())

    # ---- Bien-être + quotidien
    st.subheader("Bien-être (notes /10) + quotidien")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    fatigue        = c1.number_input("Fatigue (/10)",        min_value=0, max_value=10, value=0)
    irritabilite   = c2.number_input("Irritabilité (/10)",   min_value=0, max_value=10, value=0)
    douleurs       = c3.number_input("Douleurs (/10)",       min_value=0, max_value=10, value=0)
    malheur        = c4.number_input("Malheur (/10)",        min_value=0, max_value=10, value=0)
    charge_mentale = c5.number_input("Charge mentale (/10)", min_value=0, max_value=10, value=0)
    nombre_de_pas  = c6.number_input("Nombre de pas",        min_value=0, step=100, value=0)

    # Valeurs par défaut pour éviter les "variable referenced before assignment"
    seance_course = ""
    difficulte_seance = 0
    distance_km = 0.0
    temps_min = 0
    dplus_m = 0
    dmoins_m = 0
    calories = 0
    fc_moy = 0
    fc_max = 0
    ppm = 0
    z1 = z2 = z3 = z4 = z5 = 0
    allure_txt = ""
    vap_txt = ""
    allure_min_km = None
    vap_min_km = None
    pace_err = None
    vap_err = None

    meteo = ""
    vent_kmh = 0.0
    direction_vent = ""
    temperature_c = 0.0

    if not rest_day:

        # ---- Entraînement (masqué si repos)
        st.subheader("Entraînement")
        # Ligne 1 : Type de séance + Difficulté + Distance
        cA, cB, cC = st.columns(3)
        seance_course      = cA.selectbox("Type de séance", ["", "EF", "Seuil", "Fractionné", "Côte", "SL", "Course"], index=0)
        difficulte_seance  = cB.number_input("Difficulté de la séance (/10)", min_value=0, max_value=10, value=0)
        distance_km        = cC.number_input("Distance (km)", min_value=0.0, step=0.1, value=0.0)

        # Ligne 2 : Temps + D+ + D-
        cD, cE, cF = st.columns(3)
        temps_min = cD.number_input("Temps (min)", min_value=0, step=1, value=0)
        dplus_m   = cE.number_input("D+ (m)",      min_value=0, step=10, value=0)
        dmoins_m  = cF.number_input("D- (m)",      min_value=0, step=10, value=0)

        # Ligne 3 : Calories + Allure + VAP (mm:ss)
        cG, cH, cI = st.columns(3)
        calories   = cG.number_input("Calories", min_value=0, step=10, value=0)

        allure_txt = cH.text_input("Allure (min/km) — mm:ss", placeholder="ex: 6:36")
        allure_min_km, pace_err = _pace_mmss_to_minutes(allure_txt)
        if pace_err: cH.warning(pace_err)

        vap_txt = cI.text_input("VAP (min/km) — mm:ss", placeholder="ex: 6:10")
        vap_min_km, vap_err = _pace_mmss_to_minutes(vap_txt)
        if vap_err: cI.warning(vap_err)

        # Ligne 4 : FC moy + FC max + PPM (3 colonnes) — BPM récup supprimé
        cJ, cK, cM = st.columns(3)
        fc_moy    = cJ.number_input("FC moyenne", min_value=0, step=1, value=0)
        fc_max    = cK.number_input("FC max",     min_value=0, step=1, value=0)
        ppm       = cM.number_input("PPM",        min_value=0, step=1, value=0)

        # Ligne 5 : Zones côte à côte (ENTIERS) avec libellés clairs en %
        z1c, z2c, z3c, z4c, z5c = st.columns(5)
        z1 = z1c.number_input("Zone 1 (%)", min_value=0, max_value=100, value=0, step=1)
        z2 = z2c.number_input("Zone 2 (%)", min_value=0, max_value=100, value=0, step=1)
        z3 = z3c.number_input("Zone 3 (%)", min_value=0, max_value=100, value=0, step=1)
        z4 = z4c.number_input("Zone 4 (%)", min_value=0, max_value=100, value=0, step=1)
        z5 = z5c.number_input("Zone 5 (%)", min_value=0, max_value=100, value=0, step=1)

        zones_sum = z1 + z2 + z3 + z4 + z5
        if zones_sum > 0 and abs(zones_sum - 100) > 3:
            st.warning(f"La somme des zones fait {zones_sum} % (tolérance ±3 %).")

        # ---- Météo (champ 'Météo' en premier) + renommage des libellés
        st.subheader("Météo")
        m1, m2, m3, m4 = st.columns(4)
        meteo          = m1.selectbox("Météo", ["", "Soleil", "Nuageux", "Pluie", "Orage", "Vent", "Neige"], index=0)
        vent_kmh       = m2.number_input("Vitesse vent (km/h)", min_value=0.0, step=0.5, value=0.0)
        direction_vent = m3.selectbox("Direction vent", ["", "N","NE","E","SE","S","SO","O","NO"], index=0)
        temperature_c  = m4.number_input("Température (°C)", min_value=-50.0, max_value=60.0, step=0.5, value=0.0)

    # ---- Bouton Valider tout en bas du bloc
    submit_clicked = st.button("Valider")

# ======================= ENREGISTREMENT =======================
if submit_clicked:
    try:
        payload = {
            "user_id":           user["id"],
            "date":              dt.isoformat(),
            "fatigue":           fatigue,
            "irritabilite":      irritabilite,
            "douleurs":          douleurs,
            "malheur":           malheur,
            "charge_mentale":    charge_mentale,
            "nombre_de_pas":     int(_none_if_zero(nombre_de_pas)) if _none_if_zero(nombre_de_pas) is not None else None,
            # Difficulté de séance -> note_entrainement uniquement s'il y a séance
            "note_entrainement": difficulte_seance if not st.session_state.rest_day else None,
        }

        if not st.session_state.rest_day:
            payload.update({
                "seance_course":         seance_course or None,
                "distance_course_km":    float(_none_if_zero(distance_km)) if _none_if_zero(distance_km) is not None else None,
                "dplus_course_m":        int(_none_if_zero(dplus_m)) if _none_if_zero(dplus_m) is not None else None,
                "dmoins_course_m":       int(_none_if_zero(dmoins_m)) if _none_if_zero(dmoins_m) is not None else None,
                "temps_course_min":      int(_none_if_zero(temps_min)) if _none_if_zero(temps_min) is not None else None,
                "allure_course_min_km":  allure_min_km,   # mm:ss -> minutes
                "vap_course_min_km":     vap_min_km,      # mm:ss -> minutes
                "fc_moyenne_course":     int(_none_if_zero(fc_moy)) if _none_if_zero(fc_moy) is not None else None,
                "fc_max_course":         int(_none_if_zero(fc_max)) if _none_if_zero(fc_max) is not None else None,
                "pct_zone1_course":      float(_none_if_zero(z1)),
                "pct_zone2_course":      float(_none_if_zero(z2)),
                "pct_zone3_course":      float(_none_if_zero(z3)),
                "pct_zone4_course":      float(_none_if_zero(z4)),
                "pct_zone5_course":      float(_none_if_zero(z5)),
                "ppm_course":            int(_none_if_zero(ppm)) if _none_if_zero(ppm) is not None else None,
                "calories_course":       int(_none_if_zero(calories)) if _none_if_zero(calories) is not None else None,
                "sensation_course":      difficulte_seance,  # tu pourras dédier une colonne plus tard si besoin
                "force_vent_course_kmh": float(_none_if_zero(vent_kmh)) if _none_if_zero(vent_kmh) is not None else None,
                "direction_vent":        direction_vent or None,
                "temperature_c":         float(_none_if_zero(temperature_c)) if _none_if_zero(temperature_c) is not None else None,
                "meteo":                 meteo or None,
            })
        else:
            # Repos : nulifie tout ce qui concerne entraînement + météo
            for k in [
                "seance_course","distance_course_km","dplus_course_m","dmoins_course_m",
                "temps_course_min","allure_course_min_km","vap_course_min_km",
                "fc_moyenne_course","fc_max_course",
                "pct_zone1_course","pct_zone2_course","pct_zone3_course","pct_zone4_course","pct_zone5_course",
                "ppm_course","calories_course","sensation_course",
                "force_vent_course_kmh","direction_vent","temperature_c","meteo"
            ]:
                payload[k] = None

        sb.table("journal").insert(payload).execute()
        st.success("Ligne enregistrée ✔")
    except Exception as e:
        st.error(f"Erreur d’enregistrement : {e}")

# (aucun tableau en bas)

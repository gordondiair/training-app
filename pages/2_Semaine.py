# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login
from utils import side_bar_logout_button

sb = get_client()
u = require_login(sb)  # bloque la page tant que l'utilisateur n'est pas connecté
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

import pandas as pd
import plotly.express as px

st.title("📊 Semaine — agrégats")

# 1) Récupération via RPC (plus robuste que .table + RLS)
res = sb.rpc("weekly_summary_for_me").execute()
df = pd.DataFrame(res.data or [])

if df.empty:
    st.info("Pas encore de données.")
    st.stop()

# 2) Tri
df = df.sort_values(["iso_year", "week_no"])

# 3) Dictionnaire des métriques affichables
metrics = {
    "Km course": "run_km",
    "D+ course (m)": "run_dplus_m",
    "Temps course (heures)": "run_time_s",
    "Allure moyenne (min/km)": "allure_avg_min_km",
    "VAP moyenne (min/km)": "vap_avg_min_km",
    "FC moyenne (bpm)": "fc_avg_simple",
    "FC max (bpm)": "fc_max_week",
    "% Z1": "avg_pct_zone1",
    "% Z2": "avg_pct_zone2",
    "% Z3": "avg_pct_zone3",
    "% Z4": "avg_pct_zone4",
    "% Z5": "avg_pct_zone5",
    "BPM récup": "bpm_recup_avg",     # sera NaN tant que non mesuré
    "PPM": "ppm_avg",
    "Calories totales": "calories_total",
    "Sensation (/10)": "sensation_avg",
    "Pas totaux": "steps_total",
    "Fatigue moyenne (/10)": "fatigue_avg",
    "Irritabilité moyenne (/10)": "irritabilite_avg",
    "Douleurs moy. (/10)": "douleurs_avg",
    "Malheur moy. (/10)": "malheur_avg",
    "Charge mentale moy. (/10)": "charge_mentale_avg",
    "Score final moyen (/100)": "score_final_avg",  # NaN pour l'instant
}

# 4) Choix de la métrique
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
col = metrics[label]

# 5) Préparation des données pour l'affichage
plot_df = df.copy()
if col == "run_time_s":
    plot_df[col] = plot_df[col] / 3600.0  # secondes -> heures

# 6) Graph
fig = px.line(plot_df, x="week_key", y=col, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

# 7) Tableau récap
cols = ["week_key"] + list(metrics.values())
st.dataframe(plot_df[cols], use_container_width=True)

sidebar_logout_bottom(sb)

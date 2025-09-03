import streamlit as st
import pandas as pd
import plotly.express as px
from supa import get_client

st.title("📊 Semaine — agrégats")
sb = get_client()
user = st.session_state.get("user")
if not user: st.stop()

res = sb.table("weekly_summary").select("*").eq("user_id", user["id"]).execute()
df = pd.DataFrame(res.data)
if df.empty:
    st.info("Pas encore de données.")
    st.stop()

df = df.sort_values(["iso_year","week_key"])

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
    "BPM récup": "bpm_recup_avg",
    "PPM": "ppm_avg",
    "Calories totales": "calories_total",
    "Sensation (/10)": "sensation_avg",
    "Pas totaux": "steps_total",
    "Fatigue moyenne (/10)": "fatigue_avg",
    "Irritabilité moyenne (/10)": "irritabilite_avg",
    "Douleurs moy. (/10)": "douleurs_avg",
    "Malheur moy. (/10)": "malheur_avg",
    "Charge mentale moy. (/10)": "charge_mentale_avg",
    "Score final moyen (/100)": "score_final_avg",
}

label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
col = metrics[label]

plot_df = df.copy()
if col == "run_time_s":
    plot_df[col] = plot_df[col] / 3600.0

fig = px.line(plot_df, x="week_key", y=col, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df[["week_key"] + list(metrics.values())])

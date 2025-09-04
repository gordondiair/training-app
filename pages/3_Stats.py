# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login
from utils import sidebar_logout_bottom

sb = get_client()
u = require_login(sb)  # bloque la page tant que l'utilisateur n'est pas connecté
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

import pandas as pd
import numpy as np
import plotly.express as px

st.title("📊 Semaine — agrégats")

# ---------- Helpers ----------
def mmss_from_min_per_km(x: float) -> str:
    """x en minutes/km -> 'mm:ss/km' ; gère NaN/inf."""
    if x is None or pd.isna(x) or not np.isfinite(x) or x <= 0:
        return ""
    total_sec = int(round(x * 60))
    mm = total_sec // 60
    ss = total_sec % 60
    return f"{mm:d}:{ss:02d}/km"

# ---------- 1) Récupération via RPC ----------
res = sb.rpc("weekly_summary_for_me").execute()
df = pd.DataFrame(res.data or [])

if df.empty:
    st.info("Pas encore de données.")
    sidebar_logout_bottom(sb)
    st.stop()

# ---------- 2) Tri + colonnes dérivées ----------
df = df.sort_values(["iso_year", "week_no"]).reset_index(drop=True)

# temps en heures pour l'affichage
df["run_time_hours"] = (pd.to_numeric(df["run_time_s"], errors="coerce") / 3600.0)

# colonnes formatées lisibles
df_display = df.copy()
df_display["Allure (mm:ss/km)"] = df_display["allure_avg_min_km"].apply(mmss_from_min_per_km)
df_display["VAP (mm:ss/km)"]    = df_display["vap_avg_min_km"].apply(mmss_from_min_per_km)

# ---------- 3) Dictionnaire des métriques pour le graphe ----------
metrics = {
    "Km course": "run_km",
    "D+ course (m)": "run_dplus_m",
    "Temps course (heures)": "run_time_hours",
    "Allure moyenne (min/km)": "allure_avg_min_km",
    "VAP moyenne (min/km)": "vap_avg_min_km",
    "FC moyenne (bpm)": "fc_avg_simple",
    "FC max (bpm)": "fc_max_week",
    "Calories totales": "calories_total",
    "Pas totaux": "steps_total",
    "Effort relatif moyen": "relative_effort_avg",
}

# ---------- 4) Sélection + graphe ----------
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
ycol = metrics[label]

fig = px.line(df, x="week_key", y=ycol, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

# ---------- 5) Tableau récap ----------
# On montre les colonnes numériques + les versions formatées mm:ss/km
table_cols = [
    "iso_year", "week_no", "week_key",
    "run_km", "run_dplus_m", "run_time_hours",
    "allure_avg_min_km", "Allure (mm:ss/km)",
    "vap_avg_min_km",    "VAP (mm:ss/km)",
    "fc_avg_simple", "fc_max_week",
    "calories_total", "steps_total", "relative_effort_avg",
]

# Sécurise la présence (au cas où le RPC évoluerait)
table_cols = [c for c in table_cols if c in df_display.columns]

# Nettoie inf/NaN pour un rendu propre
df_show = df_display.copy()
for c in table_cols:
    if c in df_show.columns and df_show[c].dtype != "object":
        df_show[c] = pd.to_numeric(df_show[c], errors="coerce")
        df_show[c] = df_show[c].replace([np.inf, -np.inf], np.nan)

st.dataframe(df_show[table_cols], use_container_width=True)

sidebar_logout_bottom(sb)

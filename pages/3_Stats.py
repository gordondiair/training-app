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

# ---------- Helpers (affichage tableau uniquement) ----------
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

# ---------- 2) Tri + nettoyages légers ----------
df = df.sort_values(["iso_year", "week_no"]).reset_index(drop=True)

# Forcer numérique (sans changement d’unité) sur les colonnes qu’on trace
num_cols = [
    "run_km", "run_dplus_m", "run_time_minutes",
    "average_speed", "average_grade_adjusted_pace",
    "fc_avg_simple", "calories_total", "steps_total", "relative_effort_avg"
]
for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").replace([np.inf, -np.inf], np.nan)

# ---------- 3) Dictionnaire des métriques pour le graphe ----------
metrics = {
    "Km course": "run_km",
    "D+ course (m)": "run_dplus_m",
    "Temps course (minutes)": "run_time_minutes",
    "Allure moyenne (min/km)": "average_speed",                   # <-- DB direct
    "VAP moyenne (min/km)": "average_grade_adjusted_pace",        # <-- DB direct
    "FC moyenne (bpm)": "fc_avg_simple",
    "Calories totales": "calories_total",
    "Pas totaux": "steps_total",
    "Effort relatif moyen": "relative_effort_avg",
}
# (FC max retiré)

# ---------- 4) Sélection + graphe ----------
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
ycol = metrics[label]

if ycol not in df.columns:
    st.error(f"La colonne « {ycol} » est absente du RPC. Vérifie la fonction SQL.")
else:
    fig = px.line(df, x="week_key", y=ycol, markers=True, title=label)
    fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5) Tableau récap ----------
df_display = df.copy()
if "average_speed" in df_display.columns:
    df_display["Allure (mm:ss/km)"] = df_display["average_speed"].apply(mmss_from_min_per_km)
if "average_grade_adjusted_pace" in df_display.columns:
    df_display["VAP (mm:ss/km)"]    = df_display["average_grade_adjusted_pace"].apply(mmss_from_min_per_km)

table_cols = [
    "iso_year", "week_no", "week_key",
    "run_km", "run_dplus_m", "run_time_minutes",
    "average_speed", "Allure (mm:ss/km)",
    "average_grade_adjusted_pace", "VAP (mm:ss/km)",
    "fc_avg_simple",
    "calories_total", "steps_total", "relative_effort_avg",
]
table_cols = [c for c in table_cols if c in df_display.columns]

st.dataframe(df_display[table_cols], use_container_width=True)

sidebar_logout_bottom(sb)

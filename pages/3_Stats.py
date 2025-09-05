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

st.set_page_config(page_title="📊 Semaine — agrégats", layout="wide")
st.title("📊 Semaine — agrégats")

def mmss_from_min_per_km(x: float) -> str:
    """x en minutes/km -> 'mm:ss/km' ; gère NaN/inf (pour affichage tableau)."""
    if x is None or pd.isna(x) or not np.isfinite(x) or x <= 0:
        return ""
    total_sec = int(round(float(x) * 60))
    mm = total_sec // 60
    ss = total_sec % 60
    return f"{mm}:{ss:02d}/km"

# ---------- 1) Récupération via RPC ----------
res = sb.rpc("weekly_summary_for_me").execute()
df = pd.DataFrame(res.data or [])

if df.empty:
    st.info("Pas encore de données.")
    sidebar_logout_bottom(sb)
    st.stop()

# ---------- 2) Tri + nettoyage numérique ----------
df = df.sort_values(["iso_year", "week_no"]).reset_index(drop=True)

numeric_cols = [
    "run_km", "run_dplus_m", "run_time_s",
    "allure_avg_min_km", "vap_avg_min_km",
    "average_speed", "average_grade_adjusted_pace",
    "fc_avg_simple", "calories_total", "steps_total", "relative_effort_avg"
]
for c in numeric_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").replace([np.inf, -np.inf], np.nan)

# Temps course en minutes pour le graphe (optionnel)
if "run_time_s" in df.columns:
    df["run_time_minutes"] = df["run_time_s"] / 60.0

# ---------- 3) Dictionnaire des métriques ----------
metrics = {}
if "run_km" in df.columns:
    metrics["Km course"] = "run_km"
if "run_dplus_m" in df.columns:
    metrics["D+ course (m)"] = "run_dplus_m"
if "run_time_minutes" in df.columns:
    metrics["Temps course (minutes)"] = "run_time_minutes"
if "average_speed" in df.columns:
    metrics["Allure moyenne (min/km)"] = "average_speed"  # min/km si ta fonction RPC renvoie déjà ça
if "average_grade_adjusted_pace" in df.columns:
    metrics["VAP moyenne (min/km)"] = "average_grade_adjusted_pace"  # min/km si dispo
if "fc_avg_simple" in df.columns:
    metrics["FC moyenne (bpm)"] = "fc_avg_simple"
if "calories_total" in df.columns:
    metrics["Calories totales"] = "calories_total"
if "steps_total" in df.columns:
    metrics["Pas totaux"] = "steps_total"
if "relative_effort_avg" in df.columns:
    metrics["Effort relatif moyen"] = "relative_effort_avg"

if not metrics:
    st.error("Aucune métrique disponible dans le RPC.")
    sidebar_logout_bottom(sb)
    st.stop()

# ---------- 4) Sélection + graphe ----------
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
ycol = metrics[label]

fig = px.line(df, x="week_key", y=ycol, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

# ---------- 5) Tableau récap ----------
df_display = df.copy()
if "average_speed" in df_display.columns:
    df_display["Allure (mm:ss/km)"] = df_display["average_speed"].apply(mmss_from_min_per_km)
if "average_grade_adjusted_pace" in df_display.columns:
    df_display["VAP (mm:ss/km)"] = df_display["average_grade_adjusted_pace"].apply(mmss_from_min_per_km)

table_cols = [
    "iso_year", "week_no", "week_key",
    "run_km", "run_dplus_m", "run_time_s", "run_time_minutes",
    "allure_avg_min_km", "vap_avg_min_km",
    "average_speed", "Allure (mm:ss/km)",
    "average_grade_adjusted_pace", "VAP (mm:ss/km)",
    "fc_avg_simple",
    "calories_total", "steps_total", "relative_effort_avg",
]
table_cols = [c for c in table_cols if c in df_display.columns]

st.dataframe(df_display[table_cols], use_container_width=True)

sidebar_logout_bottom(sb)

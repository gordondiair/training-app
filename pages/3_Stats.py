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
    """x en minutes/km -> 'mm:ss/km' ; gère NaN/inf (pour affichage tableau uniquement)."""
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

# 2.a) Temps course en minutes : on prend directement 'elapsed_time' (déjà minutes). Fallback sur run_time_s/60 si besoin.
if "elapsed_time" in df.columns:
    df["run_time_minutes"] = pd.to_numeric(df["elapsed_time"], errors="coerce")
else:
    df["run_time_minutes"] = pd.to_numeric(df.get("run_time_s"), errors="coerce") / 60.0

# 2.b) Allure & VAP : on prend TEL QUEL depuis la DB (déjà en min/km). Pas de conversion d’unités.
#     (On force simplement en numérique si stocké en string "5.30" etc., sans changer d’échelle.)
required = ["average_speed", "average_grade_adjusted_pace"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.warning("Colonnes attendues manquantes : " + ", ".join(missing))

df["average_speed"] = pd.to_numeric(df.get("average_speed"), errors="coerce")
df["average_grade_adjusted_pace"] = pd.to_numeric(df.get("average_grade_adjusted_pace"), errors="coerce")

# 2.c) Colonnes formatées (pour le tableau uniquement ; les graphes utilisent les colonnes brutes)
df_display = df.copy()
df_display["Allure (mm:ss/km)"] = df_display["average_speed"].apply(mmss_from_min_per_km)
df_display["VAP (mm:ss/km)"]    = df_display["average_grade_adjusted_pace"].apply(mmss_from_min_per_km)

# ---------- 3) Dictionnaire des métriques pour le graphe ----------
metrics = {
    "Km course": "run_km",
    "D+ course (m)": "run_dplus_m",
    "Temps course (minutes)": "run_time_minutes",                 # <-- elapsed_time (minutes)
    "Allure moyenne (min/km)": "average_speed",                   # <-- DB direct (min/km)
    "VAP moyenne (min/km)": "average_grade_adjusted_pace",        # <-- DB direct (min/km)
    "FC moyenne (bpm)": "fc_avg_simple",
    "Calories totales": "calories_total",
    "Pas totaux": "steps_total",
    "Effort relatif moyen": "relative_effort_avg",
}
# (FC max retiré)

# ---------- 4) Sélection + graphe ----------
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
ycol = metrics[label]

# On s'assure que la colonne Y est numérique (sans changer d'unité).
df[ycol] = pd.to_numeric(df[ycol], errors="coerce")

fig = px.line(df, x="week_key", y=ycol, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

# ---------- 5) Tableau récap ----------
table_cols = [
    "iso_year", "week_no", "week_key",
    "run_km", "run_dplus_m", "run_time_minutes",
    "average_speed", "Allure (mm:ss/km)",
    "average_grade_adjusted_pace", "VAP (mm:ss/km)",
    "fc_avg_simple",
    "calories_total", "steps_total", "relative_effort_avg",
]
table_cols = [c for c in table_cols if c in df_display.columns]

df_show = df_display.copy()
for c in table_cols:
    if c in df_show.columns and df_show[c].dtype != "object":
        df_show[c] = pd.to_numeric(df_show[c], errors="coerce")
        df_show[c] = df_show[c].replace([np.inf, -np.inf], np.nan)

st.dataframe(df_show[table_cols], use_container_width=True)

sidebar_logout_bottom(sb)

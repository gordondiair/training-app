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

def pace_min_per_km_from_speed(speed):
    """
    Convertit une vitesse en 'min/km'.
    - Si la vitesse semble en m/s (<= 8 m/s ~ 28.8 km/h), on utilise 16.6667 / m/s.
    - Sinon on suppose km/h et on utilise 60 / kmh.
    Gère NaN/inf/<=0.
    """
    s = pd.to_numeric(speed, errors="coerce")
    if pd.isna(s) or not np.isfinite(s) or s <= 0:
        return np.nan
    if s <= 8:  # heuristique: course à pied en m/s rarement > 8 m/s
        return 16.6666666667 / s  # (1000/60)/mps
    else:
        return 60.0 / s  # km/h -> min/km

def parse_min_per_km(value):
    """
    Convertit diverses formes de 'allure' vers min/km (float):
    - 'mm:ss' ou 'm:ss' -> min + sec/60
    - nombre > 40 -> suppose secondes/km -> /60
    - nombre raisonnable (2..20) -> déjà min/km
    """
    if isinstance(value, str):
        s = value.strip()
        if ":" in s:
            try:
                mm, ss = s.split(":")
                return float(mm) + float(ss) / 60.0
            except Exception:
                return np.nan
        # sinon tenter numérique simple
        try:
            v = float(s.replace(",", "."))
        except Exception:
            return np.nan
        return v / 60.0 if v > 40 else v
    else:
        v = pd.to_numeric(value, errors="coerce")
        if pd.isna(v):
            return np.nan
        return v / 60.0 if v > 40 else v

# ---------- 1) Récupération via RPC ----------
res = sb.rpc("weekly_summary_for_me").execute()
df = pd.DataFrame(res.data or [])

if df.empty:
    st.info("Pas encore de données.")
    sidebar_logout_bottom(sb)
    st.stop()

# ---------- 2) Tri + colonnes dérivées ----------
df = df.sort_values(["iso_year", "week_no"]).reset_index(drop=True)

# 2.a) Temps course en minutes : on prend directement la colonne 'elapsed_time' (déjà en minutes)
#     Si jamais absente, on retombe sur run_time_s / 60.
if "elapsed_time" in df.columns:
    df["run_time_minutes"] = pd.to_numeric(df["elapsed_time"], errors="coerce")
else:
    df["run_time_minutes"] = pd.to_numeric(df.get("run_time_s"), errors="coerce") / 60.0

# 2.b) Allure moyenne depuis average_speed -> min/km
if "average_speed" in df.columns:
    df["allure_avg_min_km_from_speed"] = df["average_speed"].apply(pace_min_per_km_from_speed)
else:
    # fallback : garder éventuellement la colonne déjà fournie par le RPC
    df["allure_avg_min_km_from_speed"] = pd.to_numeric(df.get("allure_avg_min_km"), errors="coerce")

# 2.c) VAP moyenne depuis average_grade_adjusted_pace -> min/km
if "average_grade_adjusted_pace" in df.columns:
    df["vap_avg_min_km_from_gap"] = df["average_grade_adjusted_pace"].apply(parse_min_per_km)
else:
    df["vap_avg_min_km_from_gap"] = pd.to_numeric(df.get("vap_avg_min_km"), errors="coerce")

# 2.d) Colonnes formatées lisibles
df_display = df.copy()
df_display["Allure (mm:ss/km)"] = df_display["allure_avg_min_km_from_speed"].apply(mmss_from_min_per_km)
df_display["VAP (mm:ss/km)"]    = df_display["vap_avg_min_km_from_gap"].apply(mmss_from_min_per_km)

# ---------- 3) Dictionnaire des métriques pour le graphe ----------
metrics = {
    "Km course": "run_km",
    "D+ course (m)": "run_dplus_m",
    "Temps course (minutes)": "run_time_minutes",       # <-- elapsed_time (minutes)
    "Allure moyenne (min/km)": "allure_avg_min_km_from_speed",  # <-- depuis average_speed
    "VAP moyenne (min/km)": "vap_avg_min_km_from_gap",          # <-- depuis average_grade_adjusted_pace
    "FC moyenne (bpm)": "fc_avg_simple",
    "Calories totales": "calories_total",
    "Pas totaux": "steps_total",
    "Effort relatif moyen": "relative_effort_avg",
}
# (FC max retiré)

# ---------- 4) Sélection + graphe ----------
label = st.selectbox("Choisis la métrique à tracer", list(metrics.keys()), index=0)
ycol = metrics[label]

fig = px.line(df, x="week_key", y=ycol, markers=True, title=label)
fig.update_layout(xaxis_title="Semaine ISO", yaxis_title=label)
st.plotly_chart(fig, use_container_width=True)

# ---------- 5) Tableau récap ----------
table_cols = [
    "iso_year", "week_no", "week_key",
    "run_km", "run_dplus_m", "run_time_minutes",
    "allure_avg_min_km_from_speed", "Allure (mm:ss/km)",
    "vap_avg_min_km_from_gap",      "VAP (mm:ss/km)",
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

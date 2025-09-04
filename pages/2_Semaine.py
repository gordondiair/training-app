# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

import pandas as pd
import plotly.express as px

st.title("📊 Semaine — agrégats")

user = st.session_state.get("user")
if not user: st.stop()

res = sb.table("weekly_summary").select("*").eq("user_id", user["id"]).execute()
df = pd.DataFrame(res.data)
if df.empty:
    st.info("Pas encore de données.")
    st.stop()

df = df.sort_values(["iso_year", "week_key"])

# ... reste inchangé (metrics, selectbox, plotly, dataframe)

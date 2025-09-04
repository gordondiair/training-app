# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login
from utils import sidebar_logout_button

sb = get_client()
u = require_login(sb)
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

import re
import pandas as pd
import plotly.express as px

st.title("🤖 Questions (MVP)")

user = st.session_state.get("user")
if not user: st.stop()

txt = st.text_input("Ex: fc moyenne semaines 23 à 30")
if not txt: st.stop()

res = sb.table("weekly_summary").select("*").eq("user_id", user["id"]).execute()
df = pd.DataFrame(res.data)
if df.empty:
    st.info("Pas de données.")
    st.stop()

# ... reste inchangé (regex, métrique choisie, plotly)

sidebar_logout_bottom(sb)

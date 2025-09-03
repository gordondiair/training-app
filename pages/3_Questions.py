import re
import streamlit as st
import pandas as pd
import plotly.express as px
from supa import get_client

st.title("🤖 Questions (MVP)")
sb = get_client()
user = st.session_state.get("user")
if not user: st.stop()

txt = st.text_input("Ex: fc moyenne semaines 23 à 30")
if not txt: st.stop()

res = sb.table("weekly_summary").select("*").eq("user_id", user["id"]).execute()
df = pd.DataFrame(res.data)
if df.empty:
    st.info("Pas de données.")
    st.stop()

metric = "fc_avg_simple"
if "km" in txt.lower(): metric = "run_km"
if "vélo" in txt.lower(): metric = "bike_km"

m = re.search(r"(\d{1,2}).*?(\d{1,2})", txt)
if m:
    lo, hi = sorted([int(m.group(1)), int(m.group(2))])
    df["_w"] = df["week_key"].str.extract(r"W(\d{1,2})").astype(int)
    df = df[(df["_w"] >= lo) & (df["_w"] <= hi)]

if df.empty:
    st.info("Rien à afficher.")
    st.stop()

fig = px.line(df.sort_values("week_key"), x="week_key", y=metric, markers=True,
              title=f"{metric} par semaine")
st.plotly_chart(fig, use_container_width=True)

# Accueil.py
import streamlit as st
import pandas as pd
import plotly.express as px

from supa import get_client
from utils import require_login, logout, sidebar_logout_bottom

# =========================
# Page config
# =========================
st.set_page_config(page_title="🏁 Tableau de bord", layout="wide")

# =========================
# Auth (bloque tant que non connecté)
# =========================
sb = get_client()
u = require_login(sb)  # stoppe l'exécution tant que l'utilisateur n'est pas loggé
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}

# =========================
# Header / hero simple
# =========================
st.title("Ton entraînement, clair et motivant")
st.caption("Import Strava en 2 clics, dédoublonnage intelligent, KPIs lisibles et graphiques harmonisés.")

# CTA
st.button("Importer mes données")

# =========================
# KPIs (exemples statiques — remplace par tes vraies variables)
# =========================
st.subheader("Tes stats clés")
st.caption("Mise à jour après chaque import.")

cols = st.columns(3)
with cols[0]:
    st.metric(label="Distance (7j)", value="58.3 km", delta="+12% vs N-1")
    st.caption("Total semaine en cours")
with cols[1]:
    st.metric(label="D+ (7j)", value="+2 150 m", delta="+5%")
with cols[2]:
    st.metric(label="Temps actif (7j)", value="6 h 42", delta="-8%")

# =========================
# Graphique (exemple)
# =========================
st.subheader("Vue quotidienne")
st.caption("Un coup d’œil sur ta charge récente.")

df = pd.DataFrame({
    "date": pd.date_range("2025-08-25", periods=10, freq="D"),
    "km": [5.1, 8.2, 0.0, 10.3, 7.5, 6.2, 0.0, 12.4, 11.1, 9.0]
})
fig = px.bar(df, x="date", y="km", title="Kilométrage quotidien")
st.plotly_chart(fig, use_container_width=True)

# =========================
# Infos / aide
# =========================
st.info("Astuce : importe un CSV Strava pour générer automatiquement tes stats et détecter les doublons. 🚀")

# =========================
# Zone compte / logout
# =========================
st.success(f"Connecté : {st.session_state['user']['email']}")
if st.button("Se déconnecter"):
    logout(sb)
    st.rerun()

sidebar_logout_bottom(sb)

# =========================
# Liens vers autres pages
# =========================
st.write("👈 Utilise le menu à gauche :")
st.write("- **Saisie — Journal** : ajoute tes données")
st.write("- **Stats (Semaine)** : visualise les agrégats")
st.write("- **Questions (MVP)** : question libre (graph basique)")

# =========================
# Footer simple
# =========================
st.caption("© Training App — Exemple de tableau de bord")

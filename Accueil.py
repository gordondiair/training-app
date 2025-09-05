import streamlit as st
import pandas as pd
from supa import get_client
from utils import require_login, logout  # <-- plus de set_cookie/del_cookie
from utils import sidebar_logout_bottom
from utils_ui import inject_base_css, hero, section, stat_cards, callout, app_footer, bar, line

st.set_page_config(page_title="🏁 Tableau de bord", layout="wide")

# 1) Styles globaux
inject_base_css()

# 2) En-tête “marketing”
hero(
    title="Ton entraînement, clair et motivant",
    subtitle="Import Strava en 2 clics, dédoublonnage intelligent, KPIs lisibles et graphiques harmonisés.",
    emoji="✨",
    cta_label="Importer mes données"
)

# 3) KPIs (exemples statiques — remplace par tes vraies variables)
section("Tes stats clés", "Mise à jour après chaque import.")
stat_cards([
    {"label":"Distance (7j)", "value":"58.3 km", "delta":"+12% vs N-1", "help":"Total semaine en cours"},
    {"label":"D+ (7j)", "value":"+2 150 m", "delta":"+5%"},
    {"label":"Temps actif (7j)", "value":"6 h 42", "delta":"-8%"},
])

# 4) Graphique (exemple)
section("Vue quotidienne", "Un coup d’œil sur ta charge récente.")
df = pd.DataFrame({
    "date": pd.date_range("2025-08-25", periods=10, freq="D"),
    "km": [5.1, 8.2, 0.0, 10.3, 7.5, 6.2, 0.0, 12.4, 11.1, 9.0]
})
fig = bar(df, x="date", y="km", title="Kilométrage quotidien")
st.plotly_chart(fig, use_container_width=True)

# 5) Empty states / info
callout("Astuce : importe un CSV Strava pour générer automatiquement tes stats et détecter les doublons. 🚀", tone="info")

# 6) Footer
app_footer(brand_name="Training App", site_url="https://exemple.com", email="hello@exemple.com")

# ---- Boot / client Supabase + login obligatoire ----
sb = get_client()
u = require_login(sb)  # bloque tant que l’utilisateur n’est pas connecté
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}

# ================================
# UI connecté
# ================================
st.success(f"Connecté : {st.session_state['user']['email']}")

# Bouton logout
if st.button("Se déconnecter"):
    logout(sb)
    st.rerun()
    
sidebar_logout_bottom(sb)

# ---- Contenu d’accueil
st.write("👈 Utilise le menu **Pages** (en haut à gauche) :")
st.write("- **🏠 Saisie — Journal** : ajoute tes données")
st.write("- **📊 Semaine — agrégats** : visualise les stats")
st.write("- **🤖 Questions (MVP)** : question libre (graph basique)")

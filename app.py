import streamlit as st
from supa import get_client
from utils import require_login, logout  # <-- plus de set_cookie/del_cookie

st.set_page_config(page_title="Training App", layout="wide")

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

# ---- Contenu d’accueil
st.write("👈 Utilise le menu **Pages** (en haut à gauche) :")
st.write("- **🏠 Saisie — Journal** : ajoute tes données")
st.write("- **📊 Semaine — agrégats** : visualise les stats")
st.write("- **🤖 Questions (MVP)** : question libre (graph basique)")

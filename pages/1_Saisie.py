# --- Header commun à toutes les pages ---
import streamlit as st
from supa import get_client
from utils import require_login

sb = get_client()
u = require_login(sb)  # bloque tant que l'utilisateur n'est pas connecté
st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
# --- Fin du header commun ---

from datetime import date

st.title("🏠 Saisie — Journal")

# ---------- Styles globaux : bouton vert + checkbox verte
st.markdown("""
<style>
div.stButton > button {
  background-color:#16a34a !important;
  color:white !important;
  border:1px solid #16a34a !important;
}
div.stButton > button:hover {
  background-color:#15803d !important;
  border-color:#15803d !important;
}
input[type="checkbox"]{ accent-color:#16a34a; }
</style>
""", unsafe_allow_html=True)

user = st.session_state.get("user")
if not user:
    st.stop()

# ... le reste de ton code identique (formulaire, payload, insert supabase)

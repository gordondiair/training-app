import streamlit as st
from supa import get_client

st.set_page_config(page_title="Training App", layout="wide")

def auth_block():
    sb = get_client()

    # On mémorise l'utilisateur dans la session
    if "user" not in st.session_state:
        st.session_state.user = None

    # Si déjà connecté
    if st.session_state.user:
        st.success(f"Connecté : {st.session_state.user['email']}")
        if st.button("Se déconnecter"):
            st.session_state.user = None
            st.rerun()
        return True

    # Ecran de connexion / création de compte
    st.header("Connexion / Création de compte")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Se connecter")
        email = st.text_input("Email", key="login_email")
        pwd = st.text_input("Mot de passe", type="password", key="login_pwd")
        if st.button("Connexion"):
            try:
                data = sb.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = {"id": data.user.id, "email": data.user.email}
                st.rerun()
            except Exception as e:
                st.error(f"Échec connexion : {e}")

    with col2:
        st.subheader("Créer un compte")
        email2 = st.text_input("Email", key="signup_email")
        pwd2 = st.text_input("Mot de passe", type="password", key="signup_pwd")
        if st.button("Créer mon compte"):
            try:
                sb.auth.sign_up({"email": email2, "password": pwd2})
                st.success("Compte créé. Vérifie tes emails puis connecte-toi.")
            except Exception as e:
                st.error(f"Échec création : {e}")

    return False

# ---- Main ----
if not auth_block():
    st.stop()

st.write("👈 Utilise le menu **Pages** (en haut à gauche) :")
st.write("- **🏠 Saisie — Journal** : ajoute tes données")
st.write("- **📊 Semaine — agrégats** : visualise les stats")
st.write("- **🤖 Questions (MVP)** : question libre (graph basique)")

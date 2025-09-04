import streamlit as st
from supa import get_client
from utils import restore_session, set_cookie, del_cookie

st.set_page_config(page_title="Training App", layout="wide")

# ---- Boot / client Supabase + restauration de session ----
sb = get_client()

# On garde une compatibilité avec tes pages qui lisent st.session_state.user
def _sync_user_state():
    u = sb.auth.get_user()
    if u:
        st.session_state["user"] = {"id": u.user.id, "email": u.user.email}
    else:
        st.session_state["user"] = None
    return u

u = _sync_user_state()

# ================================
# UI non connecté : Login / Signup
# ================================
if not u:
    st.header("Connexion / Création de compte")
    tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        pwd   = st.text_input("Mot de passe", type="password", key="login_pwd")
        remember = st.checkbox("Se souvenir de moi", value=True)
        if st.button("Connexion"):
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": pwd})
                # mémorise session côté app
                st.session_state["sb_session"] = res.session
                # cookie "remember me"
                if remember and res.session and res.session.refresh_token:
                    set_cookie(res.session.refresh_token)
                _sync_user_state()
                st.rerun()
            except Exception as e:
                st.error(f"Échec connexion : {e}")

    with tab_signup:
        email2 = st.text_input("Email", key="signup_email")
        pwd2   = st.text_input("Mot de passe", type="password", key="signup_pwd")
        if st.button("Créer mon compte"):
            try:
                sb.auth.sign_up({"email": email2, "password": pwd2})
                st.success("Compte créé. Vérifie tes emails, puis connecte-toi dans l’onglet 'Se connecter'.")
            except Exception as e:
                st.error(f"Échec création : {e}")

    st.stop()  # tant qu'on n'est pas connecté, on n'affiche pas la suite

# ================================
# UI connecté
# ================================
st.success(f"Connecté : {st.session_state.user['email']}")

# Bouton logout (nettoie session + cookie)
if st.button("Se déconnecter"):
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    del_cookie()
    st.session_state.pop("sb_session", None)
    st.session_state["user"] = None
    st.rerun()

# ---- Contenu d’accueil
st.write("👈 Utilise le menu **Pages** (en haut à gauche) :")
st.write("- **🏠 Saisie — Journal** : ajoute tes données")
st.write("- **📊 Semaine — agrégats** : visualise les stats")
st.write("- **🤖 Questions (MVP)** : question libre (graph basique)")

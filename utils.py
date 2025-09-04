import streamlit as st
from time import time

# ================================
# Tes fonctions existantes
# ================================
def hhmmss_to_seconds(txt: str) -> int:
    """'HH:MM:SS' -> secondes"""
    h, m, s = [int(x) for x in txt.split(":")]
    return h*3600 + m*60 + s

def seconds_to_excel_time(seconds: int) -> float:
    """Convertit des secondes en valeur temps Excel (jours)"""
    return (seconds or 0) / 86400.0


# ================================
# Ajouts pour gestion de session
# ================================

# Config cookie (personnalisable via .streamlit/secrets.toml si tu veux)
COOKIE_NAME   = "sb_refresh_token"
COOKIE_DAYS   = int(st.secrets.get("COOKIE_DAYS", 14))
# En prod (HTTPS), mets COOKIE_SECURE=True dans secrets; en local tu peux laisser False
COOKIE_SECURE = bool(st.secrets.get("COOKIE_SECURE", False))

def set_cookie(value: str, days: int = COOKIE_DAYS):
    """Pose le cookie contenant le refresh token Supabase."""
    st.experimental_set_cookie(
        COOKIE_NAME,
        value,
        max_age=days * 24 * 3600,
        path="/",
        secure=COOKIE_SECURE,
        samesite="Lax",
    )

def del_cookie():
    """Supprime le cookie de refresh."""
    st.experimental_delete_cookie(COOKIE_NAME, path="/")

def get_cookie():
    """Récupère le refresh token stocké en cookie (ou None)."""
    return st.experimental_get_cookie(COOKIE_NAME)

def restore_session(sb):
    """
    À appeler au début de chaque page:
    - Réapplique une session déjà en mémoire (session_state)
    - Sinon, tente l’auto-login via le cookie refresh token
    - Rafraîchit la session si elle expire bientôt
    """
    # 1) Réappliquer la session mémoire si dispo
    ssess = st.session_state.get("sb_session")
    if ssess:
        try:
            sb.auth.set_session(ssess.access_token, ssess.refresh_token)
        except Exception:
            pass

    # 2) Sinon, tentative via cookie (refresh token)
    if not sb.auth.get_user():
        rt = get_cookie()
        if rt:
            try:
                # set_session(access_token, refresh_token) — access peut être vide
                sb.auth.set_session("", rt)
                sb.auth.refresh_session()
                st.session_state["sb_session"] = sb.auth.get_session()
            except Exception:
                # Cookie invalide/expiré -> on nettoie
                del_cookie()

    # 3) Entretien: rafraîchir si expiration < 60s
    sess = sb.auth.get_session()
    if sess:
        st.session_state["sb_session"] = sess
        try:
            exp = int(getattr(sess, "expires_at", 0))
        except Exception:
            exp = 0
        if exp and exp < int(time()) + 60:
            try:
                sb.auth.refresh_session()
                st.session_state["sb_session"] = sb.auth.get_session()
            except Exception:
                # Si le refresh échoue, on évite les boucles
                del_cookie()

def require_login(sb, title: str = "Connexion"):
    """
    Bloque la page tant que l’utilisateur n’est pas connecté.
    - Restaure d’abord la session (mémoire + cookie)
    - Affiche un petit formulaire de connexion sinon
    Retourne l’objet user si connecté.
    """
    restore_session(sb)
    user = sb.auth.get_user()
    if user:
        return user

    st.subheader(title)
    with st.form("login", clear_on_submit=False):
        email = st.text_input("Email")
        pwd   = st.text_input("Mot de passe", type="password")
        remember = st.checkbox("Se souvenir de moi", value=True)
        go = st.form_submit_button("Se connecter")

    if go:
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": pwd})
            st.session_state["sb_session"] = res.session
            if remember and res.session and res.session.refresh_token:
                set_cookie(res.session.refresh_token)
            st.rerun()
        except Exception:
            st.error("Échec de connexion. Vérifie tes identifiants.")
            st.stop()

    # Tant qu'on n'est pas connecté, on stoppe la suite de la page
    st.stop()

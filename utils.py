# utils.py
import streamlit as st
from time import time

# ================================
# Outils temps / Excel
# ================================
def hhmmss_to_seconds(txt: str) -> int:
    h, m, s = [int(x) for x in txt.split(":")]
    return h * 3600 + m * 60 + s

def seconds_to_excel_time(seconds: int) -> float:
    return (seconds or 0) / 86400.0


# ================================
# Gestion session / cookies (optionnels)
# ================================
COOKIE_NAME = "sb_refresh_token"

def _to_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(v, (int, float)):
        return bool(v)
    return default

COOKIE_DAYS   = int(st.secrets.get("COOKIE_DAYS", 14))
COOKIE_SECURE = _to_bool(st.secrets.get("COOKIE_SECURE", False), False)

def _get_cookie(name: str):
    if hasattr(st, "experimental_get_cookie"):
        try:
            return st.experimental_get_cookie(name)
        except Exception:
            return None
    return None

def _set_cookie(name: str, value: str, days: int):
    if hasattr(st, "experimental_set_cookie"):
        try:
            st.experimental_set_cookie(
                name,
                value,
                max_age=days * 24 * 3600,
                path="/",
                secure=COOKIE_SECURE,
                samesite="Lax",
            )
        except Exception:
            pass

def _del_cookie(name: str):
    if hasattr(st, "experimental_delete_cookie"):
        try:
            st.experimental_delete_cookie(name, path="/")
        except Exception:
            pass


def restore_session(sb):
    """Réapplique la session si dispo en mémoire ou cookie."""
    ssess = st.session_state.get("sb_session")
    if ssess:
        try:
            sb.auth.set_session(
                getattr(ssess, "access_token", "") or "",
                getattr(ssess, "refresh_token", "") or "",
            )
        except Exception:
            pass

    try:
        has_user = bool(sb.auth.get_user())
    except Exception:
        has_user = False

    if not has_user:
        rt = _get_cookie(COOKIE_NAME)
        if rt:
            try:
                sb.auth.set_session("", rt)
                sb.auth.refresh_session()
                st.session_state["sb_session"] = sb.auth.get_session()
            except Exception:
                _del_cookie(COOKIE_NAME)

    try:
        sess = sb.auth.get_session()
    except Exception:
        sess = None

    if sess:
        st.session_state["sb_session"] = sess
        exp = int(getattr(sess, "expires_at", 0) or 0)
        if exp and exp < int(time()) + 60:
            try:
                sb.auth.refresh_session()
                st.session_state["sb_session"] = sb.auth.get_session()
            except Exception:
                _del_cookie(COOKIE_NAME)


def require_login(sb, title: str = "Connexion"):
    """Bloque la page tant que l’utilisateur n’est pas connecté."""
    restore_session(sb)

    try:
        gu = sb.auth.get_user()
    except Exception:
        gu = None

    if gu and getattr(gu, "user", None):
        return gu

    st.subheader(title)
    with st.form("login", clear_on_submit=False):
        email    = st.text_input("Email")
        pwd      = st.text_input("Mot de passe", type="password")
        remember = st.checkbox("Se souvenir de moi", value=True)
        go       = st.form_submit_button("Se connecter")

    if go:
        try:
            res = sb.auth.sign_in_with_password({"email": email, "password": pwd})
            st.session_state["sb_session"] = res.session
            if remember and res.session and getattr(res.session, "refresh_token", None):
                _set_cookie(COOKIE_NAME, res.session.refresh_token, COOKIE_DAYS)
            st.rerun()
        except Exception:
            st.error("Échec de connexion. Vérifie tes identifiants.")
            st.stop()

    st.stop()


def logout(sb):
    """Déconnexion propre : Supabase + mémoire + cookie (si dispo)."""
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.pop("sb_session", None)
    st.session_state["user"] = None
    try:
        _del_cookie(COOKIE_NAME)
    except Exception:
        pass

def sidebar_logout_bottom(sb, label: str = "Se déconnecter"):
    """Bouton de déconnexion FIXE tout en bas du sidebar, quelle que soit la page."""
    # Injecter le CSS une seule fois
    if not st.session_state.get("_sidebar_footer_css_v2", False):
        st.markdown(
            """
            <style>
            /* Rendre le conteneur du sidebar positionnable */
            section[data-testid="stSidebar"] { position: relative; }

            /* Bouton fixé en bas du sidebar */
            section[data-testid="stSidebar"] .sidebar-bottom {
                position: fixed;
                bottom: 12px;
                left: 12px;               /* marge intérieure par défaut */
                width: calc(18rem - 24px);/* largeur sidebar ~ 18rem - marges */
                z-index: 1000;
            }

            /* Largeurs adaptatives selon thèmes/tailles */
            @media (max-width: 991px) {
              /* Sidebar en mode overlay sur petits écrans */
              section[data-testid="stSidebar"] .sidebar-bottom {
                  left: 16px;
                  width: calc(100vw - 32px);
              }
            }

            /* Fallback: si la largeur diffère, on tente via variable CSS (si présente) */
            section[data-testid="stSidebar"] {
                --sidebar-w: 18rem; /* valeur par défaut */
            }
            section[data-testid="stSidebar"] .sidebar-bottom.use-var {
                width: calc(var(--sidebar-w) - 24px);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.session_state["_sidebar_footer_css_v2"] = True

    with st.sidebar:
        # Conteneur fixé en bas
        st.markdown('<div class="sidebar-bottom">', unsafe_allow_html=True)
        if st.button(label, use_container_width=True, key="logout_sidebar_fixed"):
            logout(sb)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)



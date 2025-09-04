import streamlit as st
from supabase import create_client
from supabase.lib.client_options import ClientOptions

@st.cache_resource
def get_client():
    """Retourne un client Supabase configuré depuis .streamlit/secrets.toml
    avec persistance de session et refresh automatique du token.
    """
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(
        url,
        key,
        options=ClientOptions(
            persist_session=True,   # garde la session côté client
            auto_refresh_token=True # rafraîchit le token automatiquement
        )
    )

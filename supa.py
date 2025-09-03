import streamlit as st
from supabase import create_client

@st.cache_resource
def get_client():
    """Retourne un client Supabase configuré depuis .streamlit/secrets.toml"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

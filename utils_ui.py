# utils_ui.py
import streamlit as st
from textwrap import dedent
import plotly.express as px

# =========================
# CSS + polices
# =========================
def inject_base_css():
    """
    Identité visuelle nature (verts + tons terre), simple et épurée.
    Ne masque pas le header/menu Streamlit.
    """
    st.markdown(dedent("""
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">
    <style>
      :root{
        /* Palette nature */
        --leaf:#16a34a;         /* vert feuille (primary) */
        --pine:#166534;         /* vert pin (hover/texte accent) */
        --sky:#0ea5e9;          /* bleu ciel (accent soft) */
        --earth:#8b5e34;        /* terre cuivrée (accent secondaire) */
        --sun:#f59e0b;          /* soleil (warning doux) */

        --bg:#fbfcf9;           /* fond ivoire très clair */
        --bg2:#f2f6ef;          /* fond alt / ghost */
        --text:#0b1220;         /* texte */
        --muted:#6b7280;        /* texte atténué */
        --border:#e5e7eb;       /* bordure */
        --shadow:0 10px 30px rgba(0,0,0,.06);

        --radius:18px; --radius-sm:12px; --pad:18px;
        --focus:#a7f3d0;        /* focus vert menthe */
      }

      html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        color: var(--text);
        background: var(--bg);
      }

      /* Titres */
      h1, h2, h3 { letter-spacing:-0.01em; margin-top:0; }
      h1 { font-weight:800; }
      h2 { font-weight:700; }
      h3 { font-weight:600; }

      /* Conteneur principal */
      .appview-container .main .block-container{
        max-width: 1200px;
        padding-top: 1rem;
      }

      /* Cards */
      .card{
        background: #ffffff;
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: var(--pad);
        box-shadow: var(--shadow);
      }
      .card-ghost{
        background: var(--bg2);
        border: 1px dashed var(--border);
        border-radius: var(--radius);
        padding: var(--pad);
      }

      /* Sidebar nature discrète (on garde le header Streamlit) */
      section[data-testid="stSidebar"]{
        background: #ffffff !important;
        border-right: 1px solid var(--border);
      }
      section[data-testid="stSidebar"] .block-container{ padding-top: 1rem; }
      section[data-testid="stSidebar"] a{ color: var(--text); text-decoration: none; }
      section[data-testid="stSidebar"] a:hover{ color: var(--leaf); }

      /* Badge / pill */
      .pill{
        display:inline-flex; gap:8px; align-items:center;
        padding:6px 10px; border-radius:999px; font-size:12px; font-weight:600;
        background:#ecfdf5; color:#065f46; border:1px solid #bbf7d0;
        margin-bottom:6px;
      }

      /* Boutons */
      div.stButton > button, button[kind="primary"]{
        border-radius: 999px !important;
        padding: 10px 18px !important;
        border: 1px solid var(--leaf) !important;
        color: #fff !important;
        background: var(--leaf) !important;
        box-shadow: var(--shadow) !important;
      }
      div.stButton > button:hover, button[kind="primary"]:hover{ background: var(--pine) !important; }

      button[kind="secondary"]{
        border-radius: 999px !important;
        border:1px solid var(--border) !important;
        background:#fff !important; color:var(--text) !important;
      }

      /* Inputs & focus */
      .stTextInput>div>div>input, .stNumberInput input, textarea, select,
      .stTextArea textarea, .stDateInput input, .stTimeInput input{
        border-radius: 12px !important;
        border:1px solid var(--border) !important;
        background: #fff !important;
      }
      .stTextInput>div>div>input:focus, .stNumberInput input:focus, textarea:focus, select:focus,
      .stTextArea textarea:focus, .stDateInput input:focus, .stTimeInput input:focus{
        outline: 3px solid var(--focus) !important;
        border-color: #86efac !important;
      }
      input[type="checkbox"], input[type="radio"]{ accent-color: var(--leaf); }

      /* Onglets */
      .stTabs [data-baseweb="tab-list"]{
        gap:8px; border-bottom:1px solid var(--border);
      }
      .stTabs [data-baseweb="tab"]{
        border:1px solid var(--border); border-bottom:none;
        border-top-left-radius: 12px; border-top-right-radius:12px;
        background:#fff; padding:8px 12px;
      }
      .stTabs [aria-selected="true"]{
        background:#ecfdf5; border-color:#bbf7d0; color:#065f46;
      }

      /* Tableaux */
      .styled-table { width: 100%; border-collapse: collapse; border:1px solid var(--border);
                      border-radius: var(--radius); overflow:hidden; }
      .styled-table th, .styled-table td { padding: 12px 14px; border-bottom:1px solid var(--border); }
      .styled-table tr:hover { background:#fafafa }

      /* DataFrame container */
      div[data-testid="stDataFrame"] { border:1px solid var(--border); border-radius:12px; }

      /* Uploader */
      section[data-testid="stFileUploader"] div[role="button"]{
        border-radius: 14px !important;
        border: 1px dashed var(--border) !important;
        background: var(--bg2) !important;
      }

      /* Charts wrapper */
      .element-container:has(.js-plotly-plot) .stPlotlyChart{
        border:1px solid var(--border); border-radius:12px; padding:6px;
        background:#fff; box-shadow: var(--shadow);
      }

      /* Liens */
      a { color: var(--leaf); }
      a:hover { color: var(--pine); }

      /* Footer custom */
      .app-footer { color:var(--muted); font-size:13px; margin-top:32px; }
    </style>
    """), unsafe_allow_html=True)

# =========================
# Composants
# =========================
def hero(title:str, subtitle:str="", emoji:str="🌿", cta_label:str=None, cta_key:str="hero-cta"):
    st.markdown(f"""
    <div class="card" style="padding:28px;">
      <div class="pill">{emoji} Nature</div>
      <h1 style="margin:6px 0 6px 0; font-size:34px;">{title}</h1>
      <p style="margin:0; color:var(--muted); font-size:15px; max-width:900px;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
    if cta_label:
        st.button(cta_label, key=cta_key)

def section(title:str, subtitle:str=""):
    st.markdown(f"""
    <div style="margin:18px 0 8px 0;">
      <h2 style="margin:0 0 6px 0;">{title}</h2>
      <div style="color:var(--muted)">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def stat_cards(items):
    """
    items = [{"label":"Distance (7j)", "value":"58.3 km", "delta":"+12% vs N-1", "help":"Total semaine courante"}, ...]
    """
    cols = st.columns(len(items))
    for c, it in zip(cols, items):
        with c:
            color = "#16a34a" if str(it.get("delta","")).strip().startswith("+") else "#dc2626"
            st.markdown(f"""
            <div class="card">
              <div style="font-size:13px; color:var(--muted); margin-bottom:6px;">{it.get('label','')}</div>
              <div style="font-size:28px; font-weight:800; line-height:1;">{it.get('value','—')}</div>
              <div style="font-size:12px; color:{color}; margin-top:6px;">
                {it.get('delta','')}
              </div>
            </div>
            """, unsafe_allow_html=True)
            if it.get("help"):
                st.caption(it["help"])

def callout(text:str, tone:str="info"):
    colors = {"info":"#ecfeff", "ok":"#ecfdf5", "warn":"#fff7ed"}
    borders = {"info":"#bae6fd", "ok":"#bbf7d0", "warn":"#fed7aa"}
    st.markdown(f"""
    <div class="card" style="background:{colors.get(tone,'#ecfdf5')}; border-color:{borders.get(tone,'#bbf7d0')}">
      {text}
    </div>
    """, unsafe_allow_html=True)

def app_footer(brand_name:str="TrailTracker", site_url:str=None, email:str=None):
    site = f' · <a href="{site_url}" target="_blank">Site</a>' if site_url else ""
    mail = f' · <a href="mailto:{email}">Contact</a>' if email else ""
    st.markdown(f"""<div class="app-footer">© {brand_name} — Conçu avec 🌿{site}{mail}</div>""", unsafe_allow_html=True)

# =========================
# Plotly : style harmonisé
# =========================
def apply_plotly_theme(fig):
    fig.update_layout(
        title_x=0.02, bargap=0.25,
        plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
                  size=14, color="#0b1220"),
        xaxis=dict(showgrid=False, linecolor="#e5e7eb", tickangle=-30),
        yaxis=dict(gridcolor="#eaf2e8", zeroline=False),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    # Traces : liseré doux
    try:
        fig.update_traces(marker_line_color="#e5e7eb", marker_line_width=1,
                          line=dict(width=2))
    except Exception:
        pass
    return fig

def bar(df, x:str, y:str, title:str=""):
    fig = px.bar(df, x=x, y=y, title=title,
                 color_discrete_sequence=["#16a34a"])
    return apply_plotly_theme(fig)

def line(df, x:str, y:str, title:str=""):
    fig = px.line(df, x=x, y=y, title=title,
                  color_discrete_sequence=["#166534"])
    return apply_plotly_theme(fig)

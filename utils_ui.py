# utils_ui.py
import streamlit as st
from textwrap import dedent
import plotly.express as px

# =========================
# CSS + polices
# =========================
# utils_ui.py
def inject_base_css():
    from textwrap import dedent
    from streamlit.components.v1 import html  # <- composant HTML sûr

    css = dedent("""
    <style>
      :root{
        --brand:#2563eb; --ok:#16a34a; --warn:#f59e0b; --danger:#ef4444;
        --bg:#ffffff; --bg2:#f6f7fb; --text:#0b1220; --muted:#6b7280;
        --border:#e5e7eb; --shadow:0 10px 30px rgba(0,0,0,.06);
        --radius:18px; --radius-sm:12px; --pad:18px; --focus:#93c5fd;
      }

      /* Typo + layout */
      html, body, [class*="css"] { font-family: 'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif; color: var(--text); }
      .appview-container .main .block-container{ max-width:1200px; padding-top:1rem; }

      /* Masquer le chrome Streamlit */
      #MainMenu { visibility:hidden; }
      header { visibility:hidden; }
      footer { visibility:hidden; } /* footer Streamlit natif */

      /* Titres */
      h1, h2, h3 { letter-spacing:-0.01em; }
      h1 { font-weight:800; } h2 { font-weight:700; } h3 { font-weight:600; }

      /* Cards */
      .card{ background:var(--bg); border:1px solid var(--border); border-radius:var(--radius);
             padding:var(--pad); box-shadow:var(--shadow); }
      .card-ghost{ background:var(--bg2); border:1px dashed var(--border); border-radius:var(--radius); padding:var(--pad); }

      /* Sidebar */
      section[data-testid="stSidebar"]{ background:#fff !important; border-right:1px solid var(--border); }
      section[data-testid="stSidebar"] .block-container{ padding-top:1rem; }

      /* Pills */
      .pill{ display:inline-flex; gap:8px; align-items:center; padding:6px 10px; border-radius:999px;
             font-size:12px; font-weight:600; background:#eef2ff; color:#1e3a8a; border:1px solid #dbeafe; margin-bottom:6px; }

      /* Boutons */
      div.stButton > button, button[kind="primary"]{
        border-radius:999px !important; padding:10px 18px !important;
        border:1px solid var(--brand) !important; color:#fff !important; background:var(--brand) !important; box-shadow:var(--shadow) !important;
      }
      div.stButton > button:hover, button[kind="primary"]:hover{ filter:brightness(0.95); }
      button[kind="secondary"]{ border-radius:999px !important; border:1px solid var(--border) !important; background:#fff !important; color:var(--text) !important; }

      /* Inputs & focus */
      .stTextInput>div>div>input, .stNumberInput input, textarea, select,
      .stTextArea textarea, .stDateInput input, .stTimeInput input{
        border-radius:12px !important; border:1px solid var(--border) !important; background:#fff !important;
      }
      .stTextInput>div>div>input:focus, .stNumberInput input:focus, textarea:focus, select:focus,
      .stTextArea textarea:focus, .stDateInput input:focus, .stTimeInput input:focus{
        outline:3px solid var(--focus) !important; border-color:#bfdbfe !important;
      }

      /* Tabs */
      .stTabs [data-baseweb="tab-list"]{ gap:8px; border-bottom:1px solid var(--border); }
      .stTabs [data-baseweb="tab"]{ border:1px solid var(--border); border-bottom:none; border-top-left-radius:12px; border-top-right-radius:12px;
                                    background:#fff; padding:8px 12px; }
      .stTabs [aria-selected="true"]{ background:#eef2ff; border-color:#dbeafe; color:#1e3a8a; }

      /* Tables */
      .styled-table{ width:100%; border-collapse:collapse; border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; }
      .styled-table th, .styled-table td{ padding:12px 14px; border-bottom:1px solid var(--border); }
      .styled-table tr:hover{ background:#fafafa }
      div[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:12px; }

      /* Uploader */
      section[data-testid="stFileUploader"] div[role="button"]{
        border-radius:14px !important; border:1px dashed var(--border) !important; background:var(--bg2) !important;
      }

      /* Charts */
      .element-container:has(.js-plotly-plot) .stPlotlyChart{ border:1px solid var(--border); border-radius:12px; padding:6px; background:#fff; box-shadow:var(--shadow); }

      /* Scrollbar discrète */
      ::-webkit-scrollbar{ width:10px; height:10px; }
      ::-webkit-scrollbar-thumb{ background:#d1d5db; border-radius:999px; }
      ::-webkit-scrollbar-thumb:hover{ background:#9ca3af; }

      /* Footer custom (le tien) */
      .app-footer{ color:var(--muted); font-size:13px; margin-top:32px; }
    </style>
    """)

    # Injection via un iframe vide (hauteur 0) : jamais affiché en clair
    html(css, height=0)
    # Police (Inter)
    html('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap" rel="stylesheet">', height=0)



# =========================
# Composants
# =========================
def hero(title:str, subtitle:str="", emoji:str="✨", cta_label:str=None, cta_key:str="hero-cta"):
    st.markdown(f"""
    <div class="card" style="padding:28px;">
      <div class="pill">{emoji} Nouveauté</div>
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
            st.markdown(f"""
            <div class="card">
              <div style="font-size:13px; color:var(--muted); margin-bottom:6px;">{it.get('label','')}</div>
              <div style="font-size:28px; font-weight:800; line-height:1;">{it.get('value','—')}</div>
              <div style="font-size:12px; color:{'#16a34a' if str(it.get('delta','')).startswith('+') else '#dc2626'}; margin-top:6px;">
                {it.get('delta','')}
              </div>
            </div>
            """, unsafe_allow_html=True)
            if it.get("help"):
                st.caption(it["help"])

def callout(text:str, tone:str="info"):
    colors = {"info":"#eef2ff", "ok":"#ecfdf5", "warn":"#fff7ed"}
    borders = {"info":"#dbeafe", "ok":"#bbf7d0", "warn":"#fed7aa"}
    st.markdown(f"""
    <div class="card" style="background:{colors.get(tone,'#eef2ff')}; border-color:{borders.get(tone,'#dbeafe')}">
      {text}
    </div>
    """, unsafe_allow_html=True)

def app_footer(brand_name:str="Training App", site_url:str=None, email:str=None):
    site = f' · <a href="{site_url}" target="_blank">Site</a>' if site_url else ""
    mail = f' · <a href="mailto:{email}">Contact</a>' if email else ""
    st.markdown(f"""<div class="app-footer">© {brand_name} — Built with ❤️{site}{mail}</div>""", unsafe_allow_html=True)

# =========================
# Plotly : style harmonisé
# =========================
def apply_plotly_theme(fig):
    fig.update_layout(
        title_x=0.02, bargap=0.25, plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
        font=dict(family="Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif", size=14, color="#0b1220"),
        xaxis=dict(showgrid=False, linecolor="#e5e7eb", tickangle=-30),
        yaxis=dict(gridcolor="#f1f5f9", zeroline=False),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    # bords doux sur les barres/markers
    try:
        fig.update_traces(marker_line_color="#e5e7eb", marker_line_width=1)
    except Exception:
        pass
    return fig

def bar(df, x:str, y:str, title:str=""):
    fig = px.bar(df, x=x, y=y, title=title)
    return apply_plotly_theme(fig)

def line(df, x:str, y:str, title:str=""):
    fig = px.line(df, x=x, y=y, title=title)
    return apply_plotly_theme(fig)


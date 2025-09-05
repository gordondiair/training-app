# utils_ui.py
# Thème "nature" minimal + composants réutilisables pour Streamlit

from __future__ import annotations
import streamlit as st
from datetime import date
from typing import Iterable, Optional, List, Dict, Any

# =========================
# 1) CSS global : palette + styles
# =========================
def inject_base_css():
    """
    Injecte le thème 'nature' et les styles de base.
    À appeler une fois en haut de CHAQUE page, idéalement juste après set_page_config().
    """
    st.markdown(
        """
<style>
/* --------- Fonts (Google) --------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

/* --------- Palette Nature (CSS variables) --------- */
:root{
  --bg:           #0b0f0c;         /* très sombre, tire vers la forêt */
  --panel:        #121714;         /* fond des cartes */
  --panel-2:      #0f1411;         /* variantes */
  --ink:          #ecf0ed;         /* texte principal */
  --muted:        #b8c2bc;         /* texte secondaire */
  --brand:        #1f6f43;         /* vert forêt */
  --brand-2:      #2c7a52;         /* hover */
  --accent:       #81b29a;         /* sauge */
  --accent-2:     #a7c4b6;         /* sauge clair */
  --warning:      #d9a441;         /* miel/ocre */
  --danger:       #b85c5c;         /* terre cuite */
  --ok:           #5aa36e;         /* mousse */
  --sky:          #9ecae1;         /* ciel doux (accents discrets) */

  --radius: 16px;
  --radius-lg: 20px;
  --shadow: 0 10px 30px rgba(0,0,0,0.25);
}

/* --------- Reset doux --------- */
html, body, [data-testid="stAppViewContainer"]{
  background: linear-gradient(180deg, #0b0f0c 0%, #0d120e 50%, #0b0f0c 100%);
  color: var(--ink);
  font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

/* Contenu principal: un peu plus large et centré */
.block-container{
  padding-top: 1.2rem;
  max-width: 1100px;
}

/* Titres */
h1,h2,h3,h4{
  letter-spacing: 0.2px;
  color: var(--ink);
}
h1{
  font-family: "Playfair Display", serif;
  font-weight: 700;
}

/* Liens */
a{ color: var(--sky); }
a:hover{ text-decoration: underline; }

/* Cartes utilitaires */
.ui-card{
  background: var(--panel);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 1.1rem 1.2rem;
}
.ui-card.soft{
  background: var(--panel-2);
}
.ui-grid{
  display: grid;
  gap: 14px;
}
.ui-grid.cols-2{ grid-template-columns: repeat(2, minmax(0,1fr)); }
.ui-grid.cols-3{ grid-template-columns: repeat(3, minmax(0,1fr)); }
.ui-grid.cols-4{ grid-template-columns: repeat(4, minmax(0,1fr)); }
@media (max-width: 980px){
  .ui-grid.cols-4{ grid-template-columns: repeat(2, minmax(0,1fr)); }
  .ui-grid.cols-3{ grid-template-columns: repeat(1, minmax(0,1fr)); }
  .ui-grid.cols-2{ grid-template-columns: repeat(1, minmax(0,1fr)); }
}

/* Badges + deltas */
.badge{
  display:inline-flex; align-items:center; gap:.4rem;
  font-size:.78rem; padding:.18rem .5rem; border-radius:999px;
  border:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04);
}
.badge.ok{ color: #d7f2df; border-color: rgba(90,163,110,0.4); background: rgba(90,163,110,0.10); }
.badge.warn{ color: #fff2d6; border-color: rgba(217,164,65,0.4); background: rgba(217,164,65,0.12); }
.badge.danger{ color: #ffe1e1; border-color: rgba(184,92,92,0.4); background: rgba(184,92,92,0.12); }

/* Checkbox : accent vert mousse uniquement dans la zone contenu */
div[data-testid="stAppViewContainer"] input[type="checkbox"]{
  accent-color: var(--ok);
}

/* Boutons Streamlit : on garde le style par défaut pour ne pas 'en faire trop'.
   (Si tu veux un bouton "primaire" custom, vois .ui-btn plus bas) */
.ui-actions{ display:flex; flex-wrap:wrap; gap:.5rem; }
.ui-btn{
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.55rem .9rem; border-radius: 12px;
  border:1px solid rgba(255,255,255,0.08);
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-2) 100%);
  color:white; text-decoration:none; font-weight:600;
  box-shadow: var(--shadow);
}
.ui-btn.ghost{
  background: transparent; color: var(--ink);
  border-color: rgba(255,255,255,0.18);
}
.ui-btn:hover{ filter: brightness(1.02); }

/* Callouts */
.callout{
  border-radius: var(--radius);
  padding: .9rem 1rem;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,0.03);
}
.callout.ok{ border-color: rgba(90,163,110,.45); background: rgba(90,163,110,.10);}
.callout.warn{ border-color: rgba(217,164,65,.45); background: rgba(217,164,65,.10);}
.callout.danger{ border-color: rgba(184,92,92,.45); background: rgba(184,92,92,.10);}
.callout .title{ font-weight:700; margin-bottom:.25rem }

/* Hero */
.hero{
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  padding: 1.1rem 1.2rem;
  border: 1px solid rgba(255,255,255,0.06);
  background:
    radial-gradient(1200px 500px at -20% -20%, rgba(31,111,67,.30), transparent 60%),
    radial-gradient(800px 400px at 120% 0%, rgba(129,178,154,.20), transparent 50%),
    linear-gradient(180deg, rgba(15,20,17,1) 0%, rgba(18,23,20,1) 70%, rgba(15,20,17,1) 100%);
}
.hero h1{
  margin: 0 0 .35rem 0;
}
.hero .subtitle{
  color: var(--muted);
  max-width: 900px;
  line-height: 1.45;
}

/* Footer */
.footer{
  margin-top: 2.2rem; padding: .9rem 0; color: var(--muted); font-size: .9rem;
  border-top: 1px dashed rgba(255,255,255,0.10);
  text-align: center;
}
</style>
        """,
        unsafe_allow_html=True,
    )

# =========================
# 2) Composants UI réutilisables
# =========================
def hero(title: str,
         subtitle: Optional[str] = None,
         icon: Optional[str] = None,
         actions: Optional[Iterable[Dict[str, str]]] = None):
    """
    Bandeau d'en-tête sobre.
    actions: liste de dicts {"label": "...", "href": "...", "variant": "primary|ghost"}
    """
    if actions is None:
        actions = []

    icon_html = f"<span style='margin-right:.5rem'>{icon}</span>" if icon else ""
    btns = ""
    for a in actions:
        variant = "ghost" if a.get("variant", "").lower() == "ghost" else ""
        btns += f"<a class='ui-btn {variant}' href='{a.get('href','#')}'>{a.get('label','Action')}</a>"

    st.markdown(
        f"""
<div class="hero ui-card soft">
  <h1>{icon_html}{title}</h1>
  {f"<div class='subtitle'>{subtitle}</div>" if subtitle else ""}
  {f"<div class='ui-actions' style='margin-top:.8rem'>{btns}</div>" if btns else ""}
</div>
        """,
        unsafe_allow_html=True,
    )

def section(title: str, description: Optional[str] = None, anchor: Optional[str] = None):
    """
    Titre de section uniforme + paragraphe optionnel.
    """
    anchor_attr = f" id='{anchor}'" if anchor else ""
    st.markdown(
        f"""
<div{anchor_attr} style="margin:1.1rem 0 .6rem 0">
  <h2 style="margin:.1rem 0">{title}</h2>
  {f"<div style='color:var(--muted);max-width:900px'>{description}</div>" if description else ""}
</div>
        """,
        unsafe_allow_html=True,
    )

def stat_cards(items: List[Dict[str, Any]], columns: int = 3):
    """
    Affiche des cartes de stats uniformes.
    items: [{"label": "...", "value": "...", "sublabel": "...", "delta": +1/-1/None}]
    """
    cols_class = f"cols-{max(1, min(4, int(columns)))}"
    body = []
    for it in items:
        label = it.get("label","")
        value = it.get("value","—")
        sublabel = it.get("sublabel","")
        delta = it.get("delta", None)
        badge = ""
        if delta is not None:
            if isinstance(delta, (int, float)) and delta != 0:
                cls = "ok" if delta > 0 else "danger"
                sign = "+" if delta > 0 else "−"
                badge = f"<span class='badge {cls}'>{sign}{abs(delta)}</span>"
            elif isinstance(delta, str) and delta:
                badge = f"<span class='badge'>{delta}</span>"

        body.append(f"""
<div class="ui-card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:.6rem">
    <div style="font-size:.86rem;color:var(--muted)">{label}</div>
    {badge}
  </div>
  <div style="font-size:1.6rem;font-weight:700;margin:.25rem 0 .35rem 0">{value}</div>
  <div style="font-size:.88rem;color:var(--muted)">{sublabel}</div>
</div>
        """)

    st.markdown(
        f"<div class='ui-grid {cols_class}'>" + "".join(body) + "</div>",
        unsafe_allow_html=True,
    )

def callout(kind: str, title: str, body: str):
    """
    Encadré d'information.
    kind: "ok" | "warn" | "danger" | autre
    """
    kind = kind if kind in {"ok","warn","danger"} else ""
    st.markdown(
        f"""
<div class="callout {kind}">
  <div class="title">{title}</div>
  <div>{body}</div>
</div>
        """,
        unsafe_allow_html=True,
    )

def app_footer(app_name: str = "Training App"):
    """
    Petit pied de page harmonisé.
    """
    year = date.today().year
    st.markdown(
        f"""
<div class="footer">
  {app_name} • {year} • Design nature 🌿
</div>
        """,
        unsafe_allow_html=True,
    )


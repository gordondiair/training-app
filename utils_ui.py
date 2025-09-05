# utils_ui.py — Nature theme (safe)
from __future__ import annotations
import streamlit as st
from datetime import date
from typing import Iterable, Optional, List, Dict, Any

def inject_base_css():
    """
    Thème discret qui NE modifie PAS les widgets Streamlit.
    À appeler en haut de chaque page, après set_page_config().
    """
    st.markdown("""
<style>
/* Fonts */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

/* Palette "nature" utilisée SEULEMENT par nos composants .ui-* */
:root{
  --ui-ink:        #0f1a14;   /* texte foncé sur fond clair */
  --ui-muted:      #5a6a62;
  --ui-panel:      #f7faf8;   /* cartes claires */
  --ui-border:     rgba(15,26,20,.10);
  --ui-brand:      #1f6f43;   /* vert forêt */
  --ui-brand-2:    #2e7a53;
  --ui-accent:     #81b29a;   /* sauge */
  --ui-ok:         #318061;   /* mousse */
  --ui-warn:       #b5832b;   /* miel/ocre */
  --ui-danger:     #b85c5c;   /* terre cuite */
  --ui-radius:     14px;
  --ui-shadow:     0 8px 26px rgba(15,26,20,.08);
}

/* Ne PAS changer le fond général ni la couleur globale -> on laisse le thème Streamlit gérer. */
.block-container{ max-width: 1100px; }

/* Titres : léger affinement sans forcer une couleur globale */
h1,h2,h3{ letter-spacing:.2px; }
h1{ font-family:"Playfair Display", serif; font-weight:700; }

/* Cartes & grilles (nos composants uniquement) */
.ui-card{
  background: var(--ui-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius);
  box-shadow: var(--ui-shadow);
  padding: 1rem 1.1rem;
  color: var(--ui-ink);
}
.ui-grid{ display:grid; gap:14px; }
.ui-grid.cols-2{ grid-template-columns: repeat(2, minmax(0,1fr)); }
.ui-grid.cols-3{ grid-template-columns: repeat(3, minmax(0,1fr)); }
.ui-grid.cols-4{ grid-template-columns: repeat(4, minmax(0,1fr)); }
@media (max-width: 980px){
  .ui-grid.cols-4{ grid-template-columns: repeat(2, minmax(0,1fr)); }
  .ui-grid.cols-3, .ui-grid.cols-2{ grid-template-columns: 1fr; }
}

/* Badges */
.badge{
  display:inline-flex; align-items:center; gap:.4rem;
  font-size:.78rem; padding:.18rem .5rem; border-radius:999px;
  border:1px solid var(--ui-border); background:#ffffff90; color: var(--ui-ink);
}
.badge.ok{ color:#0f3b2b; background:#dff1e9; border-color:#bfe2d2; }
.badge.warn{ color:#4a3107; background:#fff0cf; border-color:#f3dba1; }
.badge.danger{ color:#4a0e0e; background:#ffe1e1; border-color:#f5c2c2; }

/* Callouts */
.callout{
  border-radius: var(--ui-radius);
  padding: .9rem 1rem;
  border: 1px solid var(--ui-border);
  background: #ffffffcf;
  color: var(--ui-ink);
}
.callout.ok{ border-color:#bfe2d2; background:#e8f5f0; }
.callout.warn{ border-color:#f3dba1; background:#fff7e6; }
.callout.danger{ border-color:#f5c2c2; background:#ffecec; }
.callout .title{ font-weight:700; margin-bottom:.25rem }

/* Hero */
.hero{
  position: relative;
  border-radius: var(--ui-radius);
  overflow: hidden;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--ui-border);
  background:
    radial-gradient(900px 400px at -10% -30%, rgba(31,111,67,.12), transparent 60%),
    radial-gradient(700px 350px at 110% 0%, rgba(129,178,154,.18), transparent 55%),
    #ffffff;
  color: var(--ui-ink);
}
.hero h1{ margin: 0 0 .35rem 0; }
.hero .subtitle{ color: var(--ui-muted); max-width: 900px; line-height: 1.45; }

/* Actions (liens-boutons propres à nos blocs, sans toucher aux st.button) */
.ui-actions{ display:flex; flex-wrap:wrap; gap:.5rem; }
.ui-btn{
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.52rem .9rem; border-radius: 10px;
  border:1px solid var(--ui-border);
  background: linear-gradient(180deg, var(--ui-brand) 0%, var(--ui-brand-2) 100%);
  color:white; text-decoration:none; font-weight:600;
  box-shadow: var(--ui-shadow);
}
.ui-btn.ghost{
  background: #ffffff; color: var(--ui-ink);
}
.ui-btn:hover{ filter: brightness(1.02); text-decoration: none; }

/* Footer */
.footer{
  margin-top: 2rem; padding:.8rem 0; color: var(--ui-muted); font-size:.92rem;
  border-top: 1px dashed var(--ui-border); text-align:center;
}
</style>
    """, unsafe_allow_html=True)

def hero(title: str,
         subtitle: Optional[str] = None,
         icon: Optional[str] = None,
         actions: Optional[Iterable[Dict[str, str]]] = None):
    if actions is None: actions = []
    icon_html = f"<span style='margin-right:.5rem'>{icon}</span>" if icon else ""
    btns = ""
    for a in actions:
        variant = "ghost" if a.get("variant","").lower()=="ghost" else ""
        btns += f"<a class='ui-btn {variant}' href='{a.get('href','#')}'>{a.get('label','Action')}</a>"
    st.markdown(f"""
<div class="hero ui-card" style="background:#fff">
  <h1>{icon_html}{title}</h1>
  {f"<div class='subtitle'>{subtitle}</div>" if subtitle else ""}
  {f"<div class='ui-actions' style='margin-top:.8rem'>{btns}</div>" if btns else ""}
</div>
""", unsafe_allow_html=True)

def section(title: str, description: Optional[str] = None, anchor: Optional[str] = None):
    anchor_attr = f" id='{anchor}'" if anchor else ""
    st.markdown(f"""
<div{anchor_attr} style="margin:1.1rem 0 .6rem 0">
  <h2 style="margin:.1rem 0">{title}</h2>
  {f"<div style='color:var(--ui-muted);max-width:900px'>{description}</div>" if description else ""}
</div>
""", unsafe_allow_html=True)

def stat_cards(items: List[Dict[str, Any]], columns: int = 3):
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
    <div style="font-size:.86rem;color:var(--ui-muted)">{label}</div>
    {badge}
  </div>
  <div style="font-size:1.6rem;font-weight:700;margin:.25rem 0 .35rem 0">{value}</div>
  <div style="font-size:.88rem;color:var(--ui-muted)">{sublabel}</div>
</div>
""")
    st.markdown(f"<div class='ui-grid {cols_class}'>" + "".join(body) + "</div>", unsafe_allow_html=True)

def callout(kind: str, title: str, body: str):
    kind = kind if kind in {"ok","warn","danger"} else ""
    st.markdown(f"""
<div class="callout {kind}">
  <div class="title">{title}</div>
  <div>{body}</div>
</div>
""", unsafe_allow_html=True)

def app_footer(app_name: str = "Training App"):
    year = date.today().year
    st.markdown(f"""
<div class="footer">
  {app_name} • {year} • Design nature 🌿
</div>
""", unsafe_allow_html=True)

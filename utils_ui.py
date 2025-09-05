# utils_ui.py — Nature theme (light/dark) pour Streamlit (safe: n'altère pas les widgets)
from __future__ import annotations
import streamlit as st
from datetime import date
from typing import Iterable, Optional, List, Dict, Any

# =========================
# 1) CSS global (composants .ui-* uniquement)
# =========================
def inject_base_css(mode: str = "light"):
    """
    Injecte un thème 'nature' harmonieux pour nos composants (hero, cards, callouts, etc.).
    NE modifie PAS les widgets Streamlit (inputs, sliders...), donc pas de casse.
    mode: "light" (défaut) ou "dark"
    """
    if mode not in {"light", "dark"}:
        mode = "light"

    # Palettes : naturelles, contrastes doux
    if mode == "light":
        css_vars = """
        --ui-ink:        #0e1a14;    /* texte principal */
        --ui-muted:      #5f6d66;    /* texte secondaire */
        --ui-bg:         #f3f6f4;    /* fond blocs doux */
        --ui-panel:      #ffffff;    /* cartes */
        --ui-border:     rgba(14,26,20,.10);

        --ui-leaf:       #2e7a53;    /* vert feuille */
        --ui-fern:       #3f8f67;    /* vert fougère */
        --ui-sage:       #9db9ab;    /* sauge */
        --ui-moss:       #2c6a4a;    /* mousse foncé (hover) */
        --ui-sky:        #8fbfde;    /* ciel doux (accent) */
        --ui-earth:      #b38b6d;    /* terre claire (accent 2) */

        --ui-ok-bg:      #e5f4ed;
        --ui-ok-br:      #bfe2d2;
        --ui-warn-bg:    #fff6e6;
        --ui-warn-br:    #f3dba1;
        --ui-danger-bg:  #ffecec;
        --ui-danger-br:  #f5c2c2;

        --ui-radius:     14px;
        --ui-shadow:     0 10px 30px rgba(14,26,20,.08);
        """
        hero_layers = """
        radial-gradient(900px 400px at -10% -30%, rgba(46,122,83,.12), transparent 60%),
        radial-gradient(700px 350px at 110% 10%, rgba(157,185,171,.18), transparent 55%),
        var(--ui-panel)
        """
    else:  # dark
        css_vars = """
        --ui-ink:        #e7efe9;    /* texte principal */
        --ui-muted:      #a7b6ad;    /* texte secondaire */
        --ui-bg:         #0d1411;    /* fond blocs doux */
        --ui-panel:      #131b17;    /* cartes */
        --ui-border:     rgba(255,255,255,.06);

        --ui-leaf:       #63c08f;    /* vert feuille lumineux */
        --ui-fern:       #7cd0a2;    /* fougère */
        --ui-sage:       #a6cabb;    /* sauge claire */
        --ui-moss:       #3aa774;    /* hover */
        --ui-sky:        #9ac7ea;    /* ciel doux */
        --ui-earth:      #d1b096;    /* terre sablée */

        --ui-ok-bg:      #143a2a;
        --ui-ok-br:      #256d4e;
        --ui-warn-bg:    #3b2c12;
        --ui-warn-br:    #7a5c27;
        --ui-danger-bg:  #3a1a1a;
        --ui-danger-br:  #7a3a3a;

        --ui-radius:     14px;
        --ui-shadow:     0 14px 34px rgba(0,0,0,.28);
        """
        hero_layers = """
        radial-gradient(900px 400px at -10% -30%, rgba(99,192,143,.14), transparent 60%),
        radial-gradient(700px 350px at 110% 10%, rgba(166,202,187,.12), transparent 55%),
        var(--ui-panel)
        """

    st.markdown(
        f"""
<style>
:root {{
  {css_vars}
}}

/* On laisse le fond/texte global gérés par le thème Streamlit.
   On n'agresse que nos composants .ui-* */
.block-container{{ max-width: 1100px; }}

/* Titres : élégants, sans imposer une couleur globale */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
h1,h2,h3{{ letter-spacing:.2px; }}
h1{{ font-family:"Playfair Display", serif; font-weight:700; }}

/* -- Grille & Cartes -- */
.ui-grid{{ display:grid; gap:16px; }}
.ui-grid.cols-2{{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
.ui-grid.cols-3{{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
.ui-grid.cols-4{{ grid-template-columns: repeat(4, minmax(0,1fr)); }}
@media (max-width: 980px){{
  .ui-grid.cols-4{{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
  .ui-grid.cols-3, .ui-grid.cols-2{{ grid-template-columns: 1fr; }}
}}

.ui-card{{
  background: var(--ui-panel);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius);
  box-shadow: var(--ui-shadow);
  padding: 1rem 1.1rem;
  color: var(--ui-ink);
}}
.ui-card.soft{{ background: var(--ui-bg); }}

/* -- Hero -- */
.hero{{
  position: relative;
  border-radius: var(--ui-radius);
  overflow: hidden;
  padding: 1.1rem 1.2rem;
  border: 1px solid var(--ui-border);
  background: {hero_layers};
  color: var(--ui-ink);
}}
.hero h1{{ margin: 0 0 .35rem 0; }}
.hero .subtitle{{ color: var(--ui-muted); max-width: 900px; line-height: 1.45; }}

/* -- Badges -- */
.badge{{
  display:inline-flex; align-items:center; gap:.4rem;
  font-size:.78rem; padding:.18rem .5rem; border-radius:999px;
  border:1px solid var(--ui-border); background:#ffffff33; color: var(--ui-ink);
}}
/* états */
.badge.ok{{ color:var(--ui-ink); background:var(--ui-ok-bg); border-color:var(--ui-ok-br); }}
.badge.warn{{ color:var(--ui-ink); background:var(--ui-warn-bg); border-color:var(--ui-warn-br); }}
.badge.danger{{ color:var(--ui-ink); background:var(--ui-danger-bg); border-color:var(--ui-danger-br); }}

/* -- Callouts -- */
.callout{{
  border-radius: var(--ui-radius);
  padding: .9rem 1rem;
  border: 1px solid var(--ui-border);
  background: var(--ui-panel);
  color: var(--ui-ink);
}}
.callout.ok{{ background: var(--ui-ok-bg); border-color: var(--ui-ok-br); }}
.callout.warn{{ background: var(--ui-warn-bg); border-color: var(--ui-warn-br); }}
.callout.danger{{ background: var(--ui-danger-bg); border-color: var(--ui-danger-br); }}
.callout .title{{ font-weight:700; margin-bottom:.25rem }}

/* -- Actions (liens-boutons) -- */
.ui-actions{{ display:flex; flex-wrap:wrap; gap:.6rem; }}
.ui-btn{{
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.54rem .92rem; border-radius: 12px;
  border:1px solid var(--ui-border);
  background: linear-gradient(180deg, var(--ui-fern) 0%, var(--ui-leaf) 100%);
  color:white; text-decoration:none; font-weight:600;
  box-shadow: var(--ui-shadow);
}}
.ui-btn.ghost{{
  background: var(--ui-panel); color: var(--ui-ink);
}}
.ui-btn.sky{{ background: linear-gradient(180deg, var(--ui-sky) 0%, #6aacd5 100%); }}
.ui-btn.earth{{ background: linear-gradient(180deg, var(--ui-earth) 0%, #a27d5f 100%); }}
.ui-btn:hover{{ filter: brightness(1.03); text-decoration: none; }}

/* -- Footer -- */
.footer{{
  margin-top: 2rem; padding:.8rem 0; color: var(--ui-muted); font-size:.92rem;
  border-top: 1px dashed var(--ui-border); text-align:center;
}}
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
         actions: Optional[Iterable[Dict[str, str]]] = None,
         soft: bool = True):
    """Bandeau d'en-tête. actions: [{"label": "...", "href": "...", "variant": "ghost|sky|earth"}]"""
    if actions is None:
        actions = []
    icon_html = f"<span style='margin-right:.5rem'>{icon}</span>" if icon else ""
    btns = ""
    for a in actions:
        variant = a.get("variant","").lower()
        variant_cls = "ghost" if variant == "ghost" else ("sky" if variant=="sky" else ("earth" if variant=="earth" else ""))
        btns += f"<a class='ui-btn {variant_cls}' href='{a.get('href','#')}'>{a.get('label','Action')}</a>"
    extra = " soft" if soft else ""
    st.markdown(
        f"""
<div class="hero ui-card{extra}">
  <h1>{icon_html}{title}</h1>
  {f"<div class='subtitle'>{subtitle}</div>" if subtitle else ""}
  {f"<div class='ui-actions' style='margin-top:.8rem'>{btns}</div>" if btns else ""}
</div>
        """,
        unsafe_allow_html=True,
    )

def section(title: str, description: Optional[str] = None, anchor: Optional[str] = None):
    """Titre de section uniforme + paragraphe optionnel."""
    anchor_attr = f" id='{anchor}'" if anchor else ""
    st.markdown(
        f"""
<div{anchor_attr} style="margin:1.1rem 0 .6rem 0">
  <h2 style="margin:.1rem 0">{title}</h2>
  {f"<div style='color:var(--ui-muted);max-width:900px'>{description}</div>" if description else ""}
</div>
        """,
        unsafe_allow_html=True,
    )

def stat_cards(items: List[Dict[str, Any]], columns: int = 3):
    """
    Affiche des cartes de stats.
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
    <div style="font-size:.86rem;color:var(--ui-muted)">{label}</div>
    {badge}
  </div>
  <div style="font-size:1.7rem;font-weight:700;margin:.25rem 0 .35rem 0">{value}</div>
  <div style="font-size:.9rem;color:var(--ui-muted)">{sublabel}</div>
</div>
        """)

    st.markdown(
        f"<div class='ui-grid {cols_class}'>" + "".join(body) + "</div>",
        unsafe_allow_html=True,
    )

def callout(kind: str, title: str, body: str):
    """Encadré d'information. kind: ok | warn | danger | (autre = neutre)"""
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
    """Pied de page harmonisé."""
    year = date.today().year
    st.markdown(
        f"""
<div class="footer">
  {app_name} • {year} • Thème nature 🌿
</div>
        """,
        unsafe_allow_html=True,
    )

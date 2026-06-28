#!/usr/bin/env python3
"""
YAASAP Notes — Générateur automatique de note quotidienne
Repo : YAASAP/yaasap_generator
Déploie dans : YAASAP/dailywatch

Dépendances : pip install requests anthropic yfinance
Secrets GitHub Actions :  NEWSAPI_KEY  +  ANTHROPIC_API_KEY

Modifications vs version originale :
  - Ajout yfinance : cours réels positions + surveillance + indices
  - Template HTML mis à jour : format YAASAP Notes actuel (masthead, QR, newsletter Formspree)
  - Claude Sonnet 4-6 (vs 4-5 précédent)
  - Garde index.html racine : INCHANGÉE (fichier existant toujours protégé)
  - docs/index.html archive : INCHANGÉ
  - Structure note-TIMESTAMP.html + note-du-jour.html : INCHANGÉE
"""

import os, sys, datetime, requests, glob
import anthropic

# yfinance optionnel — pas de crash si absent
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance non installe — donnees marche desactivees")

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
TODAY         = datetime.date.today()
NOW           = datetime.datetime.now()
DATE_STR      = TODAY.strftime("%d %B %Y")
NUM           = TODAY.strftime("%d/%m/%Y")
TIMESTAMP     = NOW.strftime("%Y-%m-%d_%H%M")
FORMSPREE_ID  = "meewwqep"

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
ROOT_DIR = os.environ.get(
    "GITHUB_WORKSPACE",
    os.path.join(os.path.dirname(__file__), "..")
)

# Vos positions personnelles
POSITIONS = {
    "SPCX": {"name": "SpaceX",   "pru": 174.44, "qty": 41,  "currency": "USD"},
    "TTWO": {"name": "Take-Two", "pru": 195.06, "qty": 6,   "currency": "USD"},
    "SQM":  {"name": "SQM ADR",  "pru": 73.21,  "qty": 12,  "currency": "USD"},
    "PFE":  {"name": "Pfizer",   "pru": 23.49,  "qty": 7,   "currency": "USD"},
}

# Valeurs sous surveillance
WATCHLIST = {
    "ARGX":  {"name": "argenx",   "currency": "USD"},
    "XYZ":   {"name": "Block Inc", "currency": "USD"},
    "MC.PA": {"name": "LVMH",     "currency": "EUR"},
    "VTRS":  {"name": "Viatris",  "currency": "USD"},
    "NVDA":  {"name": "Nvidia",   "currency": "USD"},
}

# Indices & commodites
INDICES = {
    "^GSPC":     {"name": "S&P 500",       "currency": "USD"},
    "^FCHI":     {"name": "CAC 40",        "currency": "EUR"},
    "^STOXX50E": {"name": "Euro Stoxx 50", "currency": "EUR"},
    "GC=F":      {"name": "Or ($/oz)",     "currency": "USD"},
    "CL=F":      {"name": "Brent ($/bbl)", "currency": "USD"},
    "BTC-USD":   {"name": "Bitcoin",       "currency": "USD"},
}

# Notes sectorielles du repo dailywatch
ANALYSES = [
    ("yaasap_starpipe.html",        "SpaceX Starpipe — Gazoduc 13 km Texas · Primeur",         "Flash Breaking · 25 juin 2026"),
    ("yaasap_lvmh.html",            "LVMH — -26% YTD · PER 23x · Accumulation progressive",    "Analyse · Juin 2026"),
    ("yaasap_viatris.html",         "Viatris VTRS — These valide · Attendre 12-13$",            "Analyse · Juin 2026"),
    ("yaasap_block_sq.html",        "Block Inc (XYZ) — Square · Cash App · Stablecoin",        "Analyse · Juin 2026"),
    ("yaasap_ttwo.html",            "Take-Two TTWO — GTA VI 19 nov. 2026 · BofA 320$",         "Analyse · Juin 2026"),
    ("yaasap_semi_smallcap.html",   "Comparables Silvaco SVCO — PLAB · PDFS · FORM · COHU",    "Selection · Juin 2026"),
    ("yaasap_global_souscote.html", "Tous marches v5 — PFE · BABA · GM · Comcast",             "Selection · Juin 2026"),
    ("yaasap_volatilite_v4.html",   "Minieres or — NEM · Barrick · FCF 6,72 Md$ record",       "Selection v4 · Juin 2026"),
    ("yaasap_europe_souscotee.html","Europe sous-cotee — Stellantis · EVS · Vivendi",           "Selection · Juin 2026"),
    ("yaasap_baba_v2.html",         "Alibaba (BABA) — 40 analystes Buy · Upside 69%",           "Analyse · Juin 2026"),
    ("yaasap_spatial_live.html",    "Secteur Spatial — SpaceX IPO · RKLB · ASTS",               "Analyse · Juin 2026"),
    ("yaasap_oil_gas.html",         "Oil & Gas — TotalEnergies · Majors petrolieres",            "Analyse · Mai 2026"),
    ("yaasap_ecosysteme_ia.html",   "Ecosysteme IA — LLMs · GPU · Stockage",                    "Analyse · Avr. 2026"),
    ("yaasap_value.html",           "Actions sous-cotees — PER bas · Fondamentaux solides",     "Strategie · Avr. 2026"),
    ("yaasap_gta6_light.html",      "GTA VI — Cartographie boursiere",                          "Analyse · Mars 2026"),
]


# =============================================================
# 1. DONNEES DE MARCHE (yfinance)
# =============================================================
def fetch_market_data():
    if not HAS_YF:
        return {"positions": {}, "watchlist": {}, "indices": {}}
    result = {"positions": {}, "watchlist": {}, "indices": {}}

    def get_quote(ticker):
        try:
            t    = yf.Ticker(ticker)
            info = t.fast_info
            p    = float(info.last_price) if info.last_price else None
            pc   = float(info.previous_close) if info.previous_close else None
            chg  = round(p - pc, 2) if p and pc else None
            chgp = round((chg / pc) * 100, 2) if chg and pc else None
            return {"price": round(p, 2) if p else None, "change": chg, "change_p": chgp}
        except Exception as e:
            print(f"  ERR {ticker}: {e}")
            return {"price": None, "change": None, "change_p": None}

    print("Recuperation des cours...")
    for ticker, meta in POSITIONS.items():
        q = get_quote(ticker)
        result["positions"][ticker] = {**meta, **q}
        print(f"  {ticker}: {q['price']}")
    for ticker, meta in WATCHLIST.items():
        if ticker not in POSITIONS:
            q = get_quote(ticker)
            result["watchlist"][ticker] = {**meta, **q}
            print(f"  {ticker}: {q['price']}")
    for ticker, meta in INDICES.items():
        q = get_quote(ticker)
        result["indices"][ticker] = {**meta, **q}
        print(f"  {ticker}: {q['price']}")
    return result


def _chg_span(chgp):
    if chgp is None:
        return "<span>-</span>"
    col = "#1e5c32" if chgp >= 0 else "#b01c1c"
    arr = "▲" if chgp >= 0 else "▼"
    return f'<span style="color:{col};font-weight:700;">{arr} {abs(chgp):.2f}%</span>'


def build_portfolio_html(market):
    rows = ""
    total_val = total_pnl = 0
    for ticker, d in market["positions"].items():
        p   = d.get("price")
        pru = d.get("pru")
        qty = d.get("qty", 0)
        chgp = d.get("change_p")
        ps   = f"${p:.2f}" if p else "-"
        if p and pru:
            pnl = (p - pru) * qty
            total_val += p * qty
            total_pnl += pnl
            pc  = "#1e5c32" if pnl >= 0 else "#b01c1c"
            sg  = "+" if pnl >= 0 else ""
            pnl_s = f'<span style="color:{pc};font-weight:700;">{sg}${pnl:,.0f}</span>'
            pru_s = f"${pru:.2f} x {qty}"
        else:
            pnl_s = pru_s = "-"
        rows += (f"<tr><td style='font-family:var(--mono);font-weight:700'>{ticker}</td>"
                 f"<td>{d['name']}</td>"
                 f"<td style='font-family:var(--mono)'>{ps}</td>"
                 f"<td>{_chg_span(chgp)}</td>"
                 f"<td style='font-family:var(--mono);font-size:11px;color:var(--ink3)'>{pru_s}</td>"
                 f"<td>{pnl_s}</td></tr>")
    pc   = "#1e5c32" if total_pnl >= 0 else "#b01c1c"
    sg   = "+" if total_pnl >= 0 else ""
    return (
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">'
        f'<span style="font-size:8px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-family:var(--sans);">Portefeuille · {DATE_STR}</span>'
        f'<span style="font-family:var(--mono);font-size:12px;">'
        f'${total_val:,.0f} <span style="color:{pc};font-weight:700">{sg}${total_pnl:,.0f}</span></span></div>'
        f'<div class="table-wrap"><table>'
        f'<thead><tr><th>Ticker</th><th>Valeur</th><th>Cours</th>'
        f'<th>Jour</th><th>PRU x Qte</th><th>P&L latent</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )


def build_indices_html(market):
    rows = ""
    for ticker, d in {**market["watchlist"], **market["indices"]}.items():
        p    = d.get("price")
        chgp = d.get("change_p")
        sym  = "€" if d.get("currency") == "EUR" else "$"
        ps   = f"{sym}{p:,.2f}" if p else "-"
        rows += (f"<tr><td style='font-weight:700'>{d['name']}</td>"
                 f"<td style='font-family:var(--mono)'>{ps}</td>"
                 f"<td>{_chg_span(chgp)}</td></tr>")
    return (
        f'<div style="margin-top:12px;">'
        f'<div style="font-size:8px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3);font-family:var(--sans);margin-bottom:6px;">Indices &amp; Surveillance</div>'
        f'<div class="table-wrap"><table>'
        f'<thead><tr><th>Valeur</th><th>Cours</th><th>Variation</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div></div>'
    )


def build_ticker_market(market):
    items = []
    for ticker, d in {**market["positions"], **market["indices"]}.items():
        p    = d.get("price")
        chgp = d.get("change_p")
        if not p:
            continue
        sym = "€" if d.get("currency") == "EUR" else "$"
        col = "#1e5c32" if chgp and chgp >= 0 else "#b01c1c"
        arr = "▲" if chgp and chgp >= 0 else "▼"
        items.append(
            f'<div class="kk"><div class="kk-l">{ticker}</div>'
            f'<div class="kk-v" style="color:{col};">'
            f'{sym}{p:.2f} {arr} {abs(chgp):.1f}%</div></div>'
            if chgp else
            f'<div class="kk"><div class="kk-l">{ticker}</div>'
            f'<div class="kk-v">{sym}{p:.2f}</div></div>'
        )
    return "".join(items)


def format_market_for_claude(market):
    lines = ["\n=== DONNEES DE MARCHE DU JOUR ==="]
    total_val = total_pnl = 0
    lines.append("PORTEFEUILLE :")
    for ticker, d in market["positions"].items():
        p = d.get("price"); pru = d.get("pru"); qty = d.get("qty", 0)
        chgp = d.get("change_p")
        if p and pru:
            pnl = (p - pru) * qty
            total_val += p * qty; total_pnl += pnl
            sg = "+" if pnl >= 0 else ""
            lines.append(f"  {ticker}: ${p:.2f} ({chgp:+.1f}% jour) | PRU ${pru:.2f} x {qty} | P&L {sg}${pnl:.0f}")
        else:
            lines.append(f"  {ticker}: indisponible")
    sg = "+" if total_pnl >= 0 else ""
    lines.append(f"  -> Total: ${total_val:,.0f} | P&L {sg}${total_pnl:,.0f}")
    lines.append("INDICES :")
    for ticker, d in market["indices"].items():
        p = d.get("price"); chgp = d.get("change_p")
        if p:
            sym = "€" if d.get("currency") == "EUR" else "$"
            lines.append(f"  {d['name']}: {sym}{p:,.0f} ({chgp:+.1f}%)")
    return "\n".join(lines)


# =============================================================
# 2. FETCH NEWS
# =============================================================
def fetch_news():
    articles = []
    queries  = [
        "financial markets stocks earnings results",
        "central banks interest rates inflation Fed ECB",
        "mergers acquisitions IPO deals 2026",
        "geopolitics trade war tariffs sanctions",
        "SpaceX Starship launch satellite",
    ]
    for q in queries:
        try:
            r = requests.get("https://newsapi.org/v2/everything", params={
                "q": q, "sortBy": "publishedAt", "pageSize": 5,
                "from": (TODAY - datetime.timedelta(days=2)).isoformat(),
                "apiKey": NEWSAPI_KEY
            }, timeout=10)
            data = r.json()
            if data.get("status") == "ok":
                articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"ERR fetch '{q}': {e}")
    seen, unique = set(), []
    for a in articles:
        u = a.get("url", "")
        if u and u not in seen:
            seen.add(u); unique.append(a)
    print(f"{len(unique)} articles recuperes")
    return unique


def format_articles(articles):
    lines = []
    for i, a in enumerate(articles[:25], 1):
        src  = a.get("source", {}).get("name", "?")
        titl = a.get("title", "")
        desc = (a.get("description", "") or "")[:150]
        date = a.get("publishedAt", "")[:10]
        url  = a.get("url", "")
        img  = a.get("urlToImage", "") or ""
        lines.append(f"{i}. [{src} {date}] {titl}\n   {desc}\n   URL: {url}\n   IMG: {img}")
    return "\n\n".join(lines)


def get_top_images(articles, n=2):
    imgs = []
    for a in articles:
        img = a.get("urlToImage", "")
        if img and img.startswith("http") and len(imgs) < n:
            imgs.append({"url": img, "source": a.get("source", {}).get("name", ""),
                         "title": a.get("title", "")[:60]})
    return imgs


def get_sources(articles):
    seen, sources = set(), []
    for a in articles[:20]:
        src = a.get("source", {}).get("name", "")
        url = a.get("url", "")
        if src and src not in seen:
            seen.add(src); sources.append({"name": src, "url": url})
    return sources[:8]


# =============================================================
# 3. TEMPLATE HTML — FORMAT YAASAP NOTES ACTUEL
# =============================================================
TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="theme-color" content="#0a0c0f">
<title>YAASAP Notes - DATE_PH</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600;700;900&family=Source+Code+Pro:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{
  --void:#0a0c0f;--void2:#111418;--void3:#181c22;--wire:#252a32;
  --paper:#f5f2ec;--paper2:#ece8df;
  --ink:#0d0e10;--ink3:#6a6560;--ink4:#9a948e;
  --accent:#c8290a;--green:#1a8a3a;--amber:#d4880a;--gold:#c8902a;--blue:#1a5c9a;
  --serif:'Libre Baskerville',Georgia,serif;
  --sans:'Source Sans 3','Helvetica Neue',Arial,sans-serif;
  --mono:'Source Code Pro','Courier New',monospace;
}
html,body{background:var(--void);font-family:var(--sans);color:var(--paper);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh;}

/* ── BARRE URGENCE ── */
.urgency{background:var(--accent);padding:4px 20px;display:flex;align-items:center;justify-content:space-between;gap:10px;}
.urg-left{display:flex;align-items:center;gap:8px;}
.urg-dot{width:6px;height:6px;background:#fff;border-radius:50%;animation:blink .9s ease-in-out infinite;flex-shrink:0;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.2;}}
.urg-txt{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#fff;}
.urg-time{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.65);}

/* ── MASTHEAD ── */
.masthead{background:var(--void);border-bottom:1px solid var(--wire);padding:12px 22px 10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:100;box-shadow:0 2px 12px rgba(0,0,0,.5);}
.pub-name{font-family:var(--serif);font-size:22px;font-weight:700;letter-spacing:-.02em;color:var(--paper);line-height:1;}
.pub-name em{font-style:italic;color:var(--accent);}
.pub-tagline{font-family:var(--mono);font-size:7px;color:rgba(255,255,255,.25);letter-spacing:.14em;text-transform:uppercase;margin-top:2px;}
.mast-center{text-align:center;flex:1;}
.mast-badge{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--wire);padding:3px 10px;border-radius:2px;}
.mast-badge-dot{width:5px;height:5px;background:var(--green);border-radius:50%;animation:blink .9s infinite;}
.mast-badge-txt{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.38);letter-spacing:.1em;text-transform:uppercase;}
.mast-right{display:flex;align-items:center;gap:10px;}
.mast-date{font-family:var(--serif);font-size:10px;color:rgba(255,255,255,.35);font-style:italic;}
.mast-qr-box{background:var(--paper);padding:4px;border-radius:2px;line-height:0;}
.mast-qr-lbl{font-family:var(--mono);font-size:6px;color:rgba(255,255,255,.2);letter-spacing:.06em;text-transform:uppercase;margin-top:2px;text-align:center;}

/* ── TICKER ── */
.ticker-wrap{background:var(--void2);border-bottom:1px solid var(--wire);overflow:hidden;white-space:nowrap;padding:5px 0;}
.ticker-inner{display:inline-flex;animation:scroll 35s linear infinite;}
@keyframes scroll{from{transform:translateX(0);}to{transform:translateX(-50%);}}
.tk{font-family:var(--mono);font-size:10px;color:rgba(255,255,255,.5);padding:0 22px;}
.tk.hot{color:var(--accent);font-weight:700;}
.tk-sep{color:var(--wire);}

/* ── HERO ── */
.hero{position:relative;width:100%;overflow:hidden;background:var(--void2);}
.hero img{width:100%;height:240px;object-fit:cover;display:block;filter:brightness(.55) saturate(.8);}
.hero-overlay{position:absolute;inset:0;background:linear-gradient(135deg,rgba(10,12,15,.8) 0%,transparent 60%,rgba(10,12,15,.4) 100%);}
.hero-content{position:absolute;bottom:0;left:0;right:0;padding:20px 22px;}
.hero-eyebrow{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--gold);margin-bottom:6px;}
.hero-title{font-family:var(--serif);font-size:clamp(18px,4vw,26px);font-weight:700;color:#fff;line-height:1.15;max-width:520px;margin-bottom:4px;}
.hero-caption{font-size:9.5px;color:rgba(255,255,255,.4);font-style:italic;font-family:var(--sans);}
@media(min-width:640px){.hero img{height:300px;}}

/* ── KPI STRIP ── */
.kpi-strip{display:grid;grid-template-columns:repeat(5,1fr);background:var(--void2);border-bottom:1px solid var(--wire);}
.kpi{padding:11px 0 11px 16px;border-right:1px solid var(--wire);}
.kpi:last-child{border-right:none;}
.kpi-v{font-family:var(--mono);font-size:16px;font-weight:700;color:var(--paper);line-height:1;display:block;}
.kpi-v.up{color:#4ade80;}.kpi-v.dn{color:#f87171;}.kpi-v.am{color:#fbbf24;}
.kpi-l{font-family:var(--mono);font-size:7.5px;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.28);margin-top:3px;display:block;}

/* ── SCROLL KICKER ── */
.kicker{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--void3);border-bottom:1px solid var(--wire);}
.kicker::-webkit-scrollbar{display:none;}
.kicker-inner{display:flex;padding:0 16px;min-width:max-content;}
.kk{padding:8px 16px;border-right:1px solid var(--wire);flex-shrink:0;}
.kk:last-child{border-right:none;}
.kk-l{font-family:var(--mono);font-size:7.5px;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.28);margin-bottom:2px;}
.kk-v{font-family:var(--mono);font-size:13px;font-weight:600;color:var(--paper);line-height:1;}
.kk-n{font-size:9px;color:rgba(255,255,255,.35);font-style:italic;margin-top:1px;font-family:var(--sans);}

/* ── LAYOUT PRINCIPAL ── */
.layout{max-width:800px;margin:0 auto;padding:24px 20px 56px;}

/* ── SECTION RULE ── */
.sec{display:flex;align-items:center;gap:8px;margin:28px 0 14px;}
.sec-line{flex:1;height:1px;background:var(--wire);}
.sec-dot{width:4px;height:4px;border-radius:50%;background:var(--accent);flex-shrink:0;}
.sec-t{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:rgba(255,255,255,.4);white-space:nowrap;}

/* ── MARCHÉ — GRILLE ── */
.mkt-grid{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--wire);border-radius:3px;overflow:hidden;margin-bottom:16px;}
.mkt-cell{background:var(--void2);padding:12px 14px;}
.mkt-label{font-family:var(--mono);font-size:7.5px;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.28);margin-bottom:4px;}
.mkt-val{font-family:var(--mono);font-size:20px;font-weight:700;color:var(--paper);line-height:1;}
.mkt-val.up{color:#4ade80;}.mkt-val.dn{color:#f87171;}
.mkt-sub{font-size:11px;color:rgba(255,255,255,.35);margin-top:2px;font-family:var(--sans);}

/* ── TABLES ── */
.table-wrap{background:var(--void2);border:1px solid var(--wire);border-radius:3px;overflow:hidden;margin-bottom:16px;}
.table-wrap table{width:100%;border-collapse:collapse;}
.table-wrap th{font-family:var(--mono);font-size:7.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.28);padding:8px 12px;text-align:left;border-bottom:1px solid var(--wire);background:var(--void3);}
.table-wrap td{font-size:12px;padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.04);color:rgba(255,255,255,.75);vertical-align:middle;font-family:var(--sans);}
.table-wrap tr:last-child td{border-bottom:none;}
.table-wrap tr:hover td{background:rgba(255,255,255,.02);}
.badge-up{background:rgba(26,138,58,.2);color:#4ade80;font-size:9px;font-weight:700;padding:2px 7px;border-radius:2px;border:1px solid rgba(26,138,58,.3);}
.badge-dn{background:rgba(200,41,10,.2);color:#f87171;font-size:9px;font-weight:700;padding:2px 7px;border-radius:2px;border:1px solid rgba(200,41,10,.3);}
.badge-am{background:rgba(212,136,10,.2);color:#fbbf24;font-size:9px;font-weight:700;padding:2px 7px;border-radius:2px;border:1px solid rgba(212,136,10,.3);}

/* ── SIGNAL ── */
.signal{background:var(--void2);border:1px solid var(--wire);border-left:3px solid var(--accent);border-radius:0 3px 3px 0;padding:18px 20px;margin-bottom:14px;}
.signal-label{font-family:var(--mono);font-size:8.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:8px;}
.signal-headline{font-family:var(--serif);font-size:20px;font-weight:700;line-height:1.2;margin-bottom:8px;color:var(--paper);}
.signal-deck{font-family:var(--serif);font-size:13px;font-style:italic;color:rgba(255,255,255,.45);line-height:1.5;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid var(--wire);}
.signal-body{font-size:13.5px;color:rgba(255,255,255,.7);line-height:1.65;font-family:var(--sans);}
.signal-body strong{font-weight:700;color:var(--paper);}
.signal-body p{margin-bottom:8px;}

/* ── PULL QUOTE ── */
.pull{border-left:3px solid var(--gold);background:rgba(200,144,42,.06);padding:12px 16px;margin:14px 0;border-radius:0 2px 2px 0;}
.pull-t{font-family:var(--serif);font-size:14px;font-style:italic;line-height:1.5;color:rgba(255,255,255,.85);}
.pull-a{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.3);letter-spacing:.08em;text-transform:uppercase;margin-top:5px;}

/* ── ARTICLES — CARTES COLORÉES ── */
.arts-grid{display:grid;grid-template-columns:1fr;gap:10px;margin-bottom:16px;}
.art{background:var(--void2);border:1px solid var(--wire);border-top:2px solid;border-radius:3px;padding:14px 16px;}
.art:nth-child(1){border-top-color:var(--accent);}
.art:nth-child(2){border-top-color:var(--blue);}
.art:nth-child(3){border-top-color:var(--gold);}
.art-sector{font-family:var(--mono);font-size:8px;letter-spacing:.14em;text-transform:uppercase;font-weight:700;margin-bottom:5px;color:rgba(255,255,255,.4);}
.art-h{font-family:var(--serif);font-size:15px;font-weight:700;color:var(--paper);line-height:1.25;margin-bottom:5px;}
.art-b{font-size:12.5px;color:rgba(255,255,255,.6);line-height:1.55;font-family:var(--sans);}
.art-b strong{color:var(--paper);font-weight:700;}

/* ── HERO 2 ── */
.hero2{position:relative;width:100%;height:140px;overflow:hidden;border-radius:3px;margin:16px 0;border:1px solid var(--wire);}
.hero2 img{width:100%;height:140px;object-fit:cover;filter:brightness(.6);}
.hero2-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(10,12,15,.7);padding:7px 13px;font-size:9.5px;color:rgba(255,255,255,.6);font-style:italic;font-family:var(--sans);}

/* ── VERDICT ── */
.verdict{background:var(--accent);border-radius:3px;padding:18px 20px;margin:22px 0;position:relative;overflow:hidden;}
.verdict::before{content:'VERDICT';position:absolute;right:-10px;top:50%;transform:translateY(-50%) rotate(90deg);font-family:var(--mono);font-size:72px;letter-spacing:.1em;color:rgba(0,0,0,.15);pointer-events:none;white-space:nowrap;}
.v-tag{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.6);margin-bottom:8px;display:block;}
.v-t{font-family:var(--serif);font-size:14px;color:#fff;font-style:italic;line-height:1.6;}
.v-t strong{font-style:normal;font-weight:800;color:#fff;}

/* ── SOURCES ── */
.sources{background:var(--void3);border:1px solid var(--wire);border-radius:3px;padding:12px 16px;margin:14px 0;}
.sources-label{font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.3);margin-bottom:8px;}
.src-list{display:flex;flex-wrap:wrap;gap:5px;}
.src-pill{font-size:10px;color:rgba(255,255,255,.5);background:var(--void2);border:1px solid var(--wire);border-radius:20px;padding:3px 10px;text-decoration:none;font-style:italic;font-family:var(--sans);transition:border-color .15s;}
.src-pill:hover{border-color:var(--accent);color:var(--paper);}

/* ── NEWSLETTER ── */
.nl-mini{background:var(--void2);border:1px solid var(--wire);border-top:2px solid var(--accent);border-radius:3px;padding:16px 18px;margin-top:24px;}
.nl-mini-title{font-family:var(--serif);font-size:14px;font-weight:700;color:var(--paper);margin-bottom:4px;}
.nl-mini-sub{font-size:11px;color:rgba(255,255,255,.35);margin-bottom:10px;font-family:var(--sans);}
.nl-mini-row{display:flex;gap:6px;}
.nl-mini-input{flex:1;height:40px;padding:0 12px;border:1px solid var(--wire);background:var(--void);border-radius:3px;font-family:var(--sans);font-size:13px;color:var(--paper);outline:none;transition:border-color .15s;}
.nl-mini-input::placeholder{color:rgba(255,255,255,.22);}
.nl-mini-input:focus{border-color:var(--accent);}
.nl-mini-btn{height:40px;padding:0 16px;background:var(--accent);border:none;border-radius:3px;color:#fff;font-family:var(--mono);font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;white-space:nowrap;transition:background .15s;}
.nl-mini-btn:hover{background:#a01e00;}
.nl-mini-note{font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.2);margin-top:6px;letter-spacing:.04em;}
#nlm-ok{display:none;font-family:var(--mono);font-size:11px;font-weight:700;color:#4ade80;margin-top:6px;letter-spacing:.06em;}

/* ── FOOTER ── */
footer{border-top:1px solid var(--wire);background:var(--void2);padding:16px 22px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}
.foot-brand{font-family:var(--serif);font-size:15px;font-weight:700;color:rgba(255,255,255,.4);}
.foot-brand em{font-style:italic;color:var(--accent);}
.foot-note{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.2);letter-spacing:.04em;line-height:1.6;}
.foot-nav{display:flex;gap:14px;flex-wrap:wrap;}
.foot-nav a{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:rgba(255,255,255,.28);text-decoration:none;transition:color .12s;}
.foot-nav a:hover{color:var(--accent);}

@media(max-width:480px){
  .kpi-strip{grid-template-columns:repeat(3,1fr);}
  .mkt-grid{grid-template-columns:1fr;}
  .nl-mini-row{flex-direction:column;}
  footer{flex-direction:column;text-align:center;}
}
</style>
</head>
<body>

<!-- BARRE URGENCE -->
<div class="urgency">
  <div class="urg-left">
    <div class="urg-dot"></div>
    <span class="urg-txt">Bulletin automatique YAASAP Notes</span>
  </div>
  <span class="urg-time" id="urgTime">DATE_PH · 07h00</span>
</div>

<!-- MASTHEAD -->
<div class="masthead">
  <div>
    <div class="pub-name">YAASAP <em>Notes</em></div>
    <div class="pub-tagline">Bulletin quotidien · Marches · Analyse · Positions</div>
  </div>
  <div class="mast-center">
    <div class="mast-badge">
      <div class="mast-badge-dot"></div>
      <span class="mast-badge-txt">Live · DATE_PH</span>
    </div>
  </div>
  <div class="mast-right">
    <div class="mast-date" id="liveDate">DATE_PH</div>
    <div>
      <div class="mast-qr-box"><div id="qr-mast" style="line-height:0;"></div></div>
      <div class="mast-qr-lbl">dailywatch</div>
    </div>
  </div>
</div>

<!-- TICKER DEFILANT -->
<div class="ticker-wrap">
  <div class="ticker-inner">
    <span class="tk hot">/// YAASAP NOTES ///</span>
    MARKET_TICKER_PH
    <span class="tk-sep"> &middot; </span>
    KICKER_NEWS_PH
    <span class="tk hot">/// YAASAP NOTES ///</span>
    MARKET_TICKER_PH
    <span class="tk-sep"> &middot; </span>
    KICKER_NEWS_PH
  </div>
</div>

<!-- HERO -->
HERO1_PH

<!-- LAYOUT -->
<div class="layout">

  <!-- MARCHE DU JOUR -->
  <div class="sec"><div class="sec-line"></div><div class="sec-dot"></div><span class="sec-t">Marche du jour · NOTE_NUM_PH</span><div class="sec-dot"></div><div class="sec-line"></div></div>
  PORTFOLIO_PH
  INDICES_PH

  <!-- SIGNAL -->
  <div class="sec"><div class="sec-line"></div><div class="sec-dot"></div><span class="sec-t">Signal du jour</span><div class="sec-dot"></div><div class="sec-line"></div></div>
  SIGNAL_PH

  <!-- ANALYSES -->
  <div class="sec"><div class="sec-line"></div><div class="sec-dot"></div><span class="sec-t">Analyses sectorielles</span><div class="sec-dot"></div><div class="sec-line"></div></div>
  <div class="arts-grid">ARTICLES_PH</div>
  HERO2_PH

  <!-- VERDICT -->
  <div class="verdict"><span class="v-tag">Verdict YAASAP · DATE_PH</span><div class="v-t">VERDICT_PH</div></div>

  <!-- SOURCES -->
  SOURCES_PH

  <!-- NEWSLETTER -->
  <div class="nl-mini">
    <div class="nl-mini-title">Recevoir ce bulletin chaque matin</div>
    <div class="nl-mini-sub">Gratuit · Donnees marche en temps reel + analyse editoriale · Desabonnement en 1 clic</div>
    <div class="nl-mini-row">
      <input class="nl-mini-input" type="email" id="nlm-email" placeholder="votre@email.com" autocomplete="email">
      <button class="nl-mini-btn" onclick="nlmSubmit()">S'abonner</button>
    </div>
    <div id="nlm-ok">INSCRIT</div>
    <div class="nl-mini-note">RGPD · Formspree · yaasap.github.io/dailywatch</div>
  </div>

</div><!-- /layout -->

<footer>
  <div class="foot-brand">YAASAP <em>Notes</em></div>
  <div class="foot-note">Par Yacine AOUABED &middot; NOTE_NUM_PH &middot; <span id="liveDateFooter">DATE_PH</span><br>Analyse informative uniquement &mdash; Ne constitue pas un conseil en investissement</div>
  <nav class="foot-nav">
    <a href="../index.html">Accueil</a>
    <a href="index.html">Archives</a>
    <a href="../yaasap_starpipe.html">Starpipe</a>
    <a href="../yaasap_lvmh.html">LVMH</a>
    <a href="../yaasap_spcx_position.html">SPCX</a>
  </nav>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
(function(){
  var d=new Date();
  var opts={weekday:'long',year:'numeric',month:'long',day:'numeric'};
  var s=d.toLocaleDateString('fr-FR',opts);
  ['liveDate','liveDateFooter','urgTime'].forEach(function(id){
    var el=document.getElementById(id);if(el)el.textContent=id==='urgTime'?s+' · 07h00':s;
  });
  (function tryQR(){
    var el=document.getElementById('qr-mast');
    if(!el||typeof QRCode==='undefined'){setTimeout(tryQR,80);return;}
    new QRCode(el,{text:'https://yaasap.github.io/dailywatch/index.html',
      width:48,height:48,colorDark:'#0a0c0f',colorLight:'#f5f2ec',
      correctLevel:QRCode.CorrectLevel.M});
  })();
})();
function nlmSubmit(){
  var emailEl=document.getElementById('nlm-email');
  var email=emailEl?emailEl.value.trim():'';
  if(!email||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){
    if(emailEl)emailEl.style.borderColor='rgba(200,41,10,.6)';return;
  }
  var body=new FormData();
  body.append('email',email);body.append('source','yaasap-daily-FORMSPREE_DATE_PH');
  body.append('_subject','Inscription YAASAP Notes Daily');body.append('_next','false');
  fetch('https://formspree.io/f/FORMSPREE_ID_PH',{method:'POST',body:body,headers:{'Accept':'application/json'}})
  .then(function(r){if(r.ok){
    var row=emailEl.parentElement;if(row)row.style.display='none';
    var ok=document.getElementById('nlm-ok');if(ok)ok.style.display='block';
  }});
}
document.addEventListener('keydown',function(e){
  if(e.key==='Enter'&&document.activeElement&&document.activeElement.id==='nlm-email')nlmSubmit();
});
</script>
</body>
</html>"""


# =============================================================
# 4. GENERATION HTML VIA CLAUDE
# =============================================================
SYSTEM = """Tu es l'analyste senior de YAASAP Notes, publication financiere style Financial Times.
Tu remplis un template HTML en remplacant les placeholders par du vrai contenu editorial.
Style editorial : presse financiere serieuse, analyses tranchees et actionnables.
Tu reponds UNIQUEMENT avec le HTML complet, sans backticks, sans texte avant ou apres."""


def generate_html(news_text, market_text, images, sources, market):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Images
    hero1_html = ""
    hero2_html = ""
    if images:
        img = images[0]
        hero1_html = (f'<div class="hero"><img src="{img["url"]}" alt="{img["title"]}" '
                      f'onerror="this.parentElement.style.display=\'none\'">'
                      f'<div class="hero-overlay"><div class="hero-tag">A la une</div>'
                      f'<div class="hero-title">HEADLINE_FROM_SIGNAL</div>'
                      f'<div class="hero-caption">{img["source"]}</div>'
                      f'</div></div>')
    if len(images) >= 2:
        img = images[1]
        hero2_html = (f'<div class="hero2"><img src="{img["url"]}" alt="{img["title"]}" '
                      f'onerror="this.parentElement.style.display=\'none\'">'
                      f'<div class="hero2-caption">{img["source"]} — {img["title"]}</div>'
                      f'</div>')

    # Sources
    sources_html = ""
    if sources:
        pills = "".join(f'<a href="{s["url"]}" target="_blank" class="src-pill">{s["name"]}</a>' for s in sources)
        sources_html = f'<div class="sources"><div class="sources-label">Sources</div><div class="src-list">{pills}</div></div>'

    # Blocs marché déjà calculés
    portfolio_html = build_portfolio_html(market)
    indices_html   = build_indices_html(market)
    ticker_html    = build_ticker_market(market)

    # Remplacement des placeholders statiques dans le template
    template = (TEMPLATE
        .replace("DATE_PH", DATE_STR)
        .replace("NOTE_NUM_PH", f"Note du {NUM}")
        .replace("HERO1_PH", hero1_html)
        .replace("HERO2_PH", hero2_html)
        .replace("SOURCES_PH", sources_html)
        .replace("PORTFOLIO_PH", portfolio_html)
        .replace("INDICES_PH", indices_html)
        .replace("MARKET_TICKER_PH", ticker_html)
        .replace("FORMSPREE_DATE_PH", TODAY.isoformat())
        .replace("FORMSPREE_ID_PH", FORMSPREE_ID)
    )

    prompt = f"""Articles du {DATE_STR} :
{news_text}

{market_text}

Remplace CHAQUE placeholder par du contenu editorial reel. HTML complet uniquement.

PLACEHOLDERS a remplacer :
HEADLINE_FROM_SIGNAL = titre court 8 mots max pour la photo hero

KICKER_NEWS_PH = 4 blocs kicker sur les actualites news (pas le marche, deja present) :
  <div class="kk"><div class="kk-l">LABEL</div><div class="kk-v">VALEUR</div><div class="kk-n">note</div></div>

SIGNAL_PH = signal principal :
  <div class="signal"><div class="signal-label">Analyse principale</div>
  <div class="signal-headline">TITRE</div><div class="signal-deck">sous-titre italique</div>
  <div class="signal-body"><p>paragraphe 1</p><p>paragraphe 2</p></div>
  <div class="pull"><div class="pull-t">citation</div><div class="pull-a">source</div></div></div>

ARTICLES_PH = 3 articles sectoriels :
  <div class="art"><div class="art-sector">SECTEUR</div><div class="art-h">titre</div>
  <div class="art-b">analyse avec <strong>mots cles</strong></div></div>

VERDICT_PH = 2-3 phrases synthese avec <strong>points cles</strong>

TEMPLATE :
{template}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    html = msg.content[0].text.strip()
    if "```" in html:
        for p in html.split("```"):
            s = p.strip()
            if s.startswith("<!") or s.startswith("<html"):
                return s
        html = html.split("```")[1]
        if html.startswith("html\n"):
            html = html[5:]
    return html.strip()


# =============================================================
# 5. DOCS/INDEX.HTML — INCHANGE
# =============================================================
def build_docs_index():
    pattern    = os.path.join(DOCS_DIR, "note-2*.html")
    note_files = sorted(glob.glob(pattern), reverse=True)
    items = ""
    for n in note_files:
        name  = os.path.basename(n)
        raw   = name.replace("note-", "").replace(".html", "")
        parts = raw.split("_")
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else None
        try:
            d = datetime.date.fromisoformat(date_part)
            label = d.strftime("%A %d %B %Y").capitalize()
            if time_part:
                label += " — " + time_part[:2] + "h" + time_part[2:]
            is_today = (d == TODAY)
        except Exception:
            label = raw; is_today = False
        badge = "<span class=\"badge\">Aujourd'hui</span>" if is_today else '<span class="dash">—</span>'
        items += f'<li>{badge}<a href="{name}">{label}</a></li>\n'

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes — Archives</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:Georgia,serif;background:#f9f6f0;color:#1c1814;}}
.mast{{background:#1c1814;padding:14px 20px;text-align:center;}}
.pub{{font-size:24px;font-weight:700;font-style:italic;color:#fff;letter-spacing:-.02em;}}
.pub em{{color:#8b3a1a;}}
.tagline{{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.38);margin-top:3px;font-family:Arial,sans-serif;}}
.container{{max-width:600px;margin:0 auto;padding:20px 20px 60px;}}
.sec{{font-size:9px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8b3a1a;border-bottom:1px solid #8b3a1a;padding-bottom:4px;margin:22px 0 13px;}}
.today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid #8b3a1a;padding:13px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0 3px 3px 0;}}
.today-box a{{font-size:16px;font-weight:700;color:#1c1814;text-decoration:none;display:block;line-height:1.3;}}
.today-box a:hover{{color:#8b3a1a;}}
.today-date{{font-size:10px;color:#9a8f82;font-style:italic;margin-top:5px;}}
ul{{list-style:none;padding:0;}}
li{{padding:8px 0;border-bottom:1px solid rgba(0,0,0,.07);display:flex;align-items:center;gap:10px;}}
li:last-child{{border-bottom:none;}}
li a{{font-size:13.5px;color:#1c1814;text-decoration:none;}}
li a:hover{{color:#8b3a1a;}}
.badge{{font-size:9px;background:#8b3a1a;color:#fff;padding:2px 7px;border-radius:2px;flex-shrink:0;}}
.dash{{color:#8b3a1a;font-size:13px;flex-shrink:0;}}
footer{{background:#f2ede4;border-top:1px solid rgba(0,0,0,.1);padding:13px 20px;text-align:center;font-size:10px;color:#9a8f82;font-style:italic;}}
.back{{font-size:12px;color:#8b3a1a;text-decoration:none;display:inline-block;margin-bottom:8px;}}
</style></head><body>
<div class="mast"><div class="pub">YAASAP <em>Notes</em></div>
<div class="tagline">Archives — Bulletins quotidiens automatiques</div></div>
<div class="container">
  <a class="back" href="../index.html">← Retour accueil</a>
  <div class="sec">Bulletin du jour</div>
  <div class="today-box">
    <a href="note-du-jour.html">Bulletin quotidien — {DATE_STR}</a>
    <div class="today-date" id="liveDate">{DATE_STR}</div>
  </div>
  <div class="sec">Toutes les archives ({len(note_files)} bulletins)</div>
  <ul>{items}</ul>
</div>
<footer>YAASAP Notes · Par Yacine AOUABED · Ne constitue pas un conseil en investissement</footer>
<script>(function(){{var d=new Date();var el=document.getElementById('liveDate');
if(el)el.textContent=d.toLocaleDateString('fr-FR',{{weekday:'long',year:'numeric',month:'long',day:'numeric'}});}})();</script>
</body></html>"""

    path = os.path.join(DOCS_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK docs/index.html — {len(note_files)} archives")


# =============================================================
# 6. SIDEBAR NOTES PONCTUELLES — injection dans index.html racine
# =============================================================

# Metadonnees connues des notes ponctuelles
# Format : nom_fichier -> (titre_court, categorie, date_affichee)
# "cat" : flash | position | analyse | macro | tech
NOTES_META = {
    "yaasap_starpipe.html":         ("SpaceX Starpipe — Primeur gazoduc Texas",     "flash",    "25 juin 2026"),
    "yaasap_lvmh.html":             ("LVMH — -26% YTD · PER 23x · Achat progressif","analyse",  "22 juin 2026"),
    "yaasap_viatris.html":          ("Viatris — Upside residuel · Attendre 12-13$", "analyse",  "22 juin 2026"),
    "yaasap_block_sq.html":         ("Block XYZ — BPA +25.9% · Stablecoin",         "analyse",  "18 juin 2026"),
    "yaasap_spcx_position.html":    ("SPCX — Position · PRU 174.44€ · 41 actions",  "position", "22 juin 2026"),
    "yaasap_spacex_ipo.html":       ("SpaceX IPO — 85.7 Md$ · +19% jour J",         "flash",    "15 juin 2026"),
    "yaasap_ttwo.html":             ("TTWO — GTA VI 19 nov. · BofA 320$",           "analyse",  "15 juin 2026"),
    "yaasap_semi_smallcap.html":    ("Silvaco SVCO · PDFS · COHU — Semi small-caps","analyse",  "15 juin 2026"),
    "yaasap_global_souscote.html":  ("Tous marches v5 — PFE · BABA · GM",           "analyse",  "15 juin 2026"),
    "yaasap_volatilite_v4.html":    ("Minieres or — NEM · Barrick · FCF record",    "macro",    "15 juin 2026"),
    "yaasap_europe_souscotee.html": ("Europe sous-cotee — Stellantis · Vivendi",    "analyse",  "15 juin 2026"),
    "yaasap_argenx_position.html":  ("ARGX — Achat 645€ · +20.9% · Conserver",     "position", "12 juin 2026"),
    "yaasap_oscr_position.html":    ("OSCR — Achat 19.28€ · Verdict vendre",        "position", "15 juin 2026"),
    "yaasap_argenx.html":           ("argenx — Zone achat 640-680€ · Bollinger",    "analyse",  "11 juin 2026"),
    "yaasap_volatilite_v3.html":    ("PLTR · CRWD · DDOG · SoFi — Correction",     "macro",    "11 juin 2026"),
    "yaasap_volatilite_v2.html":    ("LULU · ON Semi · OSCR — Strategie Buffett",   "analyse",   "9 juin 2026"),
    "yaasap_affiche_spcx.html":     ("Affiche print A4 — SPCX · Diffusion physique","flash",    "15 juin 2026"),
    "yaasap_baba_v2.html":          ("Alibaba BABA v2 — 40 analystes Buy",          "analyse",  "juin 2026"),
    "yaasap_spatial_live.html":     ("Secteur Spatial — RKLB · ASTS · IPO SpaceX",  "tech",     "juin 2026"),
    "yaasap_oil_gas.html":          ("Oil & Gas — TotalEnergies · Majors",           "macro",    "mai 2026"),
    "yaasap_ecosysteme_ia.html":    ("Ecosysteme IA — LLMs · GPU · Stockage",       "tech",     "avr. 2026"),
    "yaasap_gta6_light.html":       ("GTA VI — Cartographie boursiere",             "tech",     "mars 2026"),
    "yaasap_value.html":            ("Actions sous-cotees — PER bas · FCF",         "analyse",  "avr. 2026"),
}

CAT_COLORS = {
    "flash":    ("#c8290a", "rgba(200,41,10,.15)"),
    "position": ("#1a8a3a", "rgba(26,138,58,.15)"),
    "analyse":  ("#1a5c9a", "rgba(26,92,154,.15)"),
    "macro":    ("#d4880a", "rgba(212,136,10,.15)"),
    "tech":     ("#6b21a8", "rgba(107,33,168,.15)"),
}


def _title_from_filename(fname):
    """Genere un titre lisible depuis le nom de fichier."""
    return (fname
            .replace("yaasap_", "")
            .replace(".html", "")
            .replace("_", " ")
            .title())


def build_sidebar_html(root_dir):
    """
    Scanne tous les yaasap_*.html a la racine du repo,
    les trie par date (les plus recents en premier via NOTES_META,
    les inconnus en dernier), et retourne le HTML de la sidebar.
    """
    pattern = os.path.join(root_dir, "yaasap_*.html")
    found   = sorted(glob.glob(pattern), reverse=False)

    # Ordonner : connus d'abord dans l'ordre de NOTES_META, inconnus ensuite
    known_order = list(NOTES_META.keys())
    known_set   = set(known_order)

    ordered = []
    for fname in known_order:
        fpath = os.path.join(root_dir, fname)
        if os.path.exists(fpath):
            ordered.append(fname)
    for fpath in found:
        fname = os.path.basename(fpath)
        if fname not in known_set:
            ordered.append(fname)

    items_html = ""
    for i, fname in enumerate(ordered):
        meta  = NOTES_META.get(fname)
        title = meta[0] if meta else _title_from_filename(fname)
        cat   = meta[1] if meta else "analyse"
        date  = meta[2] if meta else ""
        col, bg = CAT_COLORS.get(cat, ("#9a8f82", "rgba(154,143,130,.1)"))
        is_new  = (i < 3)
        new_tag = (f'<span style="font-family:var(--mono,monospace);font-size:7px;font-weight:700;'
                   f'letter-spacing:.1em;text-transform:uppercase;background:{col};color:#fff;'
                   f'padding:1px 5px;border-radius:2px;margin-left:5px;vertical-align:middle;">NEW</span>'
                   if is_new else "")

        items_html += f"""<a class="sb-item" href="./{fname}" style="border-left-color:{col};">
  <div class="sb-cat" style="color:{col};background:{bg};">{cat.upper()}</div>
  <div class="sb-title">{title}{new_tag}</div>
  <div class="sb-date">{date}</div>
</a>
"""

    count = len(ordered)
    return f"""<!-- SIDEBAR_START -->
<aside class="sidebar">
  <div class="sb-header">
    <span class="sb-header-title">Notes ponctuelles</span>
    <span class="sb-header-count">{count}</span>
  </div>
  <div class="sb-list">
{items_html}  </div>
</aside>
<!-- SIDEBAR_END -->"""


def update_root_index_sidebar():
    """
    Injecte/met a jour la sidebar dans index.html racine.
    - Si index.html n'existe pas : le cree avec un layout deux colonnes minimal.
    - Si index.html existe et contient les marqueurs SIDEBAR_START/END : remplace le bloc.
    - Si index.html existe sans marqueurs : ajoute le CSS sidebar + injecte avant </body>.
    La zone editoriale de index.html (masthead, notes thematiques, newsletter) est preservee.
    """
    import re
    index_path = os.path.join(ROOT_DIR, "index.html")
    sidebar_html = build_sidebar_html(ROOT_DIR)

    # CSS a injecter une seule fois (si absent)
    SIDEBAR_CSS = """
<style id="yaasap-sidebar-css">
/* ── SIDEBAR NOTES PONCTUELLES (injecte par generate.py) ── */
.page-wrap{display:flex;gap:24px;max-width:1100px;margin:0 auto;padding:24px 20px 60px;align-items:flex-start;}
.main-col{flex:1;min-width:0;}
.sidebar{width:280px;flex-shrink:0;position:sticky;top:72px;max-height:calc(100vh - 90px);overflow-y:auto;}
.sidebar::-webkit-scrollbar{width:3px;}
.sidebar::-webkit-scrollbar-thumb{background:rgba(0,0,0,.15);border-radius:2px;}
.sb-header{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:var(--ink,#1c1814);border-radius:3px 3px 0 0;}
.sb-header-title{font-family:var(--mono,'Courier New'),monospace;font-size:8px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.5);}
.sb-header-count{font-family:var(--mono,'Courier New'),monospace;font-size:9px;font-weight:700;color:rgba(255,255,255,.3);background:rgba(255,255,255,.08);padding:1px 6px;border-radius:2px;}
.sb-list{display:flex;flex-direction:column;gap:0;border:1px solid rgba(0,0,0,.1);border-top:none;border-radius:0 0 3px 3px;overflow:hidden;}
.sb-item{display:block;padding:9px 12px;border-bottom:1px solid rgba(0,0,0,.07);border-left:2.5px solid transparent;text-decoration:none;background:#fff;transition:background .12s;}
.sb-item:last-child{border-bottom:none;}
.sb-item:hover{background:var(--paper2,#f2ede4);}
.sb-cat{font-family:var(--mono,'Courier New'),monospace;font-size:7px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:1px 6px;border-radius:2px;display:inline-block;margin-bottom:4px;}
.sb-title{font-family:var(--serif,'Georgia'),serif;font-size:12px;font-weight:700;color:var(--ink,#1c1814);line-height:1.3;margin-bottom:3px;}
.sb-date{font-family:var(--mono,'Courier New'),monospace;font-size:9px;color:var(--ink4,#9a8f82);}
/* Mobile : sidebar passe en bas */
@media(max-width:768px){
  .page-wrap{flex-direction:column;}
  .sidebar{width:100%;position:static;max-height:none;}
  .sb-list{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:rgba(0,0,0,.07);}
  .sb-item{background:#fff;}
}
</style>"""

    # ── CAS 1 : index.html absent ──
    if not os.path.exists(index_path):
        print("index.html absent — creation avec layout sidebar")
        html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
{SIDEBAR_CSS}
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{--paper:#f9f6f0;--paper2:#f2ede4;--ink:#1c1814;--ink4:#9a8f82;--accent:#8b3a1a;
  --serif:'Libre Baskerville',Georgia,serif;--sans:'Source Sans 3',Arial,sans-serif;
  --mono:'Source Code Pro','Courier New',monospace;}}
body{{background:var(--paper);font-family:var(--sans);color:var(--ink);font-size:15px;}}
.masthead{{background:var(--ink);padding:14px 22px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px double rgba(255,255,255,.15);position:sticky;top:0;z-index:100;}}
.pub-name{{font-family:var(--serif);font-size:22px;font-weight:700;color:#fff;letter-spacing:-.02em;}}
.pub-name em{{font-style:italic;color:var(--accent);}}
.mast-sub{{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.35);letter-spacing:.1em;text-transform:uppercase;}}
.main-col .today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid var(--accent);padding:14px 18px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0 3px 3px 0;}}
.main-col .today-box a{{font-family:var(--serif);font-size:17px;font-weight:700;color:var(--ink);text-decoration:none;display:block;}}
.main-col .today-box a:hover{{color:var(--accent);}}
.today-meta{{font-size:10px;color:var(--ink4);font-style:italic;margin-top:5px;}}
footer{{background:var(--paper2);border-top:1px solid rgba(0,0,0,.1);padding:14px 22px;text-align:center;font-size:10px;color:var(--ink4);font-style:italic;}}
</style>
</head>
<body>
<div class="masthead">
  <div>
    <div class="pub-name">YAASAP <em>Notes</em></div>
    <div class="mast-sub">Analyse financiere independante · Par Yacine AOUABED</div>
  </div>
</div>
<div class="page-wrap">
  <div class="main-col">
    <div class="today-box">
      <a href="docs/note-du-jour.html">Bulletin du jour &mdash; Marches · Positions · Analyse</a>
      <div class="today-meta" id="todayMeta">{DATE_STR}</div>
    </div>
    <p style="font-size:13px;color:var(--ink4);font-style:italic;padding:10px 0;">
      Personnalisez cette page en editant index.html — la colonne droite est mise a jour automatiquement.
    </p>
  </div>
  {sidebar_html}
</div>
<footer>YAASAP Notes &middot; Par Yacine AOUABED &middot; Ne constitue pas un conseil en investissement</footer>
<script>
(function(){{var d=new Date();var opts={{weekday:'long',year:'numeric',month:'long',day:'numeric'}};
var el=document.getElementById('todayMeta');if(el)el.textContent=d.toLocaleDateString('fr-FR',opts);}})();
</script>
</body>
</html>"""
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("OK index.html cree avec sidebar")
        return

    # ── CAS 2 : index.html existe avec marqueurs → remplace le bloc sidebar ──
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "<!-- SIDEBAR_START -->" in content and "<!-- SIDEBAR_END -->" in content:
        new_content = re.sub(
            r"<!-- SIDEBAR_START -->.*?<!-- SIDEBAR_END -->",
            sidebar_html,
            content,
            flags=re.DOTALL
        )
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        count = len([l for l in sidebar_html.split('\n') if 'sb-item' in l and 'href' in l])
        print(f"OK index.html sidebar mise a jour ({count} notes)")
        return

    # ── CAS 3 : index.html existe SANS marqueurs ──
    # Injecter le CSS (une fois) + la sidebar avant </body>
    if "yaasap-sidebar-css" not in content:
        content = content.replace("</head>", SIDEBAR_CSS + "\n</head>", 1)

    # Envelopper le contenu principal dans .page-wrap si pas encore fait
    if "page-wrap" not in content:
        # Inserer la sidebar juste avant </body>
        content = content.replace(
            "</body>",
            f"\n<!-- Sidebar injectee par generate.py -->\n{sidebar_html}\n</body>",
            1
        )
        print("OK index.html sidebar injectee (premier run sans marqueurs)")
    else:
        # page-wrap existe mais pas les marqueurs — inserer dans le wrap
        content = content.replace(
            "</body>",
            f"\n{sidebar_html}\n</body>",
            1
        )
        print("OK index.html sidebar injectee dans page-wrap existant")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


# =============================================================
# 7. MAIN
# =============================================================
def main():
    print(f"\n{'='*54}")
    print(f"YAASAP Notes — Generation {TIMESTAMP}")
    print(f"{'='*54}\n")

    os.makedirs(DOCS_DIR, exist_ok=True)

    # 1. Donnees marche
    print("1. Donnees de marche (yfinance)...")
    market = fetch_market_data()

    # 2. News
    print("\n2. Actualites financieres (NewsAPI)...")
    articles = fetch_news()
    if not articles:
        print("Aucun article recupere — arret")
        sys.exit(1)
    images    = get_top_images(articles, n=2)
    sources   = get_sources(articles)
    news_text = format_articles(articles)
    mkt_text  = format_market_for_claude(market)
    print(f"   {len(articles)} articles · {len(images)} images · {len(sources)} sources")

    # 3. Generation via Claude
    print("\n3. Generation editoriale via Claude Sonnet 4-6...")
    html = generate_html(news_text, mkt_text, images, sources, market)

    # 4. Sauvegarde
    print("\n4. Sauvegarde...")
    note_ts  = os.path.join(DOCS_DIR, f"note-{TIMESTAMP}.html")
    note_day = os.path.join(DOCS_DIR, "note-du-jour.html")
    with open(note_ts, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   OK archive : note-{TIMESTAMP}.html")
    with open(note_day, "w", encoding="utf-8") as f:
        f.write(html)
    print("   OK note-du-jour.html")

    # 5. Archives bulletins quotidiens
    print("\n5. Mise a jour docs/index.html (archives)...")
    build_docs_index()

   # 6. Sidebar notes ponctuelles dans index.html racine — DESACTIVE
   # update_root_index_sidebar()

    print(f"\n Publie : https://yaasap.github.io/dailywatch/")
    print(f"   Bulletins archives : https://yaasap.github.io/dailywatch/docs/index.html")


if __name__ == "__main__":
    main()

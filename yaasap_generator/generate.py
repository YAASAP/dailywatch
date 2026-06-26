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
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes - DATE_PH</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{
  --paper:#f9f6f0;--paper2:#f2ede4;--paper3:#e8e1d5;
  --ink:#1c1814;--ink2:#3a342c;--ink3:#6a5f52;--ink4:#9a8f82;
  --rule:rgba(0,0,0,0.12);--rule2:rgba(0,0,0,0.07);
  --accent:#8b3a1a;--green:#1e5c32;--amber:#8a5c00;--gold:#c8902a;
  --red:#8b1a1a;
  --serif:'Libre Baskerville',Georgia,serif;
  --sans:'Source Sans 3','Helvetica Neue',Arial,sans-serif;
  --mono:'Source Code Pro','Courier New',monospace;
}
html,body{background:var(--paper);font-family:var(--sans);color:var(--ink);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;}
.masthead{background:var(--ink);border-bottom:3px double rgba(255,255,255,.15);padding:12px 22px 10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3);}
.pub-name{font-family:var(--serif);font-size:22px;font-weight:700;letter-spacing:-.02em;color:#fff;line-height:1;}
.pub-name em{font-style:italic;color:var(--accent);}
.pub-tagline{font-size:7.5px;color:rgba(255,255,255,.35);letter-spacing:.14em;text-transform:uppercase;margin-top:2px;font-family:var(--sans);}
.mast-center{text-align:center;flex:1;}
.mast-tag{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.38);letter-spacing:.1em;text-transform:uppercase;border-top:1px solid rgba(255,255,255,.12);border-bottom:1px solid rgba(255,255,255,.12);padding:2px 10px;display:inline-block;}
.mast-right{display:flex;align-items:center;gap:10px;}
.mast-date{font-family:var(--serif);font-size:10px;color:rgba(255,255,255,.42);font-style:italic;}
.mast-qr-box{background:#fff;padding:4px;border-radius:2px;line-height:0;}
.mast-qr-lbl{font-family:var(--mono);font-size:6px;color:rgba(255,255,255,.22);letter-spacing:.06em;text-transform:uppercase;margin-top:2px;text-align:center;}
.hero{position:relative;width:100%;height:200px;overflow:hidden;}
.hero img{width:100%;height:200px;object-fit:cover;display:block;filter:brightness(.72);}
.hero-overlay{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(28,24,20,.85));padding:14px 20px;}
.hero-tag{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:700;margin-bottom:3px;font-family:var(--sans);}
.hero-title{font-size:18px;font-weight:700;color:#fff;line-height:1.2;font-family:var(--serif);}
.hero-caption{font-size:9.5px;color:rgba(255,255,255,.5);margin-top:3px;font-style:italic;font-family:var(--sans);}
.kicker{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--paper2);border-bottom:1px solid var(--rule);}
.kicker::-webkit-scrollbar{display:none;}
.kicker-inner{display:flex;padding:0 16px;min-width:max-content;}
.kk{padding:8px 14px;border-right:1px solid var(--rule2);flex-shrink:0;}
.kk:last-child{border-right:none;}
.kk-l{font-size:8px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink4);margin-bottom:2px;font-family:var(--sans);}
.kk-v{font-family:var(--mono);font-size:13px;font-weight:600;color:var(--ink);line-height:1;}
.kk-n{font-size:9px;color:var(--ink4);font-style:italic;margin-top:1px;font-family:var(--sans);}
.content{max-width:700px;margin:0 auto;padding:20px 20px 48px;}
.sec{display:flex;align-items:center;gap:8px;margin:24px 0 13px;}
.sec::before{content:'';width:20px;height:2px;background:var(--accent);flex-shrink:0;}
.sec-t{font-size:8px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);font-family:var(--sans);}
.sec::after{content:'';flex:1;height:1px;background:var(--rule);}
.signal{background:#fff;border:1px solid var(--rule);border-left:3px solid var(--accent);border-radius:0 3px 3px 0;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.signal-label{font-size:8.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--accent);font-weight:700;margin-bottom:6px;font-family:var(--sans);}
.signal-headline{font-family:var(--serif);font-size:19px;font-weight:700;line-height:1.2;margin-bottom:8px;color:var(--ink);}
.signal-deck{font-family:var(--serif);font-size:13px;font-style:italic;color:var(--ink3);line-height:1.5;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid var(--rule2);}
.signal-body{font-size:13px;color:var(--ink2);line-height:1.65;font-family:var(--sans);}
.signal-body strong{font-weight:700;color:var(--ink);}
.signal-body p{margin-bottom:8px;}
.pull{border-top:2px solid var(--accent);border-bottom:1px solid var(--rule);padding:10px 13px;margin:13px 0;}
.pull-t{font-family:var(--serif);font-size:14px;font-style:italic;line-height:1.45;color:var(--ink);}
.pull-a{font-size:9px;color:var(--ink4);letter-spacing:.08em;text-transform:uppercase;margin-top:4px;font-family:var(--sans);}
.art{background:#fff;border:1px solid var(--rule);border-radius:2px;padding:13px 15px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.art-sector{font-size:8.5px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;margin-bottom:4px;font-family:var(--sans);color:var(--accent);}
.art-h{font-family:var(--serif);font-size:15px;font-weight:700;color:var(--ink);line-height:1.25;margin-bottom:5px;}
.art-b{font-size:12.5px;color:var(--ink3);line-height:1.55;font-family:var(--sans);}
.art-b strong{color:var(--ink);font-weight:700;}
.hero2{position:relative;width:100%;height:150px;overflow:hidden;border-radius:2px;margin:14px 0;}
.hero2 img{width:100%;height:150px;object-fit:cover;filter:brightness(.8);}
.hero2-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(28,24,20,.7);padding:6px 12px;font-size:9.5px;color:rgba(255,255,255,.75);font-style:italic;font-family:var(--sans);}
.table-wrap{background:#fff;border:1px solid var(--rule);border-radius:2px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05);margin-bottom:14px;}
.table-wrap table{width:100%;border-collapse:collapse;}
.table-wrap th{font-size:8px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink4);padding:7px 11px;text-align:left;border-bottom:1.5px solid var(--ink);background:var(--paper2);font-family:var(--sans);}
.table-wrap td{font-size:12px;padding:7px 11px;border-bottom:1px solid var(--rule2);color:var(--ink2);vertical-align:middle;font-family:var(--sans);}
.table-wrap tr:last-child td{border-bottom:none;}
.table-wrap tr:hover td{background:var(--paper2);}
.badge-up{background:rgba(30,92,50,.1);color:var(--green);font-size:9px;font-weight:700;padding:2px 6px;border-radius:2px;}
.badge-dn{background:rgba(139,58,26,.1);color:var(--accent);font-size:9px;font-weight:700;padding:2px 6px;border-radius:2px;}
.badge-am{background:rgba(138,92,0,.1);color:var(--amber);font-size:9px;font-weight:700;padding:2px 6px;border-radius:2px;}
.verdict{background:var(--ink);border-radius:2px;padding:16px 18px;margin:22px 0;}
.v-tag{font-size:8px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;background:var(--accent);color:#fff;padding:3px 8px;border-radius:2px;display:inline-block;margin-bottom:10px;font-family:var(--sans);}
.v-t{font-family:var(--serif);font-size:13px;color:rgba(255,255,255,.88);font-style:italic;line-height:1.6;}
.v-t strong{font-style:normal;color:var(--gold);}
.sources{background:var(--paper2);border-radius:2px;padding:11px 15px;margin:14px 0;}
.sources-label{font-size:8.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:7px;font-family:var(--sans);}
.src-list{display:flex;flex-wrap:wrap;gap:5px;}
.src-pill{font-size:10px;color:var(--ink3);background:#fff;border:1px solid var(--rule);border-radius:20px;padding:3px 9px;text-decoration:none;font-style:italic;font-family:var(--sans);}
.nl-mini{background:var(--ink);border-top:2px solid var(--accent);padding:14px 16px;margin-top:22px;border-radius:2px;}
.nl-mini-title{font-family:var(--serif);font-size:13px;font-weight:700;color:#f0ebe3;margin-bottom:4px;}
.nl-mini-sub{font-size:11px;color:rgba(255,255,255,.38);margin-bottom:8px;font-family:var(--sans);}
.nl-mini-row{display:flex;gap:6px;}
.nl-mini-input{flex:1;height:38px;padding:0 11px;border:1.5px solid rgba(255,255,255,.15);background:rgba(255,255,255,.07);border-radius:3px;font-family:var(--sans);font-size:13px;color:#fff;outline:none;}
.nl-mini-input::placeholder{color:rgba(255,255,255,.28);}
.nl-mini-input:focus{border-color:var(--gold);}
.nl-mini-btn{height:38px;padding:0 14px;background:var(--accent);border:none;border-radius:3px;color:#fff;font-family:var(--sans);font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;}
.nl-mini-note{font-size:9.5px;color:rgba(255,255,255,.2);margin-top:5px;font-family:var(--sans);}
#nlm-ok{display:none;font-size:12px;font-weight:700;color:#4ade80;margin-top:5px;}
footer{background:var(--paper2);border-top:1.5px solid var(--rule);padding:14px 20px;text-align:center;}
.foot-brand{font-family:var(--serif);font-size:14px;font-weight:700;color:var(--ink);margin-bottom:3px;}
.foot-brand em{font-style:italic;color:var(--accent);}
.foot-note{font-size:10px;color:var(--ink4);font-style:italic;font-family:var(--sans);}
.foot-nav{display:flex;justify-content:center;gap:14px;margin-top:8px;flex-wrap:wrap;}
.foot-nav a{font-size:11px;color:var(--accent);text-decoration:none;font-family:var(--sans);}
@media(min-width:640px){.hero{height:260px;}.hero img{height:260px;}.hero-title{font-size:22px;}}
</style>
</head>
<body>
<div class="masthead">
  <div>
    <div class="pub-name">YAASAP <em>Notes</em></div>
    <div class="pub-tagline">Bulletin quotidien automatique · Analyse financiere independante</div>
  </div>
  <div class="mast-center">
    <span class="mast-tag">Bulletin du DATE_PH · Genere automatiquement a 07h00</span>
  </div>
  <div class="mast-right">
    <div class="mast-date" id="liveDate">DATE_PH</div>
    <div>
      <div class="mast-qr-box"><div id="qr-mast" style="line-height:0;"></div></div>
      <div class="mast-qr-lbl">dailywatch</div>
    </div>
  </div>
</div>
HERO1_PH
<div class="kicker"><div class="kicker-inner">MARKET_TICKER_PHKICKER_NEWS_PH</div></div>
<div class="content">
  <div class="sec"><span class="sec-t">Marche du jour · Portefeuille &amp; Indices</span></div>
  PORTFOLIO_PH
  INDICES_PH
  <div class="sec"><span class="sec-t">Signal du jour</span></div>
  SIGNAL_PH
  <div class="sec"><span class="sec-t">Analyses sectorielles</span></div>
  ARTICLES_PH
  HERO2_PH
  <div class="verdict"><div class="v-tag">Verdict YAASAP</div><div class="v-t">VERDICT_PH</div></div>
  SOURCES_PH
  <div class="nl-mini">
    <div class="nl-mini-title">Recevoir ce bulletin chaque matin</div>
    <div class="nl-mini-sub">Gratuit · Desabonnement en 1 clic · Donnees marche + analyse editoriale</div>
    <div class="nl-mini-row">
      <input class="nl-mini-input" type="email" id="nlm-email" placeholder="votre@email.com" autocomplete="email">
      <button class="nl-mini-btn" onclick="nlmSubmit()">S'abonner</button>
    </div>
    <div id="nlm-ok">Inscrit !</div>
    <div class="nl-mini-note">RGPD · Formspree · yaasap.github.io/dailywatch</div>
  </div>
</div>
<footer>
  <div class="foot-brand">YAASAP <em>Notes</em></div>
  <div class="foot-note">Par <strong>Yacine AOUABED</strong> &middot; NOTE_NUM_PH &middot; <span id="liveDateFooter">DATE_PH</span><br>Analyse informative uniquement - Ne constitue pas un conseil en investissement</div>
  <div class="foot-nav">
    <a href="../index.html">Accueil</a>
    <a href="index.html">Archives</a>
    <a href="../yaasap_starpipe.html">Starpipe</a>
    <a href="../yaasap_lvmh.html">LVMH</a>
    <a href="../yaasap_spcx_position.html">Position SPCX</a>
  </div>
</footer>
<script>
(function(){
  var d=new Date();
  var opts={weekday:'long',year:'numeric',month:'long',day:'numeric'};
  var s=d.toLocaleDateString('fr-FR',opts);
  var e1=document.getElementById('liveDate');
  var e2=document.getElementById('liveDateFooter');
  if(e1)e1.textContent=s;
  if(e2)e2.textContent=s;
  (function tryQR(){
    var el=document.getElementById('qr-mast');
    if(!el||typeof QRCode==='undefined'){setTimeout(tryQR,80);return;}
    new QRCode(el,{text:'https://yaasap.github.io/dailywatch/index.html',
      width:48,height:48,colorDark:'#1c1814',colorLight:'#ffffff',
      correctLevel:QRCode.CorrectLevel.M});
  })();
})();
function nlmSubmit(){
  var emailEl=document.getElementById('nlm-email');
  var email=emailEl?emailEl.value.trim():'';
  if(!email||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){
    if(emailEl){emailEl.style.borderColor='rgba(255,100,100,.6)';}return;
  }
  var body=new FormData();
  body.append('email',email);body.append('source','yaasap-daily-FORMSPREE_DATE_PH');
  body.append('_subject','Inscription YAASAP Notes Daily');body.append('_next','false');
  fetch('https://formspree.io/f/FORMSPREE_ID_PH',{method:'POST',body:body,headers:{'Accept':'application/json'}})
  .then(function(r){if(r.ok){var row=emailEl.parentElement;if(row)row.style.display='none';
    var ok=document.getElementById('nlm-ok');if(ok)ok.style.display='block';}});
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
# 6. INDEX RACINE — PROTEGE (inchange)
# =============================================================
def build_root_index():
    """
    NE REGENERE JAMAIS index.html si le fichier existe deja.
    Garde identique a la version originale.
    """
    index_path = os.path.join(ROOT_DIR, "index.html")
    if os.path.exists(index_path):
        print("SKIP index.html racine — fichier existant protege (supprimer pour regenerer)")
        return

    print("index.html absent — generation initiale minimale")
    KNOWN = {f: (t, m) for f, t, m in ANALYSES}
    pattern    = os.path.join(ROOT_DIR, "yaasap_*.html")
    found_files = sorted(glob.glob(pattern), reverse=True)
    analyses_items = ""
    for i, fpath in enumerate(found_files):
        fname = os.path.basename(fpath)
        if fname in KNOWN:
            title, meta = KNOWN[fname]
        else:
            title = fname.replace("yaasap_","").replace(".html","").replace("_"," ").title()
            meta  = "Analyse YAASAP Notes"
        badge = '<span class="badge-new">Nouveau</span>' if i < 3 else ''
        analyses_items += (f'<li><span class="note-bullet">&mdash;</span><div>'
                           f'<a class="note-link" href="{fname}">{title}{badge}</a>'
                           f'<span class="li-meta">{meta}</span></div></li>\n')

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YAASAP Notes</title>
<meta http-equiv="refresh" content="0;url=docs/note-du-jour.html">
</head><body>
<p><a href="docs/note-du-jour.html">YAASAP Notes — Bulletin du jour</a></p>
</body></html>"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK index.html racine (redirection minimale — a personnaliser)")


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

    # 5. Archives
    print("\n5. Mise a jour docs/index.html...")
    build_docs_index()

    # 6. Index racine (protege)
    print("\n6. Verification index.html racine...")
    build_root_index()

    print(f"\nPublie : https://yaasap.github.io/dailywatch/docs/note-du-jour.html")


if __name__ == "__main__":
    main()

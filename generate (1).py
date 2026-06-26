#!/usr/bin/env python3
"""
YAASAP Notes — Générateur automatique de note quotidienne
Déclenché par GitHub Actions chaque matin à 7h00 (Paris)
Dépendances : pip install yfinance requests
"""

import os
import json
import datetime
import yfinance as yf

# ──────────────────────────────────────────────
# CONFIG — TITRES SUIVIS
# ──────────────────────────────────────────────
TICKERS = {
    # Vos positions personnelles
    "SPCX":  {"name": "SpaceX",            "cat": "position", "pru": 174.44, "qty": 41},
    "TTWO":  {"name": "Take-Two",          "cat": "position", "pru": 195.06, "qty": 6},
    "SQM":   {"name": "SQM ADR",           "cat": "position", "pru": 73.21,  "qty": 12},
    "PFE":   {"name": "Pfizer",            "cat": "position", "pru": 23.49,  "qty": 7},
    # Valeurs sous surveillance
    "ARGX":  {"name": "argenx",            "cat": "watch",    "pru": None,   "qty": 0},
    "XYZ":   {"name": "Block Inc",         "cat": "watch",    "pru": None,   "qty": 0},
    "MC.PA": {"name": "LVMH",              "cat": "watch",    "pru": None,   "qty": 0},
    "VTRS":  {"name": "Viatris",           "cat": "watch",    "pru": None,   "qty": 0},
    # Indices de référence
    "^GSPC": {"name": "S&P 500",           "cat": "index",    "pru": None,   "qty": 0},
    "^FCHI": {"name": "CAC 40",            "cat": "index",    "pru": None,   "qty": 0},
    "^STOXX50E": {"name": "Euro Stoxx 50", "cat": "index",    "pru": None,   "qty": 0},
    "GC=F":  {"name": "Or (Gold)",         "cat": "macro",    "pru": None,   "qty": 0},
    "BTC-USD": {"name": "Bitcoin",         "cat": "macro",    "pru": None,   "qty": 0},
}

def fetch_data():
    """Récupère les données de marché via yfinance."""
    data = {}
    for ticker, meta in TICKERS.items():
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            price    = round(float(info.last_price), 2) if info.last_price else None
            prev     = round(float(info.previous_close), 2) if info.previous_close else None
            change   = round(price - prev, 2) if price and prev else None
            change_p = round((change / prev) * 100, 2) if change and prev else None
            data[ticker] = {
                "name":     meta["name"],
                "cat":      meta["cat"],
                "pru":      meta.get("pru"),
                "qty":      meta.get("qty", 0),
                "price":    price,
                "prev":     prev,
                "change":   change,
                "change_p": change_p,
                "currency": getattr(info, "currency", "USD"),
            }
            print(f"  ✓ {ticker:12s} {price}")
        except Exception as e:
            print(f"  ✗ {ticker:12s} erreur: {e}")
            data[ticker] = {**meta, "price": None, "prev": None, "change": None, "change_p": None, "currency": "USD"}
    return data

def fmt_price(price, currency="USD", decimals=2):
    sym = "€" if currency == "EUR" else "$"
    if price is None:
        return "—"
    return f"{sym}{price:,.{decimals}f}"

def fmt_change(chp):
    if chp is None:
        return '<span style="color:#9a8f82;">—</span>'
    color = "#1e5c32" if chp >= 0 else "#b01c1c"
    arrow = "▲" if chp >= 0 else "▼"
    return f'<span style="color:{color};font-weight:700;">{arrow} {abs(chp):.2f}%</span>'

def pnl_row(meta, price):
    """Calcule le P&L latent sur une position."""
    if not meta.get("pru") or not meta.get("qty") or not price:
        return None
    pru = meta["pru"]
    qty = meta["qty"]
    pnl = (price - pru) * qty
    pnl_p = ((price - pru) / pru) * 100
    return {"pnl": round(pnl, 2), "pnl_p": round(pnl_p, 2), "pru": pru, "qty": qty}

def generate_html(data, date_str, date_fr):
    """Génère le HTML complet de la note quotidienne."""

    # Calculs portefeuille
    total_val = 0
    total_pnl = 0
    for ticker, d in data.items():
        if d["cat"] == "position" and d["price"] and d.get("qty"):
            val = d["price"] * d["qty"]
            total_val += val
            p = pnl_row(d, d["price"])
            if p:
                total_pnl += p["pnl"]

    # Ligne de ticker défilant
    ticker_items = ""
    for ticker, d in data.items():
        if d["price"]:
            sym = "€" if d.get("currency") == "EUR" else "$"
            chp = d["change_p"]
            col = "#4ade80" if chp and chp >= 0 else "#f87171"
            arr = "▲" if chp and chp >= 0 else "▼"
            ticker_items += f'<span class="tick-item">{d["name"]} {sym}{d["price"]:.2f} <span style="color:{col};">{arr} {abs(chp):.2f}%</span></span><span class="tick-sep"> ◆ </span>'

    # Table des positions
    pos_rows = ""
    for ticker, d in data.items():
        if d["cat"] != "position":
            continue
        p = pnl_row(d, d["price"])
        price_str = fmt_price(d["price"], d.get("currency","USD"))
        change_str = fmt_change(d["change_p"])
        if p:
            pnl_col = "#1e5c32" if p["pnl"] >= 0 else "#b01c1c"
            pnl_str = f'<span style="color:{pnl_col};font-weight:700;">{"+" if p["pnl"]>=0 else ""}{p["pnl"]:,.0f} $ ({p["pnl_p"]:+.2f}%)</span>'
            pru_str = f'${p["pru"]:.2f} × {p["qty"]}'
        else:
            pnl_str = "—"
            pru_str = "—"
        pos_rows += f"""
        <tr>
          <td style="font-weight:700;font-family:var(--mono);">{ticker}</td>
          <td>{d["name"]}</td>
          <td style="font-family:var(--mono);">{price_str}</td>
          <td>{change_str}</td>
          <td style="font-family:var(--mono);font-size:11px;">{pru_str}</td>
          <td>{pnl_str}</td>
        </tr>"""

    # Table de surveillance
    watch_rows = ""
    for ticker, d in data.items():
        if d["cat"] not in ("watch", "macro"):
            continue
        price_str = fmt_price(d["price"], d.get("currency","USD"))
        change_str = fmt_change(d["change_p"])
        watch_rows += f"""
        <tr>
          <td style="font-weight:700;font-family:var(--mono);">{ticker}</td>
          <td>{d["name"]}</td>
          <td style="font-family:var(--mono);">{price_str}</td>
          <td>{change_str}</td>
        </tr>"""

    # Table des indices
    index_rows = ""
    for ticker, d in data.items():
        if d["cat"] != "index":
            continue
        price_str = fmt_price(d["price"], d.get("currency","USD"), 0)
        change_str = fmt_change(d["change_p"])
        index_rows += f"""
        <tr>
          <td style="font-weight:700;font-family:var(--mono);">{d["name"]}</td>
          <td style="font-family:var(--mono);">{price_str}</td>
          <td>{change_str}</td>
        </tr>"""

    pnl_col_total = "#1e5c32" if total_pnl >= 0 else "#b01c1c"
    pnl_sign = "+" if total_pnl >= 0 else ""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YAASAP Notes · Bulletin quotidien · {date_fr}</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{
  --paper:#f9f6f0;--paper2:#f2ede4;
  --ink:#1c1814;--ink2:#3a342c;--ink3:#6a5f52;--ink4:#9a8f82;
  --rule:rgba(0,0,0,0.12);--rule2:rgba(0,0,0,0.07);
  --accent:#8b3a1a;--green:#1e5c32;--amber:#8a5c00;--gold:#c8902a;
  --serif:'Libre Baskerville',Georgia,serif;
  --sans:'Source Sans 3','Helvetica Neue',Arial,sans-serif;
  --mono:'Source Code Pro','Courier New',monospace;
}}
html,body{{background:var(--paper);font-family:var(--sans);color:var(--ink);font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased;}}
.masthead{{background:var(--ink);padding:12px 22px 10px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border-bottom:3px double rgba(255,255,255,.15);}}
.pub-name{{font-family:var(--serif);font-size:22px;font-weight:700;color:#fff;line-height:1;}}
.pub-name em{{font-style:italic;color:var(--accent);}}
.pub-tagline{{font-size:7.5px;color:rgba(255,255,255,.35);letter-spacing:.14em;text-transform:uppercase;margin-top:2px;font-family:var(--sans);}}
.mast-center{{text-align:center;flex:1;}}
.mast-tag{{font-family:var(--mono);font-size:8px;color:rgba(255,255,255,.38);letter-spacing:.1em;text-transform:uppercase;border-top:1px solid rgba(255,255,255,.12);border-bottom:1px solid rgba(255,255,255,.12);padding:2px 10px;display:inline-block;}}
.mast-right{{display:flex;align-items:center;gap:12px;}}
.mast-date{{font-family:var(--serif);font-size:10px;color:rgba(255,255,255,.4);font-style:italic;}}
.mast-qr-box{{background:#fff;padding:4px;border-radius:2px;line-height:0;}}
.mast-qr-lbl{{font-family:var(--mono);font-size:6px;color:rgba(255,255,255,.25);letter-spacing:.06em;text-transform:uppercase;margin-top:2px;text-align:center;}}
.ticker-bar{{background:var(--accent);overflow:hidden;white-space:nowrap;padding:5px 0;}}
.ticker-inner{{display:inline-flex;animation:tick 35s linear infinite;}}
@keyframes tick{{from{{transform:translateX(0);}}to{{transform:translateX(-50%);}}}}
.tick-item{{font-family:var(--mono);font-size:10px;color:#fff;padding:0 20px;white-space:nowrap;}}
.tick-sep{{color:rgba(255,255,255,.4);}}
.hero{{background:var(--ink);padding:20px 22px 16px;border-bottom:1px solid rgba(255,255,255,.06);}}
.hero-inner{{max-width:720px;margin:0 auto;}}
.hero-eyebrow{{font-family:var(--mono);font-size:8.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--gold);margin-bottom:8px;}}
.hero-hl{{font-family:var(--serif);font-size:24px;font-weight:700;color:#f0ebe3;line-height:1.15;margin-bottom:8px;}}
.hero-kpis{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid rgba(255,255,255,.07);padding-top:12px;margin-top:4px;}}
.hkpi{{padding:4px 14px 4px 0;}}
.hkpi-v{{font-family:var(--mono);font-size:16px;font-weight:600;color:#f0ebe3;line-height:1;display:block;}}
.hkpi-l{{font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.28);margin-top:3px;display:block;font-family:var(--sans);}}
.content{{max-width:720px;margin:0 auto;padding:22px 22px 48px;}}
.sec-rule{{display:flex;align-items:center;gap:8px;margin:24px 0 13px;}}
.sec-rule::before{{content:'';width:20px;height:2px;background:var(--accent);flex-shrink:0;}}
.sec-rule-text{{font-size:8px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);font-family:var(--sans);}}
.sec-rule::after{{content:'';flex:1;height:1px;background:var(--rule);}}
.data-table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule);border-radius:2px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);font-size:12.5px;margin-bottom:18px;}}
.data-table th{{font-size:8px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink4);padding:8px 12px;text-align:left;border-bottom:1.5px solid var(--ink);background:var(--paper2);font-family:var(--sans);}}
.data-table td{{padding:7px 12px;border-bottom:1px solid var(--rule2);color:var(--ink2);vertical-align:middle;font-family:var(--sans);}}
.data-table tr:last-child td{{border-bottom:none;}}
.data-table tr:hover td{{background:var(--paper2);}}
.portfolio-summary{{background:#fff;border:1px solid var(--rule);border-top:3px solid var(--accent);border-radius:2px;padding:14px 16px;margin-bottom:18px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;box-shadow:0 1px 4px rgba(0,0,0,.05);}}
.ps-item{{text-align:center;}}
.ps-v{{font-family:var(--mono);font-size:18px;font-weight:700;color:var(--ink);display:block;line-height:1;}}
.ps-l{{font-size:8px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink4);margin-top:3px;display:block;font-family:var(--sans);}}
.nav-links{{display:flex;gap:10px;margin-bottom:22px;flex-wrap:wrap;}}
.nav-link{{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:5px 12px;border:1px solid var(--rule);border-radius:2px;color:var(--accent);text-decoration:none;transition:all .12s;font-family:var(--sans);}}
.nav-link:hover{{background:var(--accent);color:#fff;border-color:var(--accent);}}
.nl-mini{{background:var(--ink);border-top:2px solid var(--accent);padding:14px 16px;margin-top:24px;border-radius:2px;}}
.nl-mini-title{{font-family:var(--serif);font-size:14px;font-weight:700;color:#f0ebe3;margin-bottom:4px;}}
.nl-mini-row{{display:flex;gap:6px;margin-top:8px;}}
.nl-mini-input{{flex:1;height:38px;padding:0 11px;border:1.5px solid rgba(255,255,255,.15);background:rgba(255,255,255,.07);border-radius:3px;font-family:var(--sans);font-size:13px;color:#fff;outline:none;}}
.nl-mini-input::placeholder{{color:rgba(255,255,255,.28);}}
.nl-mini-input:focus{{border-color:var(--gold);}}
.nl-mini-btn{{height:38px;padding:0 14px;background:var(--accent);border:none;border-radius:3px;color:#fff;font-family:var(--sans);font-size:13px;font-weight:700;cursor:pointer;}}
.nl-mini-note{{font-size:10px;color:rgba(255,255,255,.22);margin-top:6px;font-family:var(--sans);}}
#nlm-ok{{display:none;font-size:12px;font-weight:700;color:#4ade80;margin-top:6px;}}
footer{{background:var(--paper2);border-top:1.5px solid var(--rule);padding:12px 22px;text-align:center;}}
.foot-brand{{font-family:var(--serif);font-size:14px;font-weight:700;color:var(--ink);}}
.foot-brand em{{font-style:italic;color:var(--accent);}}
.foot-note{{font-size:10px;color:var(--ink4);font-style:italic;font-family:var(--sans);margin-top:2px;}}
</style>
</head>
<body>

<div class="masthead">
  <div>
    <div class="pub-name">YAASAP <em>Notes</em></div>
    <div class="pub-tagline">Bulletin quotidien automatique · Analyse financière indépendante</div>
  </div>
  <div class="mast-center">
    <span class="mast-tag">Bulletin quotidien · {date_fr} · Généré automatiquement à 07h00</span>
  </div>
  <div class="mast-right">
    <div class="mast-date">{date_fr}</div>
    <div>
      <div class="mast-qr-box"><div id="qr-mast" style="line-height:0;"></div></div>
      <div class="mast-qr-lbl">dailywatch</div>
    </div>
  </div>
</div>

<div class="ticker-bar">
  <div class="ticker-inner">
    {ticker_items}{ticker_items}
  </div>
</div>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">Bulletin du {date_fr} · Données de clôture veille · yfinance</div>
    <div class="hero-hl">Bulletin de marché — Portefeuille &amp; surveillance</div>
    <div class="hero-kpis">
      <div class="hkpi">
        <span class="hkpi-v">${total_val:,.0f}</span>
        <span class="hkpi-l">Valeur portefeuille</span>
      </div>
      <div class="hkpi">
        <span class="hkpi-v" style="color:{'#4ade80' if total_pnl >= 0 else '#f87171'};">{pnl_sign}{total_pnl:,.0f} $</span>
        <span class="hkpi-l">P&amp;L latent total</span>
      </div>
      <div class="hkpi">
        <span class="hkpi-v">{date_str}</span>
        <span class="hkpi-l">Date bulletin</span>
      </div>
      <div class="hkpi">
        <span class="hkpi-v">07h00</span>
        <span class="hkpi-l">Heure génération</span>
      </div>
    </div>
  </div>
</div>

<div class="content">

  <div class="nav-links">
    <a class="nav-link" href="../index.html">← Accueil</a>
    <a class="nav-link" href="archive.html">Archive complète</a>
    <a class="nav-link" href="../yaasap_spcx_position.html">Position SPCX</a>
    <a class="nav-link" href="../yaasap_lvmh.html">LVMH</a>
    <a class="nav-link" href="../yaasap_ttwo.html">TTWO</a>
  </div>

  <div class="sec-rule"><span class="sec-rule-text">Portefeuille · Positions ouvertes au {date_fr}</span></div>
  <div class="portfolio-summary">
    <div class="ps-item">
      <span class="ps-v">${total_val:,.0f}</span>
      <span class="ps-l">Valeur totale</span>
    </div>
    <div class="ps-item">
      <span class="ps-v" style="color:{pnl_col_total};">{pnl_sign}{total_pnl:,.0f} $</span>
      <span class="ps-l">P&amp;L latent</span>
    </div>
    <div class="ps-item">
      <span class="ps-v" style="color:{pnl_col_total};">{pnl_sign}{(total_pnl/total_val*100 if total_val else 0):.1f}%</span>
      <span class="ps-l">Performance</span>
    </div>
  </div>

  <table class="data-table">
    <thead>
      <tr>
        <th>Ticker</th><th>Valeur</th><th>Cours</th><th>Variation</th><th>PRU × Qté</th><th>P&amp;L latent</th>
      </tr>
    </thead>
    <tbody>{pos_rows}</tbody>
  </table>

  <div class="sec-rule"><span class="sec-rule-text">Surveillance · Valeurs suivies</span></div>
  <table class="data-table">
    <thead>
      <tr><th>Ticker</th><th>Valeur</th><th>Cours</th><th>Variation</th></tr>
    </thead>
    <tbody>{watch_rows}</tbody>
  </table>

  <div class="sec-rule"><span class="sec-rule-text">Marchés · Indices &amp; commodités</span></div>
  <table class="data-table">
    <thead>
      <tr><th>Indice / Actif</th><th>Niveau</th><th>Variation</th></tr>
    </thead>
    <tbody>{index_rows}</tbody>
  </table>

  <div class="nl-mini">
    <div class="nl-mini-title">Recevoir ce bulletin par email</div>
    <div class="nl-mini-row">
      <input class="nl-mini-input" type="email" id="nlm-email" placeholder="votre@email.com">
      <button class="nl-mini-btn" onclick="nlmSubmit()">S'abonner</button>
    </div>
    <div id="nlm-ok">✅ Inscrit !</div>
    <div class="nl-mini-note">RGPD · Formspree · yaasap.github.io/dailywatch</div>
  </div>

</div>

<footer>
  <div class="foot-brand">YAASAP <em>Notes</em></div>
  <div class="foot-note">Bulletin généré automatiquement le {date_fr} à 07h00 · Par Yacine AOUABED · Ne constitue pas un conseil en investissement</div>
</footer>

<script>
(function tryQR(){{
  var el=document.getElementById('qr-mast');
  if(!el||typeof QRCode==='undefined'){{setTimeout(tryQR,80);return;}}
  new QRCode(el,{{text:'https://yaasap.github.io/dailywatch/index.html',width:48,height:48,colorDark:'#1c1814',colorLight:'#ffffff',correctLevel:QRCode.CorrectLevel.M}});
}})();
function nlmSubmit(){{
  var emailEl=document.getElementById('nlm-email'),email=emailEl?emailEl.value.trim():'';
  if(!email||!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email))return;
  var body=new FormData();body.append('email',email);body.append('source','yaasap-daily-{date_str}');body.append('_next','false');
  fetch('https://formspree.io/f/meewwqep',{{method:'POST',body:body,headers:{{'Accept':'application/json'}}}})
  .then(function(r){{if(r.ok){{var row=emailEl.parentElement;if(row)row.style.display='none';var ok=document.getElementById('nlm-ok');if(ok)ok.style.display='block';}}}});
}}
</script>
</body>
</html>"""
    return html


def update_archive(notes_dir, date_str, date_fr):
    """Met à jour la page d'archive avec toutes les notes."""
    note_files = sorted(
        [f for f in os.listdir(notes_dir) if f.endswith('.html') and f != 'archive.html'],
        reverse=True
    )

    rows = ""
    for fn in note_files:
        try:
            d = datetime.datetime.strptime(fn.replace('.html',''), '%Y-%m-%d')
            date_label = d.strftime('%-d %b %Y')
        except:
            date_label = fn.replace('.html','')
        rows += f'<tr><td><a href="{fn}" style="color:var(--accent);text-decoration:none;font-family:var(--serif);font-weight:700;">{date_label}</a></td><td style="font-family:var(--mono);font-size:11px;color:var(--ink4);">{fn}</td></tr>\n'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>YAASAP Notes · Archive des bulletins quotidiens</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Source+Sans+3:wght@300;400;600;700&family=Source+Code+Pro:wght@400;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{--paper:#f9f6f0;--paper2:#f2ede4;--ink:#1c1814;--ink4:#9a8f82;--rule:rgba(0,0,0,0.12);--rule2:rgba(0,0,0,0.07);--accent:#8b3a1a;--serif:'Libre Baskerville',Georgia,serif;--sans:'Source Sans 3',Arial,sans-serif;--mono:'Source Code Pro','Courier New',monospace;}}
html,body{{background:var(--paper);font-family:var(--sans);color:var(--ink);font-size:15px;}}
.masthead{{background:var(--ink);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px double rgba(255,255,255,.15);}}
.pub-name{{font-family:var(--serif);font-size:22px;font-weight:700;color:#fff;}}
.pub-name em{{font-style:italic;color:var(--accent);}}
.content{{max-width:640px;margin:0 auto;padding:28px 24px 48px;}}
.sec-rule{{display:flex;align-items:center;gap:8px;margin:0 0 16px;}}
.sec-rule::before{{content:'';width:20px;height:2px;background:var(--accent);flex-shrink:0;}}
.sec-rule-text{{font-size:8px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);font-family:var(--sans);}}
.sec-rule::after{{content:'';flex:1;height:1px;background:var(--rule);}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--rule);border-radius:2px;box-shadow:0 1px 4px rgba(0,0,0,.05);}}
th{{font-size:8px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink4);padding:8px 14px;text-align:left;border-bottom:1.5px solid var(--ink);background:var(--paper2);font-family:var(--sans);}}
td{{padding:8px 14px;border-bottom:1px solid var(--rule2);font-family:var(--sans);font-size:13px;}}
tr:last-child td{{border-bottom:none;}}
tr:hover td{{background:var(--paper2);}}
.back-link{{display:inline-block;margin-bottom:20px;font-family:var(--sans);font-size:12px;color:var(--accent);text-decoration:none;font-weight:700;}}
</style>
</head>
<body>
<div class="masthead">
  <div class="pub-name">YAASAP <em>Notes</em></div>
  <span style="font-family:var(--mono);font-size:9px;color:rgba(255,255,255,.35);letter-spacing:.1em;text-transform:uppercase;">Archive · Bulletins quotidiens</span>
</div>
<div class="content">
  <a class="back-link" href="../index.html">← Retour à l'accueil</a>
  <div class="sec-rule"><span class="sec-rule-text">Archive · {len(note_files)} bulletins · Du plus récent au plus ancien</span></div>
  <table>
    <thead><tr><th>Date</th><th>Fichier</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
</body>
</html>"""

    with open(os.path.join(notes_dir, 'archive.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✓ archive.html mis à jour ({len(note_files)} bulletins)")


def update_index_daily(notes_dir, date_str, date_fr, note_filename):
    """
    Injecte la dernière note quotidienne en tête de l'index.html principal.
    Remplace le bloc entre les marqueurs <!-- DAILY_NOTE_START --> et <!-- DAILY_NOTE_END -->.
    """
    index_path = 'index.html'
    if not os.path.exists(index_path):
        print("  ⚠ index.html non trouvé — skip mise à jour index")
        return

    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_block = f"""<!-- DAILY_NOTE_START -->
<div class="note-une" style="border-top-color:#1e5c32;">
  <div class="une-body">
    <div class="une-eyebrow" style="color:#1e5c32;">⚡ Bulletin automatique · {date_fr} · Généré à 07h00</div>
    <div class="une-title">Bulletin quotidien du {date_fr} — Portefeuille &amp; marchés en temps réel</div>
    <div class="une-desc">Cours de clôture · P&L latent mis à jour · Indices &amp; commodités · Généré automatiquement via yfinance</div>
    <a href="./notes/{note_filename}" class="une-link" style="background:#1e5c32;">Voir le bulletin →</a>
  </div>
  <div class="une-meta">
    <div class="une-date">{date_fr}</div>
    <div class="une-badge" style="background:rgba(30,92,50,.25);border-color:rgba(30,92,50,.5);color:#4ade80;">Auto</div>
  </div>
</div>
<!-- DAILY_NOTE_END -->"""

    import re
    if '<!-- DAILY_NOTE_START -->' in content:
        content = re.sub(
            r'<!-- DAILY_NOTE_START -->.*?<!-- DAILY_NOTE_END -->',
            new_block,
            content,
            flags=re.DOTALL
        )
    else:
        # Insérer après la première .sec-rule (section "Dernière publication")
        content = content.replace(
            '<div class="note-une"',
            new_block + '\n<div class="note-une"',
            1
        )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  ✓ index.html mis à jour avec le bulletin du {date_fr}")


def main():
    # Dates
    tz_paris = datetime.timezone(datetime.timedelta(hours=2))  # CEST
    now = datetime.datetime.now(tz_paris)
    date_str = now.strftime('%Y-%m-%d')
    mois = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
    date_fr = f"{now.day} {mois[now.month-1]} {now.year}"

    print(f"\n=== YAASAP Notes · Bulletin quotidien · {date_fr} ===\n")
    print("1. Récupération des données de marché...")
    data = fetch_data()

    print("\n2. Génération du HTML...")
    html = generate_html(data, date_str, date_fr)

    print("\n3. Écriture du fichier...")
    notes_dir = 'notes'
    os.makedirs(notes_dir, exist_ok=True)
    note_filename = f"{date_str}.html"
    note_path = os.path.join(notes_dir, note_filename)
    with open(note_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✓ {note_path}")

    print("\n4. Mise à jour de l'archive...")
    update_archive(notes_dir, date_str, date_fr)

    print("\n5. Mise à jour de l'index principal...")
    update_index_daily(notes_dir, date_str, date_fr, note_filename)

    print(f"\n✅ Bulletin du {date_fr} généré avec succès !")

if __name__ == '__main__':
    main()

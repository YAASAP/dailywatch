#!/usr/bin/env python3
import os, sys, datetime, requests, glob
import anthropic

NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
TODAY         = datetime.date.today()
NOW           = datetime.datetime.now()
DATE_STR      = TODAY.strftime("%d %B %Y")
NUM           = TODAY.strftime("%d/%m/%Y")
TIMESTAMP     = NOW.strftime("%Y-%m-%d_%H%M")
DOCS_DIR      = os.path.join(os.path.dirname(__file__), "..", "docs")
ROOT_DIR      = os.environ.get(
    "GITHUB_WORKSPACE",
    os.path.join(os.path.dirname(__file__), "..")
)

# ── Analyses sectorielles statiques présentes dans le repo ──
ANALYSES = [
    ("yaasap_baba_v2.html",       "Alibaba (BABA) — Analyse d'investissement complète",        "Achat progressif · Stop-loss $112 · Cible $191 · Guide novices"),
    ("yaasap_poutine_xi.html",    "Poutine & Xi — Grand échiquier 2026",                        "Ukraine · Iran · Israël · Commerce mondial · Scénarios"),
    ("yaasap_midterms.html",      "Midterms 2026 — Trump sans Congrès : l'arsenal résiduel",    "Tarifs · Guerre Iran · Fed · Scénarios marchés"),
    ("yaasap_spatial_live.html",  "Secteur Spatial — SpaceX IPO · Cotations live",              "N°18 · RKLB · ASTS · LUNR · Corrélations"),
    ("yaasap_oil_gas.html",       "Oil & Gas — TotalEnergies · Majors pétrolières",              "N°17 · Brent · Ormuz · Strategika · Machiavel"),
    ("yaasap_ecosysteme_ia.html", "Ecosystème IA — LLMs · GPU · Stockage",                      "N°15 · Claude · NVDA · OpenAI · DeepSeek"),
    ("yaasap_value.html",         "Actions sous-cotées — PER bas · Fondamentaux solides",        "N°16 · MSFT · PFE · BABA · VZ"),
    ("yaasap_gta6_light.html",    "GTA VI — Cartographie boursière",                            "N°13 · TTWO · SONY · NVDA · Corrélations"),
    ("yaasap_v3_paysage.html",    "Flash Marché MRNA — Bandes de Bollinger",                    "N°12 · Moderna · Scénarios trading"),
    ]

# ─────────────────────────────────────────────
# 1. FETCH NEWS
# ─────────────────────────────────────────────
def fetch_news():
    articles = []
    queries = [
        "FIFA World Cup 2026 host economy sponsors",
        "financial markets stocks earnings results",
        "BNP research",
        "currency exchange EUR USD",
        "VIX INDEX",
        "mergers acquisitions IPO deals 2026",
        "geopolitics trade war tariffs sanctions",
        "Africa emerging markets economy growth 2026",
        "Nigeria Kenya Ethiopia GDP investment",
        "BRICS emerging economies trade currency",
        "IMF World Bank Africa development loans",
        "commodity prices copper lithium cobalt Africa",
    ]
    for q in queries:
        try:
            r = requests.get("https://newsapi.org/v2/everything", params={
                "q": q, "sortBy": "publishedAt", "pageSize": 5,
                "from": (TODAY - datetime.timedelta(days=3)).isoformat(),
                "apiKey": NEWSAPI_KEY
            }, timeout=10)
            data = r.json()
            if data.get("status") == "ok":
                articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"Erreur fetch '{q}': {e}")
    seen, unique = set(), []
    for a in articles:
        u = a.get("url", "")
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    print(f"{len(unique)} articles recuperes")
    return unique

def format_articles(articles):
    lines = []
    for i, a in enumerate(articles[:30], 1):
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
        img  = a.get("urlToImage", "")
        src  = a.get("source", {}).get("name", "")
        titl = a.get("title", "")
        if img and img.startswith("http") and len(imgs) < n:
            imgs.append({"url": img, "source": src, "title": titl[:60]})
    return imgs

def get_sources(articles):
    seen, sources = set(), []
    for a in articles[:20]:
        src  = a.get("source", {}).get("name", "")
        url  = a.get("url", "")
        date = a.get("publishedAt", "")[:10]
        if src and src not in seen:
            seen.add(src)
            sources.append({"name": src, "url": url, "date": date})
    return sources[:8]

# ─────────────────────────────────────────────
# 2. TEMPLATE HTML NOTE QUOTIDIENNE
# ─────────────────────────────────────────────
TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes - DATE_PH</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
:root{
  --ink:#1c1814;--ink2:#3a342c;--ink3:#6a5f52;--muted:#9a8f82;
  --paper:#f9f6f0;--paper2:#f2ede4;--paper3:#e8e1d5;
  --red:#8b1a1a;--green:#1e5c32;--amber:#8a5c00;--gold:#f0c956;
}
html{scroll-behavior:smooth;}
body{background:var(--paper);font-family:Georgia,'Times New Roman',serif;color:var(--ink);font-size:16px;line-height:1.6;-webkit-text-size-adjust:100%;}
.mast{background:var(--ink);padding:16px 20px 12px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3);}
.mast-inner{display:flex;align-items:center;justify-content:space-between;max-width:680px;margin:0 auto;}
.mast-brand{font-size:22px;font-weight:700;font-style:italic;color:#fff;letter-spacing:-.02em;}
.mast-brand span{color:var(--red);}
.mast-right{text-align:right;}
.mast-date{font-size:11px;color:rgba(255,255,255,.55);font-weight:600;}
.mast-brent{font-size:12px;font-weight:700;color:var(--gold);}
.hero{position:relative;width:100%;height:200px;overflow:hidden;}
.hero img{width:100%;height:200px;object-fit:cover;display:block;filter:brightness(.75);}
.hero-overlay{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(28,24,20,.85));padding:16px 20px;}
.hero-tag{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:700;margin-bottom:4px;}
.hero-title{font-size:18px;font-weight:700;color:#fff;line-height:1.25;}
.hero-caption{font-size:10px;color:rgba(255,255,255,.55);margin-top:4px;font-style:italic;}
.kicker{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--paper2);border-bottom:1px solid rgba(0,0,0,.1);}
.kicker::-webkit-scrollbar{display:none;}
.kicker-inner{display:flex;padding:0 12px;min-width:max-content;}
.kk{padding:10px 14px;border-right:1px solid rgba(0,0,0,.08);flex-shrink:0;}
.kk:last-child{border-right:none;}
.kk-l{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:2px;}
.kk-v{font-size:15px;font-weight:700;color:var(--ink);line-height:1;}
.kk-n{font-size:10px;color:var(--muted);font-style:italic;margin-top:1px;}
.up{color:var(--green);}.dn{color:var(--red);}.am{color:var(--amber);}
.content{max-width:680px;margin:0 auto;padding:0 20px 40px;}
.sec{display:flex;align-items:center;gap:10px;margin:24px 0 14px;}
.sec::before{content:'';width:20px;height:2px;background:var(--red);flex-shrink:0;}
.sec-t{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--red);}
.sec::after{content:'';flex:1;height:1px;background:rgba(0,0,0,.1);}
.signal{background:#fff;border:1px solid rgba(0,0,0,.08);border-left:3px solid var(--red);border-radius:0 4px 4px 0;padding:16px 18px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.signal-label{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--red);font-weight:700;margin-bottom:6px;}
.signal-headline{font-size:19px;font-weight:700;line-height:1.2;margin-bottom:8px;color:var(--ink);}
.signal-deck{font-size:13px;font-style:italic;color:var(--ink3);line-height:1.5;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(0,0,0,.06);}
.signal-body{font-size:13px;color:var(--ink2);line-height:1.65;}
.signal-body strong{font-weight:700;color:var(--ink);}
.signal-body p{margin-bottom:8px;}
.pull{border-top:2px solid var(--red);border-bottom:1px solid rgba(0,0,0,.1);padding:10px 14px;margin:14px 0;}
.pull-t{font-size:14px;font-style:italic;line-height:1.45;color:var(--ink);}
.pull-a{font-size:10px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-top:5px;}
.art{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:4px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.art-sector{font-size:9px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;margin-bottom:5px;}
.art-h{font-size:15px;font-weight:700;color:var(--ink);line-height:1.25;margin-bottom:6px;}
.art-b{font-size:12.5px;color:var(--ink3);line-height:1.55;}
.art-b strong{color:var(--ink);font-weight:700;}
.hero2{position:relative;width:100%;height:160px;overflow:hidden;border-radius:4px;margin:16px 0;}
.hero2 img{width:100%;height:160px;object-fit:cover;filter:brightness(.8);}
.hero2-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(28,24,20,.7);padding:8px 12px;font-size:10px;color:rgba(255,255,255,.8);font-style:italic;}
.table-wrap{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:4px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.table-wrap table{width:100%;border-collapse:collapse;}
.table-wrap th{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);padding:8px 12px;text-align:left;border-bottom:1.5px solid var(--ink);background:var(--paper2);}
.table-wrap td{font-size:12.5px;padding:8px 12px;border-bottom:1px solid rgba(0,0,0,.06);color:var(--ink2);}
.table-wrap tr:last-child td{border-bottom:none;}
.badge-up{background:rgba(30,92,50,.1);color:var(--green);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}
.badge-dn{background:rgba(139,26,26,.1);color:var(--red);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}
.badge-am{background:rgba(138,92,0,.1);color:var(--amber);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}
.verdict{background:var(--ink);border-radius:4px;padding:16px 18px;margin:24px 0;}
.v-tag{background:var(--red);color:#fff;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;padding:3px 8px;border-radius:2px;display:inline-block;margin-bottom:10px;}
.v-t{font-size:13px;color:rgba(255,255,255,.88);font-style:italic;line-height:1.6;}
.v-t strong{font-style:normal;color:var(--gold);}
.sources{background:var(--paper2);border-radius:4px;padding:12px 16px;margin:16px 0;}
.sources-label{font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--red);margin-bottom:8px;}
.src-list{display:flex;flex-wrap:wrap;gap:6px;}
.src-pill{font-size:10px;color:var(--ink3);background:#fff;border:1px solid rgba(0,0,0,.1);border-radius:12px;padding:3px 10px;text-decoration:none;font-style:italic;}
footer{background:var(--paper2);border-top:1px solid rgba(0,0,0,.1);padding:16px 20px;text-align:center;}
.foot-brand{font-size:16px;font-weight:700;font-style:italic;color:var(--ink);margin-bottom:4px;}
.foot-brand span{color:var(--red);}
.foot-note{font-size:10px;color:var(--muted);font-style:italic;}
.foot-nav{display:flex;justify-content:center;gap:16px;margin-top:10px;flex-wrap:wrap;}
.foot-nav a{font-size:11px;color:var(--red);text-decoration:none;}
@media(min-width:640px){.hero{height:260px;}.hero img{height:260px;}.hero-title{font-size:22px;}}
</style>
</head>
<body>
<div class="mast">
  <div class="mast-inner">
    <div class="mast-brand">YAASAP <span>Notes</span></div>
    <div class="mast-right">
      <div class="mast-date" id="liveDate">DATE_PH</div>
      <div class="mast-brent">BRENT_PH</div>
    </div>
  </div>
</div>
HERO1_PH
<div class="kicker"><div class="kicker-inner">KICKER_PH</div></div>
<div class="content">
  <div class="sec"><span class="sec-t">Signal du jour</span></div>
  SIGNAL_PH
  <div class="sec"><span class="sec-t">Analyses sectorielles</span></div>
  ARTICLES_PH
  HERO2_PH
  <div class="sec"><span class="sec-t">Valeurs a surveiller</span></div>
  <div class="table-wrap">TABLE_PH</div>
  <div class="verdict"><div class="v-tag">Verdict YAASAP</div><div class="v-t">VERDICT_PH</div></div>
  SOURCES_PH
</div>
<footer>
  <div class="foot-brand">YAASAP <span>Notes</span></div>
  <div class="foot-note">Par <strong>Yacine AOUABED</strong> &middot; NOTE_NUM_PH &middot; <span id="liveDateFooter">DATE_PH</span><br>Analyse informative uniquement &mdash; Ne constitue pas un conseil en investissement</div>
  <div class="foot-nav">
    <a href="../index.html">Accueil</a>
    <a href="index.html">Archives</a>
    <a href="../yaasap_spatial_live.html">Spatial</a>
    <a href="../yaasap_oil_gas.html">Oil &amp; Gas</a>
    <a href="../yaasap_ecosysteme_ia.html">IA</a>
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
})();
</script>
</body>
</html>"""

SYSTEM = """Tu es l'analyste senior de YAASAP Notes, publication financiere style Financial Times.
Tu remplis un template HTML en remplacant les placeholders par du vrai contenu editorial.
Secteurs couverts : Coupe du Monde 2026 (impacts economiques, sponsors, droits TV, tourisme),
marches financiers (resultats, fusions-acquisitions, IPO), banques centrales (Fed, BCE, taux),
geopolitique commerciale (tarifs, sanctions, conflits), valeurs a surveiller.
Style editorial presse financiere serieuse. Analyses tranchees et actionnables.
Tu reponds UNIQUEMENT avec le HTML complet, sans backticks, sans texte avant ou apres."""

# ─────────────────────────────────────────────
# 3. GENERATION HTML VIA CLAUDE
# ─────────────────────────────────────────────
def generate_html(text, images, sources):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    hero1_html = ""
    hero2_html = ""
    if len(images) >= 1:
        img = images[0]
        hero1_html = (
            f'<div class="hero">'
            f'<img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'">'
            f'<div class="hero-overlay">'
            f'<div class="hero-tag">A la une</div>'
            f'<div class="hero-title">HEADLINE_FROM_SIGNAL</div>'
            f'<div class="hero-caption">{img["source"]}</div>'
            f'</div></div>'
        )
    if len(images) >= 2:
        img = images[1]
        hero2_html = (
            f'<div class="hero2">'
            f'<img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'">'
            f'<div class="hero2-caption">{img["source"]} &mdash; {img["title"]}</div>'
            f'</div>'
        )

    sources_html = ""
    if sources:
        pills = "".join(
            f'<a href="{s["url"]}" target="_blank" class="src-pill">{s["name"]}</a>'
            for s in sources
        )
        sources_html = (
            f'<div class="sources">'
            f'<div class="sources-label">Sources</div>'
            f'<div class="src-list">{pills}</div>'
            f'</div>'
        )

    template = TEMPLATE.replace("HERO1_PH", hero1_html)\
                       .replace("HERO2_PH", hero2_html)\
                       .replace("SOURCES_PH", sources_html)

    prompt = f"""Articles du {DATE_STR} :

{text}

Remplace CHAQUE placeholder par du contenu editorial reel. HTML complet uniquement.

PLACEHOLDERS :
DATE_PH = {DATE_STR}
NOTE_NUM_PH = Note du {NUM}
BRENT_PH = cours Brent du jour ex: 110$ +2.1pct
HEADLINE_FROM_SIGNAL = titre court 8 mots max pour la photo hero
KICKER_PH = 6 blocs :
  <div class="kk"><div class="kk-l">LABEL</div><div class="kk-v up">VALEUR</div><div class="kk-n">note</div></div>
SIGNAL_PH = signal principal :
  <div class="signal"><div class="signal-label">Analyse principale</div><div class="signal-headline">TITRE</div><div class="signal-deck">sous-titre italique</div><div class="signal-body"><p>paragraphe 1</p><p>paragraphe 2</p></div><div class="pull"><div class="pull-t">citation</div><div class="pull-a">source</div></div></div>
ARTICLES_PH = 3 articles sectoriels :
  <div class="art"><div class="art-sector up">SECTEUR</div><div class="art-h">titre</div><div class="art-b">analyse avec <strong>mots cles</strong></div></div>
TABLE_PH = tableau :
  <table><thead><tr><th>Ticker</th><th>Valeur</th><th>Signal</th><th>Direction</th></tr></thead><tbody><tr><td>TICK</td><td>Nom</td><td>Signal</td><td><span class="badge-up">HAUSSE</span></td></tr></tbody></table>
VERDICT_PH = 2-3 phrases synthese avec <strong>points cles</strong>

TEMPLATE :
{template}"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    html = msg.content[0].text
    if "```" in html:
        for p in html.split("```"):
            s = p.strip()
            if s.startswith("<!") or s.startswith("<html"):
                return s
        html = html.split("```")[1]
        if html.startswith("html\n"):
            html = html[5:]
    return html.strip()

# ─────────────────────────────────────────────
# 4. INDEX DOCS/ (archives notes quotidiennes)
# ─────────────────────────────────────────────
def build_docs_index():
    pattern = os.path.join(DOCS_DIR, "note-2*.html")
    note_files = sorted(glob.glob(pattern), reverse=True)

    items = ""
    for n in note_files:
        name = os.path.basename(n)
        raw  = name.replace("note-", "").replace(".html", "")
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
            label = raw
            is_today = False
        badge = '<span class="badge">Aujourd\'hui</span>' if is_today else '<span class="dash">—</span>'
        items += f'<li>{badge}<a href="{name}">{label}</a></li>\n'

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes — Archives</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:Georgia,serif;background:#f9f6f0;color:#1c1814;}}
.mast{{background:#1c1814;padding:14px 20px;text-align:center;}}
.pub{{font-size:26px;font-weight:700;font-style:italic;color:#fff;letter-spacing:-.02em;}}
.pub span{{color:#8b1a1a;}}
.tagline{{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-top:3px;}}
.container{{max-width:600px;margin:0 auto;padding:20px 20px 60px;}}
.sec{{font-size:9px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8b1a1a;border-bottom:1px solid #8b1a1a;padding-bottom:4px;margin:24px 0 14px;}}
.today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid #8b1a1a;padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0 4px 4px 0;}}
.today-box a{{font-size:17px;font-weight:700;color:#1c1814;text-decoration:none;display:block;line-height:1.3;}}
.today-box a:hover{{color:#8b1a1a;}}
.today-date{{font-size:10px;color:#9a8f82;font-style:italic;margin-top:5px;}}
ul{{list-style:none;padding:0;}}
li{{padding:9px 0;border-bottom:1px solid rgba(0,0,0,.07);display:flex;align-items:center;gap:10px;}}
li:last-child{{border-bottom:none;}}
li a{{font-size:14px;color:#1c1814;text-decoration:none;}}
li a:hover{{color:#8b1a1a;}}
.badge{{font-size:9px;background:#8b1a1a;color:#fff;padding:2px 7px;border-radius:2px;flex-shrink:0;}}
.dash{{color:#8b1a1a;font-size:14px;flex-shrink:0;}}
footer{{background:#f2ede4;border-top:1px solid rgba(0,0,0,.1);padding:14px 20px;text-align:center;font-size:10px;color:#9a8f82;font-style:italic;}}
.back{{font-size:12px;color:#8b1a1a;text-decoration:none;display:inline-block;margin-bottom:8px;}}
</style>
</head>
<body>
<div class="mast">
  <div class="pub">YAASAP <span>Notes</span></div>
  <div class="tagline">Archives — Notes quotidiennes</div>
</div>
<div class="container">
  <a class="back" href="../index.html">← Retour accueil</a>
  <div class="sec">Note du jour</div>
  <div class="today-box">
    <a href="note-du-jour.html">Analyse du jour &mdash; {DATE_STR}</a>
    <div class="today-date" id="liveDate">{DATE_STR}</div>
  </div>
  <div class="sec">Toutes les archives ({len(note_files)} notes)</div>
  <ul>{items}</ul>
</div>
<footer>YAASAP Notes &middot; Par Yacine AOUABED &middot; Ne constitue pas un conseil en investissement</footer>
<script>
(function(){{
  var d=new Date();
  var opts={{weekday:'long',year:'numeric',month:'long',day:'numeric'}};
  var el=document.getElementById('liveDate');
  if(el) el.textContent=d.toLocaleDateString('fr-FR',opts);
}})();
</script>
</body>
</html>"""
    path = os.path.join(DOCS_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK docs/index.html — {len(note_files)} archives")

# ─────────────────────────────────────────────
# 5. INDEX RACINE (toutes les analyses)
# ─────────────────────────────────────────────
def build_root_index():
    # Scanner tous les fichiers yaasap_*.html a la racine du repo
    pattern = os.path.join(ROOT_DIR, "yaasap_*.html")
    found_files = sorted(glob.glob(pattern), reverse=True)
    print(f"ROOT_DIR = {ROOT_DIR}")
    print(f"Fichiers trouves : {[os.path.basename(f) for f in found_files]}")

    # Dictionnaire titre+meta pour les fichiers connus
    KNOWN = {f: (t, m) for f, t, m in ANALYSES}

    analyses_items = ""
    for i, fpath in enumerate(found_files):
        fname = os.path.basename(fpath)
        if fname in KNOWN:
            title, meta = KNOWN[fname]
        else:
            # Fichier inconnu : generer un titre lisible depuis le nom
            title = fname.replace("yaasap_","").replace(".html","").replace("_"," ").title()
            meta  = "Analyse YAASAP Notes"
        badge = '<span class="badge-new">Nouveau</span>' if i < 3 else ''
        analyses_items += f"""    <li class="note-item">
      <span class="note-bullet">&mdash;</span>
      <div>
        <a class="note-link" href="{fname}">{title}{badge}</a>
        <span class="li-meta">{meta}</span>
      </div>
    </li>\n"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YAASAP Notes</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,700;1,400&family=Source+Sans+3:wght@400;600;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
:root{{
  --paper:#f9f6f0;--paper2:#f2ede4;--paper3:#e8e1d5;
  --ink:#1c1814;--ink2:#3a342c;--ink3:#6a5f52;--ink4:#9a8f82;
  --rule:rgba(0,0,0,0.12);--rule2:rgba(0,0,0,0.07);
  --accent:#8b3a1a;
  --serif:'Libre Baskerville',Georgia,serif;
  --sans:'Source Sans 3',system-ui,sans-serif;
}}
body{{background:var(--paper);font-family:var(--sans);color:var(--ink);font-size:15px;-webkit-font-smoothing:antialiased;}}
.masthead{{border-bottom:3px double var(--rule);padding:20px 32px 14px;text-align:center;background:var(--paper);}}
.pub-name{{font-family:var(--serif);font-size:42px;font-weight:700;letter-spacing:-0.02em;line-height:1;}}
.pub-name em{{font-style:italic;color:var(--accent);}}
.pub-rule{{display:flex;align-items:center;gap:12px;margin:10px 0 6px;justify-content:center;}}
.pub-rule::before,.pub-rule::after{{content:'';flex:1;max-width:100px;height:1px;background:var(--ink);}}
.pub-tagline{{font-size:9px;letter-spacing:0.22em;text-transform:uppercase;color:var(--ink4);}}
.pub-date{{font-family:var(--serif);font-size:11px;color:var(--ink4);font-style:italic;margin-top:4px;}}
.container{{max-width:720px;margin:0 auto;padding:24px 24px 60px;}}
.sec{{font-size:9px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--accent);padding-bottom:4px;margin:28px 0 14px;display:flex;align-items:center;gap:8px;}}
.sec::after{{content:'';flex:1;}}
.today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid var(--accent);padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0 3px 3px 0;}}
.today-box a{{font-family:var(--serif);font-size:17px;font-weight:700;color:var(--ink);text-decoration:none;display:block;line-height:1.3;}}
.today-box a:hover{{color:var(--accent);}}
.today-meta{{font-size:10px;color:var(--ink4);font-style:italic;margin-top:5px;}}
ul.note-list{{list-style:none;padding:0;margin-bottom:28px;}}
ul.note-list li{{display:flex;align-items:baseline;gap:10px;padding:9px 0;border-bottom:1px solid var(--rule2);}}
ul.note-list li:last-child{{border-bottom:none;}}
ul.note-list li::before{{content:'&mdash;';color:var(--accent);flex-shrink:0;font-size:14px;}}
.note-link{{font-family:var(--serif);font-size:15px;color:var(--ink);text-decoration:none;line-height:1.3;}}
.note-link:hover{{color:var(--accent);}}
.li-meta{{font-size:10px;color:var(--ink4);font-style:italic;display:block;margin-top:2px;}}
.badge-new{{font-size:8px;font-weight:700;background:var(--accent);color:#fff;padding:1px 5px;border-radius:2px;margin-left:6px;letter-spacing:.05em;vertical-align:middle;}}
.archive-link{{display:inline-block;font-family:var(--serif);font-size:13px;color:var(--accent);text-decoration:none;border:1px solid var(--accent);padding:5px 12px;border-radius:2px;margin-top:6px;}}
.archive-link:hover{{background:var(--accent);color:#fff;}}
footer{{background:var(--paper2);border-top:1.5px solid var(--rule);padding:14px 32px;text-align:center;font-size:10px;color:var(--ink4);font-style:italic;}}
footer strong{{color:var(--ink3);font-style:normal;}}
</style>
</head>
<body>
<div class="masthead">
  <div class="pub-name">YAASAP <em>Notes</em></div>
  <div class="pub-rule"><span class="pub-tagline">Analyse financiere quotidienne &mdash; Petrole &middot; Geopolitique &middot; IA &middot; Pharma &middot; IT</span></div>
  <div class="pub-date" id="pubDate"></div>
</div>
<div class="container">

  <div class="sec">Note du jour</div>
  <div class="today-box">
    <a href="docs/note-du-jour.html">Analyse quotidienne &mdash; Petrole &middot; Geopolitique &middot; IA &middot; Pharma &middot; IT</a>
    <div class="today-meta" id="todayMeta"></div>
  </div>
  <a class="archive-link" href="docs/index.html">Voir toutes les archives ({DATE_STR}) &rarr;</a>

  <div class="sec">Analyses sectorielles</div>
  <ul class="note-list">
{analyses_items}  </ul>

</div>
<footer>YAASAP Notes &nbsp;&middot;&nbsp; Par <strong>Yacine AOUABED</strong> &nbsp;&middot;&nbsp; Analyse informative uniquement &nbsp;&middot;&nbsp; Ne constitue pas un conseil en investissement</footer>
<script>
(function(){{
  var d=new Date();
  var opts={{weekday:'long',year:'numeric',month:'long',day:'numeric'}};
  var s=d.toLocaleDateString('fr-FR',opts);
  var p=document.getElementById('pubDate');
  var t=document.getElementById('todayMeta');
  if(p) p.textContent=s;
  if(t) t.textContent=s;
}})();
</script>
</body>
</html>"""
    path = os.path.join(ROOT_DIR, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK index.html racine mis a jour")

# ─────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────
def main():
    print(f"\n{'='*52}")
    print(f"YAASAP Notes — Generation {TIMESTAMP}")
    print(f"{'='*52}\n")

    os.makedirs(DOCS_DIR, exist_ok=True)

    # Fetch
    articles = fetch_news()
    if not articles:
        print("Aucun article recupere — arret")
        sys.exit(1)

    images  = get_top_images(articles, n=2)
    sources = get_sources(articles)
    print(f"{len(images)} images, {len(sources)} sources")

    # Generer le HTML
    html = generate_html(format_articles(articles), images, sources)

    # Sauvegarder avec timestamp (plusieurs notes par jour possibles)
    note_ts   = os.path.join(DOCS_DIR, f"note-{TIMESTAMP}.html")
    note_day  = os.path.join(DOCS_DIR, "note-du-jour.html")

    with open(note_ts, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK archive : note-{TIMESTAMP}.html")

    with open(note_day, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK note-du-jour.html")

    # Reconstruire les deux index
    build_docs_index()
    build_root_index()

    print(f"\nPublie : https://YAASAP.github.io/dailywatch/")

if __name__ == "__main__":
    main()

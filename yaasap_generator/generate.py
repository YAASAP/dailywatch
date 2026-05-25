#!/usr/bin/env python3
import os, sys, datetime, requests, glob
import anthropic

NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
TODAY         = datetime.date.today()
DATE_STR      = TODAY.strftime("%d %B %Y")
NUM           = TODAY.strftime("%d/%m/%Y")
DOCS_DIR      = os.path.join(os.path.dirname(__file__), "..", "docs")

def fetch_news():
    articles = []
    for q in ["oil gas brent","geopolitics Iran China","artificial intelligence AI","pharma FDA biotech","technology semiconductor"]:
        try:
            r = requests.get("https://newsapi.org/v2/everything",
                params={"q":q,"sortBy":"publishedAt","pageSize":5,
                        "from":(TODAY - datetime.timedelta(days=2)).isoformat(),
                        "apiKey":NEWSAPI_KEY},
                timeout=10)
            data = r.json()
            if data.get("status") == "ok":
                articles.extend(data.get("articles",[]))
        except Exception as e:
            print(f"Erreur: {e}")
    seen, unique = set(), []
    for a in articles:
        u = a.get("url","")
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    print(f"{len(unique)} articles")
    return unique

def format_articles(articles):
    lines = []
    for i, a in enumerate(articles[:30], 1):
        src  = a.get("source",{}).get("name","?")
        titl = a.get("title","")
        desc = (a.get("description","") or "")[:150]
        date = a.get("publishedAt","")[:10]
        url  = a.get("url","")
        img  = a.get("urlToImage","") or ""
        lines.append(f"{i}. [{src} {date}] {titl}\n   {desc}\n   URL: {url}\n   IMG: {img}")
    return "\n\n".join(lines)

def get_top_images(articles, n=2):
    imgs = []
    for a in articles:
        img  = a.get("urlToImage","")
        src  = a.get("source",{}).get("name","")
        titl = a.get("title","")
        if img and img.startswith("http") and len(imgs) < n:
            imgs.append({"url": img, "source": src, "title": titl[:60]})
    return imgs

def get_sources(articles):
    seen, sources = set(), []
    for a in articles[:20]:
        src  = a.get("source",{}).get("name","")
        url  = a.get("url","")
        date = a.get("publishedAt","")[:10]
        if src and src not in seen:
            seen.add(src)
            sources.append({"name": src, "url": url, "date": date})
    return sources[:8]

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
  --ink:#1c1814; --ink2:#3a342c; --ink3:#6a5f52; --muted:#9a8f82;
  --paper:#f9f6f0; --paper2:#f2ede4; --paper3:#e8e1d5;
  --red:#8b1a1a; --green:#1e5c32; --amber:#8a5c00;
  --gold:#f0c956;
}
html{scroll-behavior:smooth;}
body{background:var(--paper);font-family:Georgia,'Times New Roman',serif;color:var(--ink);font-size:16px;line-height:1.6;-webkit-text-size-adjust:100%;}

/* MASTHEAD */
.mast{background:var(--ink);padding:16px 20px 12px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.3);}
.mast-inner{display:flex;align-items:center;justify-content:space-between;max-width:680px;margin:0 auto;}
.mast-brand{font-size:22px;font-weight:700;font-style:italic;color:#fff;letter-spacing:-.02em;}
.mast-brand span{color:var(--red);}
.mast-date{font-size:11px;color:rgba(255,255,255,.5);text-align:right;line-height:1.3;}
.mast-brent{font-size:12px;font-weight:700;color:var(--gold);}

/* HERO IMAGE */
.hero{position:relative;width:100%;height:200px;overflow:hidden;}
.hero img{width:100%;height:200px;object-fit:cover;display:block;filter:brightness(.75);}
.hero-overlay{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(transparent,rgba(28,24,20,.85));padding:16px 20px;}
.hero-tag{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:var(--gold);font-weight:700;margin-bottom:4px;}
.hero-title{font-size:18px;font-weight:700;color:#fff;line-height:1.25;}
.hero-caption{font-size:10px;color:rgba(255,255,255,.55);margin-top:4px;font-style:italic;}

/* KICKER STRIP */
.kicker{overflow-x:auto;-webkit-overflow-scrolling:touch;background:var(--paper2);border-bottom:1px solid rgba(0,0,0,.1);}
.kicker::-webkit-scrollbar{display:none;}
.kicker-inner{display:flex;padding:0 12px;min-width:max-content;}
.kk{padding:10px 14px;border-right:1px solid rgba(0,0,0,.08);flex-shrink:0;}
.kk:last-child{border-right:none;}
.kk-l{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin-bottom:2px;}
.kk-v{font-size:15px;font-weight:700;color:var(--ink);line-height:1;}
.kk-n{font-size:10px;color:var(--muted);font-style:italic;margin-top:1px;}
.up{color:var(--green);} .dn{color:var(--red);} .am{color:var(--amber);}

/* CONTENT */
.content{max-width:680px;margin:0 auto;padding:0 20px 40px;}

/* SECTION HEADERS */
.sec{display:flex;align-items:center;gap:10px;margin:24px 0 14px;}
.sec::before{content:'';width:20px;height:2px;background:var(--red);flex-shrink:0;}
.sec-t{font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--red);}
.sec::after{content:'';flex:1;height:1px;background:rgba(0,0,0,.1);}

/* SIGNAL DU JOUR */
.signal{background:#fff;border:1px solid rgba(0,0,0,.08);border-left:3px solid var(--red);border-radius:0 4px 4px 0;padding:16px 18px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);}
.signal-label{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--red);font-weight:700;margin-bottom:6px;}
.signal-headline{font-size:19px;font-weight:700;line-height:1.2;margin-bottom:8px;color:var(--ink);}
.signal-deck{font-size:13px;font-style:italic;color:var(--ink3);line-height:1.5;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid rgba(0,0,0,.06);}
.signal-body{font-size:13px;color:var(--ink2);line-height:1.65;}
.signal-body strong{font-weight:700;color:var(--ink);}
.pull{border-top:2px solid var(--red);border-bottom:1px solid rgba(0,0,0,.1);padding:10px 14px;margin:14px 0;}
.pull-t{font-size:14px;font-style:italic;line-height:1.45;color:var(--ink);}
.pull-a{font-size:10px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;margin-top:5px;}

/* ARTICLES */
.art{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:4px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.art-sector{font-size:9px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;margin-bottom:5px;}
.art-h{font-size:15px;font-weight:700;color:var(--ink);line-height:1.25;margin-bottom:6px;}
.art-b{font-size:12.5px;color:var(--ink3);line-height:1.55;}
.art-b strong{color:var(--ink);font-weight:700;}

/* VALEURS TABLE */
.table-wrap{background:#fff;border:1px solid rgba(0,0,0,.08);border-radius:4px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.05);}
.table-wrap table{width:100%;border-collapse:collapse;}
.table-wrap th{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);padding:8px 12px;text-align:left;border-bottom:1.5px solid var(--ink);background:var(--paper2);}
.table-wrap td{font-size:12.5px;padding:8px 12px;border-bottom:1px solid rgba(0,0,0,.06);color:var(--ink2);}
.table-wrap tr:last-child td{border-bottom:none;}
.badge-up{background:rgba(30,92,50,.1);color:var(--green);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}
.badge-dn{background:rgba(139,26,26,.1);color:var(--red);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}
.badge-am{background:rgba(138,92,0,.1);color:var(--amber);font-size:10px;font-weight:700;padding:2px 7px;border-radius:10px;}

/* VERDICT */
.verdict{background:var(--ink);border-radius:4px;padding:16px 18px;margin:24px 0;}
.v-tag{background:var(--red);color:#fff;font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;padding:3px 8px;border-radius:2px;display:inline-block;margin-bottom:10px;}
.v-t{font-size:13px;color:rgba(255,255,255,.88);font-style:italic;line-height:1.6;}
.v-t strong{font-style:normal;color:var(--gold);}

/* SOURCES */
.sources{background:var(--paper2);border-radius:4px;padding:12px 16px;margin:16px 0;}
.sources-label{font-size:9px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--red);margin-bottom:8px;}
.src-list{display:flex;flex-wrap:wrap;gap:6px;}
.src-pill{font-size:10px;color:var(--ink3);background:#fff;border:1px solid rgba(0,0,0,.1);border-radius:12px;padding:3px 10px;text-decoration:none;font-style:italic;}
.src-pill:hover{border-color:var(--red);color:var(--red);}

/* SECOND HERO (image 2) */
.hero2{position:relative;width:100%;height:160px;overflow:hidden;border-radius:4px;margin:16px 0;}
.hero2 img{width:100%;height:160px;object-fit:cover;filter:brightness(.8);}
.hero2-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(28,24,20,.7);padding:8px 12px;font-size:10px;color:rgba(255,255,255,.8);font-style:italic;}

/* FOOTER */
footer{background:var(--paper2);border-top:1px solid rgba(0,0,0,.1);padding:16px 20px;text-align:center;}
.foot-brand{font-size:16px;font-weight:700;font-style:italic;color:var(--ink);margin-bottom:4px;}
.foot-brand span{color:var(--red);}
.foot-note{font-size:10px;color:var(--muted);font-style:italic;line-height:1.5;}
.foot-nav{display:flex;justify-content:center;gap:16px;margin-top:10px;flex-wrap:wrap;}
.foot-nav a{font-size:11px;color:var(--red);text-decoration:none;}
.foot-nav a:hover{text-decoration:underline;}

/* RESPONSIVE DESKTOP */
@media(min-width:640px){
  .mast-brand{font-size:28px;}
  .hero{height:260px;}
  .hero img{height:260px;}
  .hero-title{font-size:22px;}
  .signal-headline{font-size:22px;}
  .art-h{font-size:17px;}
  .art-b{font-size:13.5px;}
  .v-t{font-size:14px;}
}
</style>
</head>
<body>

<!-- MASTHEAD -->
<div class="mast">
  <div class="mast-inner">
    <div class="mast-brand">YAASAP <span>Notes</span></div>
    <div class="mast-date">
      <div id="liveDate">DATE_PH</div>
      <div class="mast-brent">BRENT_PH</div>
    </div>
  </div>
</div>

<!-- HERO IMAGE 1 -->
HERO1_PH

<!-- KICKER STRIP (scroll horizontal) -->
<div class="kicker"><div class="kicker-inner">KICKER_PH</div></div>

<!-- CONTENT -->
<div class="content">

  <!-- SIGNAL DU JOUR -->
  <div class="sec"><span class="sec-t">Signal du jour</span></div>
  SIGNAL_PH

  <!-- ANALYSES SECTORIELLES -->
  <div class="sec"><span class="sec-t">Analyses sectorielles</span></div>
  ARTICLES_PH

  <!-- IMAGE 2 -->
  HERO2_PH

  <!-- VALEURS A SURVEILLER -->
  <div class="sec"><span class="sec-t">Valeurs a surveiller</span></div>
  <div class="table-wrap">TABLE_PH</div>

  <!-- VERDICT -->
  <div class="verdict"><div class="v-tag">Verdict YAASAP</div><div class="v-t">VERDICT_PH</div></div>

  <!-- SOURCES -->
  SOURCES_PH

</div>

<!-- FOOTER -->
<footer>
  <div class="foot-brand">YAASAP <span>Notes</span></div>'Yacine AOUABED'
  <div class="foot-note">Analyse informative uniquement &mdash; Ne constitue pas un conseil en investissement<br>NOTE_NUM_PH &middot; <span id="liveDateFooter">DATE_PH</span></div>
  <div class="foot-nav">
    <a href="index.html">Archives</a>
    <a href="../yaasap_spatial_live.html">Spatial</a>
    <a href="../yaasap_oil_gas.html">Oil &amp; Gas</a>
    <a href="../yaasap_ecosysteme_ia.html">IA</a>
    <a href="../index.html">Accueil</a>
  </div>
</footer>

<script>
(function(){
  var d = new Date();
  var opts = {weekday:'long',year:'numeric',month:'long',day:'numeric'};
  var str = d.toLocaleDateString('fr-FR', opts);
  var e1 = document.getElementById('liveDate');
  var e2 = document.getElementById('liveDateFooter');
  if(e1) e1.textContent = str;
  if(e2) e2.textContent = str;
})();
</script>
</body>
</html>"""

SYSTEM = """Tu es l'analyste senior de YAASAP Notes, publication financiere mobile-first.
Tu remplis un template HTML en remplacant les placeholders.
Style Financial Times adapte mobile. Analyses tranchees et actionnables.
Tu reponds UNIQUEMENT avec le HTML complet, sans backticks, sans texte avant ou apres."""

def generate_html(text, images, sources):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Hero 1
    hero1_html = ""
    hero2_html = ""
    if len(images) >= 1:
        img = images[0]
        hero1_html = f'<div class="hero"><img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'"><div class="hero-overlay"><div class="hero-tag">A la une</div><div class="hero-title">HEADLINE_FROM_SIGNAL</div><div class="hero-caption">{img["source"]}</div></div></div>'
    if len(images) >= 2:
        img = images[1]
        hero2_html = f'<div class="hero2"><img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'"><div class="hero2-caption">{img["source"]} &mdash; {img["title"]}</div></div>'

    # Sources
    sources_html = ""
    if sources:
        pills = ""
        for s in sources:
            pills += f'<a href="{s["url"]}" target="_blank" class="src-pill">{s["name"]}</a>'
        sources_html = f'<div class="sources"><div class="sources-label">Sources</div><div class="src-list">{pills}</div></div>'

    template = TEMPLATE.replace("HERO1_PH", hero1_html).replace("HERO2_PH", hero2_html).replace("SOURCES_PH", sources_html)

    prompt = f"""Articles du {DATE_STR} :

{text}

Remplace CHAQUE placeholder par du contenu editorial reel. HTML complet uniquement.

PLACEHOLDERS :
DATE_PH = {DATE_STR}
NOTE_NUM_PH = Note du {NUM}
BRENT_PH = cours Brent ex: 110$ +2.1pct
KICKER_PH = 6 blocs scrollables :
  <div class="kk"><div class="kk-l">LABEL</div><div class="kk-v up">VALEUR</div><div class="kk-n">note</div></div>
SIGNAL_PH = bloc signal principal :
  <div class="signal"><div class="signal-label">Analyse principale</div><div class="signal-headline">TITRE ACCROCHEUR</div><div class="signal-deck">sous-titre italique</div><div class="signal-body">2 paragraphes analyse <strong>mots cles en gras</strong></div><div class="pull"><div class="pull-t">citation cle</div><div class="pull-a">source</div></div></div>
ARTICLES_PH = 3 articles sectoriels (petrole, IA, pharma) :
  <div class="art"><div class="art-sector up">SECTEUR</div><div class="art-h">titre</div><div class="art-b">analyse 2-3 phrases avec <strong>mots cles</strong></div></div>
HEADLINE_FROM_SIGNAL = titre court du signal pour la photo hero (10 mots max)
TABLE_PH = tableau valeurs :
  <table><thead><tr><th>Ticker</th><th>Valeur</th><th>Signal</th><th>Direction</th></tr></thead><tbody>
  <tr><td>TICK</td><td>Nom</td><td>Achat/Vente/Hold</td><td><span class="badge-up">HAUSSSE</span></td></tr>
  </tbody></table>
VERDICT_PH = synthese 3 phrases avec <strong>points cles</strong>

TEMPLATE :
{template}"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=SYSTEM,
        messages=[{"role":"user","content":prompt}]
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

def build_index():
    pattern = os.path.join(DOCS_DIR, "note-2*.html")
    note_files = sorted(glob.glob(pattern), reverse=True)
    items = ""
    for n in note_files:
        name = os.path.basename(n)
        date_part = name.replace("note-","").replace(".html","")
        try:
            d = datetime.date.fromisoformat(date_part)
            label = d.strftime("%A %d %B %Y").capitalize()
            is_today = (d == TODAY)
        except Exception:
            label = date_part
            is_today = False
        badge = '<span class="badge">Aujourd\'hui</span>' if is_today else '<span class="dash">—</span>'
        items += f'<li>{badge}<a href="{name}">{label}</a></li>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#1c1814">
<title>YAASAP Notes</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:Georgia,serif;background:#f9f6f0;color:#1c1814;}}
.mast{{background:#1c1814;padding:16px 20px;text-align:center;}}
.pub{{font-size:28px;font-weight:700;font-style:italic;color:#fff;letter-spacing:-.02em;}}
.pub span{{color:#8b1a1a;}}
.tagline{{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-top:4px;}}
.container{{max-width:600px;margin:0 auto;padding:20px 20px 60px;}}
.sec{{font-size:9px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8b1a1a;border-bottom:1px solid #8b1a1a;padding-bottom:4px;margin:24px 0 14px;}}
.today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid #8b1a1a;padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);border-radius:0 4px 4px 0;}}
.today-box a{{font-size:17px;font-weight:700;color:#1c1814;text-decoration:none;display:block;line-height:1.3;}}
.today-box a:hover{{color:#8b1a1a;}}
.today-date{{font-size:10px;color:#9a8f82;font-style:italic;margin-top:5px;}}
ul{{list-style:none;padding:0;}}
li{{padding:10px 0;border-bottom:1px solid rgba(0,0,0,.07);display:flex;align-items:center;gap:10px;}}
li:last-child{{border-bottom:none;}}
li a{{font-size:14px;color:#1c1814;text-decoration:none;}}
li a:hover{{color:#8b1a1a;}}
.badge{{font-size:9px;background:#8b1a1a;color:#fff;padding:2px 7px;border-radius:2px;flex-shrink:0;}}
.dash{{color:#8b1a1a;font-size:14px;flex-shrink:0;}}
.other-sec a{{display:block;padding:10px 0;border-bottom:1px solid rgba(0,0,0,.07);font-size:14px;color:#1c1814;text-decoration:none;}}
.other-sec a:hover{{color:#8b1a1a;}}
.other-sec a::before{{content:"→ ";color:#8b1a1a;}}
footer{{background:#f2ede4;border-top:1px solid rgba(0,0,0,.1);padding:16px 20px;text-align:center;font-size:10px;color:#9a8f82;font-style:italic;}}
</style>
</head>
<body>
<div class="mast">
  <div class="pub">YAASAP <span>Notes</span></div>
  <div class="tagline">Analyse financiere quotidienne</div>
</div>
<div class="container">
  <div class="sec">Note du jour</div>
  <div class="today-box">
    <a href="note-du-jour.html">Analyse du jour &mdash; {DATE_STR}</a>
    <div class="today-date" id="liveDate">{DATE_STR}</div>
  </div>
  <div class="sec">Archives ({len(note_files)} notes)</div>
  <ul>{items}</ul>
  <div class="sec">Toutes nos analyses</div>
  <div class="other-sec">
    <a href="../yaasap_spatial_live.html">Secteur Spatial &mdash; SpaceX IPO</a>
    <a href="../yaasap_oil_gas.html">Oil &amp; Gas N&deg;17 &mdash; TotalEnergies</a>
    <a href="../yaasap_ecosysteme_ia.html">Ecosysteme IA &mdash; LLMs &middot; GPU</a>
    <a href="../yaasap_gta6_light.html">GTA VI &mdash; Cartographie boursiere</a>
    <a href="../yaasap_value.html">Actions sous-cotees</a>
    <a href="../yaasap_v3_paysage.html">Flash Marche MRNA</a>
  </div>
</div>
<footer>YAASAP Notes &middot; Ne constitue pas un conseil en investissement</footer>
<script>
(function(){{
  var d = new Date();
  var opts = {{weekday:'long',year:'numeric',month:'long',day:'numeric'}};
  var el = document.getElementById('liveDate');
  if(el) el.textContent = d.toLocaleDateString('fr-FR', opts);
}})();
</script>
</body>
</html>"""
    idx_path = os.path.join(DOCS_DIR, "index.html")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"OK index.html ({len(note_files)} archives)")

def main():
    print(f"YAASAP Notes - {TODAY}")
    os.makedirs(DOCS_DIR, exist_ok=True)
    articles = fetch_news()
    if not articles:
        print("Aucun article")
        sys.exit(1)
    images  = get_top_images(articles, n=2)
    sources = get_sources(articles)
    print(f"{len(images)} images, {len(sources)} sources")
    html = generate_html(format_articles(articles), images, sources)
    note_dated = os.path.join(DOCS_DIR, f"note-{TODAY.isoformat()}.html")
    with open(note_dated, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK archive : {os.path.basename(note_dated)}")
    note_today = os.path.join(DOCS_DIR, "note-du-jour.html")
    with open(note_today, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK note-du-jour.html")
    build_index()
    print(f"Publie : https://YAASAP.github.io/dailywatch/docs/")
def build_root_index():
    import glob
    root = os.path.join(os.path.dirname(__file__), "..")
    
    # Scanner tous les fichiers HTML à la racine
    html_files = sorted(glob.glob(os.path.join(root, "yaasap_*.html")), reverse=True)
    
    # Mapping noms de fichiers → titres lisibles
    titles = {
        "yaasap_midterms.html":      ("🗳️", "Midterms 2026 — Trump sans Congrès", "Analyse spéciale · Tarifs · Guerre Iran · Fed"),
        "yaasap_spatial_live.html":  ("🚀", "Secteur Spatial — SpaceX IPO · Cotations live", "N°18 · RKLB · ASTS · LUNR"),
        "yaasap_spatial.html":       ("🚀", "Secteur Spatial — Analyse PDF", "N°18 · Flash Spatial"),
        "yaasap_oil_gas.html":       ("🛢️", "Oil & Gas — TotalEnergies · Majors pétrolières", "N°17 · Brent · Ormuz · Stratégie"),
        "yaasap_ecosysteme_ia.html": ("🤖", "Ecosystème IA — LLMs · GPU · Stockage", "N°15 · NVDA · Claude · OpenAI"),
        "yaasap_ecosysteme_ia_v2.html":("🤖","Ecosystème IA v2 — Polices système", "N°15 · Version corrigée"),
        "yaasap_value.html":         ("📉", "Actions sous-cotées — PER bas · Fondamentaux", "N°16 · MSFT · PFE · BABA · VZ"),
        "yaasap_gta6_light.html":    ("🎮", "GTA VI — Cartographie boursière", "N°13 · TTWO · SONY · NVDA"),
        "yaasap_gta6.html":          ("🎮", "GTA VI — Version originale", "N°13 · Flash Marché"),
        "yaasap_v3_paysage.html":    ("📊", "Flash Marché MRNA — Bandes de Bollinger", "N°12 · Moderna · Scénarios trading"),
    }
    
    items = ""
    for f in html_files:
        name = os.path.basename(f)
        if name in titles:
            icon, title, meta = titles[name]
            items += f"""    <li class="note-item">
      <span class="note-bullet">—</span>
      <div>
        <a class="note-link" href="{name}">{icon} {title}</a>
        <div class="note-meta">{meta}</div>
      </div>
    </li>\n"""

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YAASAP Notes</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=Source+Serif+4:wght@300;400;600&display=swap');
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Source Serif 4',Georgia,serif;background:#f9f6f0;color:#1c1814;}}
  .masthead{{border-bottom:3px double rgba(0,0,0,.2);padding:28px 48px 16px;text-align:center;}}
  .pub-name{{font-family:'Playfair Display','Times New Roman',serif;font-size:48px;font-weight:700;letter-spacing:-.02em;}}
  .pub-name em{{font-style:italic;color:#8b1a1a;}}
  .pub-rule{{display:flex;align-items:center;gap:12px;margin:10px 0 6px;justify-content:center;}}
  .pub-rule::before,.pub-rule::after{{content:'';flex:1;max-width:120px;height:1px;background:#1c1814;}}
  .pub-tagline{{font-size:11px;letter-spacing:.25em;text-transform:uppercase;color:#6a5f52;}}
  .pub-date{{font-size:12px;color:#9a8f82;font-style:italic;margin-top:4px;}}
  .container{{max-width:680px;margin:0 auto;padding:32px 24px 60px;}}
  .section-head{{font-size:9px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;color:#8b1a1a;border-bottom:1px solid #8b1a1a;padding-bottom:4px;margin-bottom:16px;margin-top:28px;}}
  .note-today{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid #8b1a1a;padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);}}
  .note-today a{{font-size:16px;font-weight:700;color:#1c1814;text-decoration:none;display:block;}}
  .note-today a:hover{{color:#8b1a1a;}}
  .note-meta-today{{font-size:10px;color:#9a8f82;font-style:italic;margin-top:4px;}}
  .note-list{{list-style:none;padding:0;margin-bottom:32px;}}
  .note-item{{display:flex;align-items:baseline;gap:12px;padding:10px 0;border-bottom:1px solid rgba(0,0,0,.08);}}
  .note-item:last-child{{border-bottom:none;}}
  .note-bullet{{font-size:18px;color:#8b1a1a;flex-shrink:0;line-height:1;}}
  .note-link{{font-family:'Playfair Display',Georgia,serif;font-size:16px;color:#1c1814;text-decoration:none;line-height:1.3;}}
  .note-link:hover{{color:#8b1a1a;}}
  .note-meta{{font-size:11px;color:#9a8f82;font-style:italic;margin-top:2px;}}
  footer{{border-top:1px solid rgba(0,0,0,.12);padding:16px 48px;text-align:center;font-size:10px;color:#9a8f82;font-style:italic;background:#f2ede4;}}
</style>
</head>
<body>
<div class="masthead">
  <div class="pub-name">YAASAP <em>Notes</em></div>
  <div class="pub-rule"><span class="pub-tagline">Analyse financière quotidienne</span></div>
  <div class="pub-date" id="pubDate"></div>
</div>
<div class="container">
  <div class="section-head">Dernière publication</div>
  <div class="note-today">
    <a href="docs/note-du-jour.html">📄 Analyse quotidienne — Pétrole · Géopolitique · IA · Pharma · IT</a>
    <div class="note-meta-today" id="todayDate"></div>
  </div>
  <div class="section-head">Archives &amp; analyses sectorielles</div>
  <ul class="note-list">
{items}
  </ul>
</div>
<footer>YAASAP Notes · Analyse financière à titre informatif · Ne constitue pas un conseil en investissement</footer>
<script>
  var d = new Date();
  var opts = {{weekday:'long',year:'numeric',month:'long',day:'numeric'}};
  var s = d.toLocaleDateString('fr-FR', opts);
  document.getElementById('pubDate').textContent = s;
  document.getElementById('todayDate').textContent = s;
</script>
</body>
</html>"""

    root_index = os.path.join(root, "index.html")
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(index_html)
    print("OK index.html racine mis a jour")
if __name__ == "__main__":
    main()

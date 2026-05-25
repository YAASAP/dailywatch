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
        titl = a.get("title","")
        date = a.get("publishedAt","")[:10]
        if src and src not in seen:
            seen.add(src)
            sources.append({"name": src, "url": url, "title": titl[:80], "date": date})
    return sources[:8]

TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>YAASAP Notes - DATE_PH</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{background:#f9f6f0;font-family:Georgia,'Times New Roman',serif;color:#1c1814;font-size:11px;}
.page{width:1122px;overflow:hidden;display:flex;flex-direction:column;margin:0 auto;}
.mast{border-bottom:3px double rgba(0,0,0,.2);padding:8px 32px;display:flex;align-items:flex-end;justify-content:space-between;background:#f9f6f0;}
.mast-title{font-size:32px;font-weight:700;font-style:italic;letter-spacing:-.02em;color:#1c1814;}
.mast-title span{color:#8b1a1a;}
.mast-mid{text-align:center;}
.mast-issue{font-size:8px;letter-spacing:.15em;text-transform:uppercase;color:#6a5f52;border-top:1px solid #1c1814;border-bottom:1px solid #1c1814;padding:2px 0;}
.mast-right{text-align:right;}
.mast-date{font-size:11px;color:#1c1814;font-weight:600;}
.hero{display:grid;grid-template-columns:1fr 1fr;gap:0;height:120px;overflow:hidden;border-bottom:2px solid rgba(0,0,0,.15);}
.hero-img{position:relative;overflow:hidden;}
.hero-img img{width:100%;height:120px;object-fit:cover;display:block;filter:brightness(.88);}
.hero-img-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(28,24,20,.72);color:rgba(255,255,255,.85);font-size:7px;font-style:italic;padding:3px 7px;}
.kicker{display:flex;border-bottom:1px solid rgba(0,0,0,.12);background:#f2ede4;padding:0 32px;}
.kk{flex:1;padding:5px 10px;border-right:1px solid rgba(0,0,0,.08);}
.kk:last-child{border-right:none;}
.kk-l{font-size:7px;letter-spacing:.1em;text-transform:uppercase;color:#9a8f82;margin-bottom:1px;}
.kk-v{font-size:12px;font-weight:700;color:#1c1814;}
.kk-n{font-size:8px;color:#9a8f82;font-style:italic;}
.up{color:#1e5c32;} .dn{color:#8b1a1a;} .am{color:#8a5c00;}
.body{flex:1;display:grid;grid-template-columns:2fr 1.6fr 1.1fr;min-height:0;}
.col{padding:12px 16px;overflow:hidden;border-right:1px solid rgba(0,0,0,.08);}
.col:last-child{border-right:none;background:#f2ede4;}
.sec-rule{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
.sec-rule::before{content:'';width:18px;height:2px;background:#8b1a1a;flex-shrink:0;}
.sec-rule-t{font-size:7px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#8b1a1a;}
.sec-rule::after{content:'';flex:1;height:1px;background:rgba(0,0,0,.1);}
.headline{font-size:15px;font-weight:700;line-height:1.2;margin-bottom:4px;}
.deck{font-size:9.5px;font-style:italic;color:#6a5f52;line-height:1.4;margin-bottom:7px;border-bottom:1px solid rgba(0,0,0,.06);padding-bottom:6px;}
.body-t{font-size:8.5px;line-height:1.6;color:#3a342c;margin-bottom:6px;}
.body-t strong{font-weight:700;color:#1c1814;}
.pull{border-top:2px solid #8b1a1a;border-bottom:1px solid rgba(0,0,0,.1);padding:6px 10px;margin:7px 0;}
.pull-t{font-size:10px;font-style:italic;line-height:1.45;color:#1c1814;}
.pull-a{font-size:7px;color:#9a8f82;letter-spacing:.08em;text-transform:uppercase;margin-top:3px;}
.art{padding:6px 0;border-bottom:1px solid rgba(0,0,0,.07);}
.art:last-child{border-bottom:none;}
.art-h{font-size:10px;font-weight:700;color:#1c1814;margin-bottom:2px;}
.art-b{font-size:8px;color:#6a5f52;line-height:1.45;}
table{width:100%;border-collapse:collapse;}
th{font-size:7px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#6a5f52;padding:3px 5px;text-align:left;border-bottom:1.5px solid #1c1814;}
td{font-size:8.5px;padding:3px 5px;border-bottom:1px solid rgba(0,0,0,.06);color:#3a342c;}
tr:last-child td{border-bottom:none;}
.verdict{background:#1c1814;border-top:2px solid #8b1a1a;padding:7px 32px;display:flex;align-items:center;gap:10px;flex-shrink:0;}
.v-tag{background:#8b1a1a;color:#f9f6f0;font-size:7px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;padding:3px 8px;white-space:nowrap;flex-shrink:0;}
.v-t{font-size:9.5px;color:rgba(255,255,255,.85);font-style:italic;line-height:1.5;}
.v-t strong{font-style:normal;color:#f0c956;}
.sources{background:#f2ede4;border-top:1px solid rgba(0,0,0,.12);padding:5px 32px;display:flex;flex-wrap:wrap;gap:0;align-items:center;}
.sources-label{font-size:7px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#8b1a1a;margin-right:10px;flex-shrink:0;}
.src-item{font-size:7px;color:#6a5f52;font-style:italic;padding:0 8px;border-right:1px solid rgba(0,0,0,.15);}
.src-item:last-child{border-right:none;}
.src-item a{color:#6a5f52;text-decoration:none;}
.footer{background:#f2ede4;border-top:1px solid rgba(0,0,0,.12);padding:4px 32px;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;}
.foot-l{font-size:6.5px;color:#9a8f82;font-style:italic;}
.foot-r{font-size:7.5px;color:#6a5f52;}
</style>
</head>
<body>
<div class="page">
<div class="mast">
  <div><div class="mast-title">YAASAP <span>Notes</span></div><div style="font-size:8px;color:#9a8f82;letter-spacing:.12em;text-transform:uppercase;">Analyse financiere quotidienne</div></div>
  <div class="mast-mid"><div class="mast-issue">NOTE_NUM_PH</div></div>
  <div class="mast-right"><div class="mast-date" id="liveDate">DATE_PH</div><div style="font-size:10px;font-weight:700;color:#8b1a1a;margin-top:2px;">BRENT_PH</div></div>
</div>
HERO_PH
<div class="kicker">KICKER_PH</div>
<div class="body">
  <div class="col">COL1_PH</div>
  <div class="col">COL2_PH</div>
  <div class="col">COL3_PH</div>
</div>
<div class="verdict"><div class="v-tag">Verdict YAASAP</div><div class="v-t">VERDICT_PH</div></div>
SOURCES_PH
<div class="footer">
  <div class="foot-l">Analyse informative uniquement - Ne constitue pas un conseil en investissement</div>
  <div class="foot-r">YAASAP Notes - NOTE_NUM_PH - <span id="liveDateFooter">DATE_PH</span></div>
</div>
</div>
<script>
(function(){
  var d = new Date();
  var opts = {weekday:'long',year:'numeric',month:'long',day:'numeric'};
  var str = d.toLocaleDateString('fr-FR', opts);
  var el1 = document.getElementById('liveDate');
  var el2 = document.getElementById('liveDateFooter');
  if(el1) el1.textContent = str;
  if(el2) el2.textContent = str;
})();
</script>
</body>
</html>"""

SYSTEM = """Tu es l'analyste senior de YAASAP Notes, publication financiere style Financial Times.
Tu remplis un template HTML en remplacant les placeholders par du vrai contenu editorial.
Tes analyses sont tranchees, precises, actionnables. Style presse financiere serieuse.
Tu reponds UNIQUEMENT avec le HTML complet, sans backticks, sans texte avant ou apres."""

def generate_html(text, images, sources):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    hero_html = ""
    if images:
        imgs_html = ""
        for img in images:
            imgs_html += f'<div class="hero-img"><img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'"><div class="hero-img-caption">{img["source"]} - {img["title"]}</div></div>'
        hero_html = f'<div class="hero">{imgs_html}</div>'
    sources_html = ""
    if sources:
        items = ""
        for s in sources:
            items += f'<span class="src-item"><a href="{s["url"]}" target="_blank">{s["name"]}</a> - {s["date"]}</span>'
        sources_html = f'<div class="sources"><span class="sources-label">Sources</span>{items}</div>'
    template = TEMPLATE.replace("HERO_PH", hero_html).replace("SOURCES_PH", sources_html)
    prompt = f"""Voici les articles du {DATE_STR} a analyser :

{text}

Remplace CHAQUE placeholder par du contenu editorial reel.
Reponds UNIQUEMENT avec le HTML complet.

PLACEHOLDERS :
DATE_PH = {DATE_STR}
NOTE_NUM_PH = Note du {NUM}
BRENT_PH = cours Brent du jour avec variation ex: 110$ +2.1pct
KICKER_PH = 7 blocs <div class="kk"><div class="kk-l">LABEL</div><div class="kk-v up">VALEUR</div><div class="kk-n">note</div></div>
COL1_PH = section-rule Signal du Jour, headline, deck, 2x body-t, 1 pull quote
COL2_PH = 3-4 articles <div class="art"><div class="art-h">titre</div><div class="art-b">analyse</div></div>
COL3_PH = section-rule Valeurs, tableau Ticker / Signal / Direction
VERDICT_PH = 2-3 phrases synthese avec balises strong

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
        if is_today:
            items += f'<li class="today-item"><span class="badge">Aujourd\'hui</span><a href="{name}">{label}</a></li>\n'
        else:
            items += f'<li><a href="{name}">{label}</a></li>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YAASAP Notes</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:Georgia,'Times New Roman',serif;background:#f9f6f0;color:#1c1814;}}
.mast{{border-bottom:3px double rgba(0,0,0,.2);padding:20px 48px 14px;text-align:center;}}
.pub{{font-size:42px;font-weight:700;font-style:italic;letter-spacing:-.02em;}}
.pub span{{color:#8b1a1a;}}
.tagline{{font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:#9a8f82;margin-top:4px;}}
.container{{max-width:700px;margin:32px auto;padding:0 24px 60px;}}
.sec{{font-size:9px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#8b1a1a;border-bottom:1px solid #8b1a1a;padding-bottom:4px;margin-bottom:16px;margin-top:28px;}}
.today-box{{background:#fff;border:1px solid rgba(0,0,0,.1);border-left:3px solid #8b1a1a;padding:14px 18px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,.06);}}
.today-box a{{font-size:17px;font-weight:700;color:#1c1814;text-decoration:none;display:block;}}
.today-box a:hover{{color:#8b1a1a;}}
.today-box .date{{font-size:10px;color:#9a8f82;font-style:italic;margin-top:4px;}}
ul{{list-style:none;padding:0;}}
li{{padding:9px 0;border-bottom:1px solid rgba(0,0,0,.07);display:flex;align-items:center;gap:10px;}}
li:last-child{{border-bottom:none;}}
li::before{{content:"—";color:#8b1a1a;flex-shrink:0;}}
li a{{font-size:14px;color:#1c1814;text-decoration:none;}}
li a:hover{{color:#8b1a1a;}}
li.today-item{{background:rgba(139,26,26,.04);padding:9px 8px;border-radius:2px;}}
.badge{{font-size:8px;background:#8b1a1a;color:#fff;padding:1px 6px;border-radius:2px;font-family:Georgia,serif;flex-shrink:0;}}
.other-notes{{margin-top:28px;}}
.other-notes a{{font-size:14px;color:#8b1a1a;text-decoration:none;font-weight:700;}}
.other-notes a:hover{{text-decoration:underline;}}
.other-item{{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid rgba(0,0,0,.07);}}
.other-item:last-child{{border-bottom:none;}}
.other-item::before{{content:"→";color:#9a8f82;}}
footer{{border-top:1px solid rgba(0,0,0,.12);padding:14px 48px;text-align:center;font-size:10px;color:#9a8f82;font-style:italic;background:#f2ede4;margin-top:40px;}}
</style>
</head>
<body>
<div class="mast">
  <div class="pub">YAASAP <span>Notes</span></div>
  <div class="tagline">Analyse financiere quotidienne &mdash; Petrole &middot; Geopolitique &middot; IA &middot; Pharma &middot; IT</div>
</div>
<div class="container">
  <div class="sec">Note du jour</div>
  <div class="today-box">
    <a href="note-du-jour.html">Analyse quotidienne &mdash; {DATE_STR}</a>
    <div class="date" id="liveDate">{DATE_STR}</div>
  </div>

  <div class="sec">Archives</div>
  <ul>{items}</ul>

  <div class="sec">Toutes nos analyses</div>
  <div class="other-notes">
    <div class="other-item"><a href="../yaasap_spatial_live.html">Secteur Spatial &mdash; SpaceX IPO &middot; Cotations live</a></div>
    <div class="other-item"><a href="../yaasap_oil_gas.html">Oil &amp; Gas N&deg;17 &mdash; TotalEnergies &middot; Ormuz</a></div>
    <div class="other-item"><a href="../yaasap_ecosysteme_ia.html">Ecosysteme IA &mdash; LLMs &middot; GPU &middot; Stockage</a></div>
    <div class="other-item"><a href="../yaasap_gta6_light.html">GTA VI &mdash; Cartographie boursiere</a></div>
    <div class="other-item"><a href="../yaasap_value.html">Actions sous-cotees &mdash; PER bas &middot; Fondamentaux</a></div>
    <div class="other-item"><a href="../yaasap_v3_paysage.html">Flash Marche MRNA &mdash; Bollinger</a></div>
  </div>
</div>
<footer>YAASAP Notes &middot; Analyse informative uniquement &middot; Ne constitue pas un conseil en investissement</footer>
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
    print(f"OK index.html mis a jour ({len(note_files)} notes archivees)")

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

    # Sauvegarder note datee (archive)
    note_dated = os.path.join(DOCS_DIR, f"note-{TODAY.isoformat()}.html")
    with open(note_dated, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK archive : {os.path.basename(note_dated)}")

    # Copier comme note-du-jour
    note_today = os.path.join(DOCS_DIR, "note-du-jour.html")
    with open(note_today, "w", encoding="utf-8") as f:
        f.write(html)
    print("OK note-du-jour.html mis a jour")

    # Mettre a jour l'index avec toutes les archives
    build_index()

    print(f"Publie : https://YAASAP.github.io/dailywatch/docs/")

if __name__ == "__main__":
    main()

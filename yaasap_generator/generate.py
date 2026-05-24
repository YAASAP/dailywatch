#!/usr/bin/env python3
import os, sys, datetime, requests
import anthropic

NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
TODAY         = datetime.date.today()
DATE_STR      = TODAY.strftime("%d %B %Y")
NUM           = TODAY.strftime("%d/%m/%Y")

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
        src   = a.get("source",{}).get("name","?")
        titl  = a.get("title","")
        desc  = (a.get("description","") or "")[:150]
        date  = a.get("publishedAt","")[:10]
        url   = a.get("url","")
        img   = a.get("urlToImage","") or ""
        lines.append(f"{i}. [{src} {date}] {titl}\n   {desc}\n   URL: {url}\n   IMG: {img}")
    return "\n\n".join(lines)

def get_top_images(articles, n=2):
    imgs = []
    for a in articles:
        img = a.get("urlToImage","")
        src = a.get("source",{}).get("name","")
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
.mast-date{font-size:10px;color:#6a5f52;font-style:italic;}
.hero{display:grid;grid-template-columns:1fr 1fr;gap:0;height:120px;overflow:hidden;border-bottom:2px solid rgba(0,0,0,.15);}
.hero-img{position:relative;overflow:hidden;}
.hero-img img{width:100%;height:120px;object-fit:cover;display:block;filter:brightness(.88);}
.hero-img-caption{position:absolute;bottom:0;left:0;right:0;background:rgba(28,24,20,.72);color:rgba(255,255,255,.85);font-size:7px;font-style:italic;padding:3px 7px;letter-spacing:.03em;}
.kicker{display:flex;border-bottom:1px solid rgba(0,0,0,.12);background:#f2ede4;padding:0 32px;}
.kk{flex:1;padding:5px 10px;border-right:1px solid rgba(0,0,0,.08);}
.kk:last-child{border-right:none;}
.kk-l{font-size:7px;letter-spacing:.1em;text-transform:uppercase;color:#9a8f82;margin-bottom:1px;}
.kk-v{font-size:12px;font-weight:700;color:#1c1814;font-family:Georgia,serif;}
.kk-n{font-size:8px;color:#9a8f82;font-style:italic;}
.up{color:#1e5c32;} .dn{color:#8b1a1a;} .am{color:#8a5c00;}
.body{flex:1;display:grid;grid-template-columns:2fr 1.6fr 1.1fr;min-height:0;}
.col{padding:12px 16px;overflow:hidden;border-right:1px solid rgba(0,0,0,.08);}
.col:last-child{border-right:none;background:#f2ede4;}
.sec-rule{display:flex;align-items:center;gap:8px;margin-bottom:8px;}
.sec-rule::before{content:'';width:18px;height:2px;background:#8b1a1a;flex-shrink:0;}
.sec-rule-t{font-size:7px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:#8b1a1a;}
.sec-rule::after{content:'';flex:1;height:1px;background:rgba(0,0,0,.1);}
.headline{font-size:15px;font-weight:700;line-height:1.2;margin-bottom:4px;font-family:Georgia,serif;}
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
td{font-size:8.5px;padding:3px 5px;border-bottom:1px solid rgba(0,0,0,.06);color:#3a342c;font-family:Georgia,serif;}
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
.src-item a:hover{color:#8b1a1a;}
.footer{background:#f2ede4;border-top:1px solid rgba(0,0,0,.12);padding:4px 32px;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;}
.foot-l{font-size:6.5px;color:#9a8f82;font-style:italic;}
.foot-r{font-size:7.5px;color:#6a5f52;font-family:Georgia,serif;}
</style>
</head>
<body>
<div class="page">

<div class="mast">
  <div><div class="mast-title">YAASAP <span>Notes</span></div><div style="font-size:8px;color:#9a8f82;letter-spacing:.12em;text-transform:uppercase;">Analyse financiere quotidienne</div></div>
  <div class="mast-mid"><div class="mast-issue">NOTE_NUM_PH</div></div>
  <div class="mast-right"><div class="mast-date">DATE_PH</div><div style="font-size:10px;font-weight:700;color:#8b1a1a;margin-top:2px;">BRENT_PH</div></div>
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
  <div class="foot-l">Analyse informative uniquement - Ne constitue pas un conseil en investissement - Sources : NewsAPI, Reuters, Bloomberg, Financial Times, Les Echos</div>
  <div class="foot-r">YAASAP Notes - NOTE_NUM_PH - DATE_PH</div>
</div>

</div>
<script>
const d = new Date();
const opts = {weekday:'long',year:'numeric',month:'long',day:'numeric'};
const str = d.toLocaleDateString('fr-FR', opts);
document.querySelectorAll('.live-date').forEach(el => el.textContent = str);
</script>
</body>
</html>"""

SYSTEM = """Tu es l'analyste senior de YAASAP Notes, publication financiere style Financial Times.
Tu remplis un template HTML en remplacant les placeholders par du vrai contenu editorial.
Tes analyses sont tranchees, precises, actionnables. Style presse financiere serieuse.
Tu reponds UNIQUEMENT avec le HTML complet, sans backticks, sans texte avant ou apres."""

def generate_html(text, images, sources):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    # Build hero HTML
    hero_html = ""
    if images:
        imgs_html = ""
        for img in images:
            imgs_html += f'<div class="hero-img"><img src="{img["url"]}" alt="{img["title"]}" onerror="this.parentElement.style.display=\'none\'"><div class="hero-img-caption">{img["source"]} - {img["title"]}</div></div>'
        hero_html = f'<div class="hero">{imgs_html}</div>'

    # Build sources HTML
    sources_html = ""
    if sources:
        items = ""
        for s in sources:
            items += f'<span class="src-item"><a href="{s["url"]}" target="_blank">{s["name"]}</a> - {s["date"]}</span>'
        sources_html = f'<div class="sources"><span class="sources-label">Sources</span>{items}</div>'

    template = TEMPLATE.replace("HERO_PH", hero_html).replace("SOURCES_PH", sources_html)

    prompt = f"""Voici les articles du {DATE_STR} a analyser :

{text}

Remplace CHAQUE placeholder dans ce template HTML par du contenu editorial reel.
Reponds UNIQUEMENT avec le HTML complet.

PLACEHOLDERS :
DATE_PH = {DATE_STR}
NOTE_NUM_PH = Note du {NUM}
BRENT_PH = cours Brent du jour avec variation ex: 110$ +2.1pct
KICKER_PH = 7 blocs au format <div class="kk"><div class="kk-l">LABEL</div><div class="kk-v up">VALEUR</div><div class="kk-n">note</div></div>
COL1_PH = colonne gauche : section-rule Signal du Jour, headline, deck, 2 paragraphes body-t, 1 pull quote
COL2_PH = colonne centrale : 3-4 articles au format <div class="art"><div class="art-h">titre</div><div class="art-b">analyse</div></div>
COL3_PH = colonne droite : section-rule Valeurs, tableau avec colonnes Ticker / Signal / Direction
VERDICT_PH = 2-3 phrases de synthese actionnelle avec balises strong pour points cles

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

def main():
    print(f"YAASAP Notes - {TODAY}")
    os.makedirs("../docs", exist_ok=True)
    articles = fetch_news()
    if not articles:
        print("Aucun article")
        sys.exit(1)
    images  = get_top_images(articles, n=2)
    sources = get_sources(articles)
    print(f"{len(images)} images, {len(sources)} sources")
    html = generate_html(format_articles(articles), images, sources)
    with open("../docs/note-du-jour.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("OK note-du-jour.html cree")
    with open("../docs/index.html", "w", encoding="utf-8") as f:
        f.write(f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0;url=note-du-jour.html"><title>YAASAP Notes</title></head><body><a href="note-du-jour.html">YAASAP Notes - {DATE_STR}</a></body></html>')
    print(f"Publie : https://YAASAP.github.io/dailywatch/docs/note-du-jour.html")

if __name__ == "__main__":
    main()

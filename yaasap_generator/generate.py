#!/usr/bin/env python3
import os, sys, datetime, requests
from pathlib import Path
import anthropic

NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_DIR    = Path("docs")
TODAY         = datetime.date.today()
ISSUE_FILE    = Path("yaasap_generator/.issue_number")

def get_issue():
    ISSUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    n = int(ISSUE_FILE.read_text().strip()) + 1 if ISSUE_FILE.exists() else 1
    ISSUE_FILE.write_text(str(n))
    return n

def fetch_news():
    articles = []
    for q in ["oil gas brent","geopolitics Iran China","artificial intelligence AI","pharma FDA biotech","technology semiconductor"]:
        try:
            r = requests.get("https://newsapi.org/v2/everything", params={
                "q": q, "sortBy": "publishedAt", "pageSize": 5,
                "from": TODAY.isoformat(), "apiKey": NEWSAPI_KEY
            }, timeout=10)
            data = r.json()
            if data.get("status") == "ok":
                articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"Erreur: {e}")
    seen, unique = set(), []
    for a in articles:
        u = a.get("url","")
        if u and u not in seen:
            seen.add(u)
            unique.append(a)
    print(f"OK {len(unique)} articles")
    return unique

def format_articles(articles):
    lines = []
    for i, a in enumerate(articles[:30], 1):
        src  = a.get("source",{}).get("name","?")
        titl = a.get("title","")
        desc = (a.get("description","") or "")[:150]
        date = a.get("publishedAt","")[:10]
        lines.append(f"{i}. [{src} {date}] {titl}\n   {desc}")
    return "\n\n".join(lines)

def generate_html(articles_text, num, date_str):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system="Tu es l'analyste senior de YAASAP Notes. Tu generes des notes financieres professionnelles en HTML pur.",
        messages=[{"role":"user","content":f"""Articles du {date_str}:

{articles_text}

Genere la note YAASAP Notes N{num} en HTML complet.
- Style presse financiere, polices systeme uniquement
- Format 1122x794px, 3 colonnes
- Theme clair et or : fond #f9f6f0, accents #b8952a, encre #1c1814
- Masthead YAASAP Notes + date + numero
- Kicker bar 7 metriques cles
- 3 colonnes : signal du jour / analyses / valeurs a surveiller
- Verdict YAASAP fond sombre accent or
- Footer : YAASAP Notes - N{num} - {date_str}

HTML UNIQUEMENT, sans backticks, sans texte avant ou apres."""}]
    )
    html = msg.content[0].text
    if "```" in html:
        parts = html.split("```")
        for p in parts:
            s = p.strip()
            if s.startswith("<!") or s.startswith("<html"):
                html = s
                break
    if html.startswith("html\n"):
        html = html[5:]
    return html.strip()

def main():
    print(f"YAASAP Notes - {TODAY}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    num      = get_issue()
    date_str = TODAY.strftime("%d %B %Y")
    articles = fetch_news()
    if not articles:
        print("Aucun article - arret")
        sys.exit(1)
    html = generate_html(format_articles(articles), num, date_str)
    out  = OUTPUT_DIR / "note-du-jour.html"
    out.write_text(html, encoding="utf-8")
    print(f"OK -> {out}")
    idx = OUTPUT_DIR / "index.html"
    idx.write_text(f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url=note-du-jour.html">
<title>YAASAP Notes</title></head>
<body><a href="note-du-jour.html">YAASAP Notes N{num} - {date_str}</a></body></html>""", encoding="utf-8")
    print(f"Note N{num} publiee : https://YAASAP.github.io/dailywatch/")

if __name__ == "__main__":
    main()

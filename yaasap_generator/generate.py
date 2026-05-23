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
                params={"q":q,"sortBy":"publishedAt","pageSize":5,"from":TODAY.isoformat(),"apiKey":NEWSAPI_KEY},
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
        lines.append(f"{i}. [{src} {date}] {titl}\n   {desc}")
    return "\n\n".join(lines)

def generate_html(text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system="Tu es l'analyste senior de YAASAP Notes. Tu generes des notes financieres professionnelles en HTML pur.",
        messages=[{"role":"user","content":f"""Articles du {DATE_STR}:

{text}

Genere la note YAASAP Notes du {NUM} en HTML complet.
- Style presse financiere, polices systeme uniquement
- Format 1122x794px, 3 colonnes
- Theme clair et or : fond #f9f6f0, accents #b8952a, encre #1c1814
- Masthead YAASAP Notes + date
- Kicker bar 7 metriques cles
- 3 colonnes : signal du jour / analyses / valeurs a surveiller
- Verdict YAASAP fond sombre accent or
- Footer : YAASAP Notes - {NUM} - {DATE_STR}
HTML UNIQUEMENT sans backticks."""}])
    html = msg.content[0].text
    if "```" in html:
        for p in html.split("```"):
            s =

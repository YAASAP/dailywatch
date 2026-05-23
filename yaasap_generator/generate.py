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
                params={"q":q,"sortBy":"publishedAt","pageSize":5,"from":(TODAY - datetime.timedelta(days=2)).isoformat(),"apiKey":NEWSAPI_KEY},
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

Genere la note YAASAP Notes du {NUM} en HTML complet et valide.

IMPORTANT : Reponds UNIQUEMENT avec du code HTML. Commence par <!DOCTYPE html> et termine par </html>. Zero texte avant ou apres.

Structure obligatoire :
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>YAASAP Notes - {DATE_STR}</title>
<style>
/* styles inline complets - polices systeme Georgia Times New Roman */
/* fond #f9f6f0, accents #8b1a1a bordeaux, encre #1c1814 */
/* format 1122px largeur, style Financial Times */
</style>
</head>
<body>
<div class="page">
<!-- masthead : YAASAP Notes + date + kicker bar 7 metriques -->
<!-- body : 3 colonnes grid -->
<!-- col 1 : signal du jour + analyse principale -->
<!-- col 2 : 3-4 analyses sectorielles avec impact boursier -->
<!-- col 3 : tableau valeurs a surveiller + agenda -->
<!-- verdict fond sombre -->
<!-- footer -->
</div>
</body>
</html>"""}]

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
            s = p.strip()
            if s.startswith("<!") or s.startswith("<html"):
                return s
    return html.strip()

def main():
    print(f"YAASAP Notes - {TODAY}")
    os.makedirs("../docs", exist_ok=True)
    articles = fetch_news()
    if not articles:
        print("Aucun article")
        sys.exit(1)
    html = generate_html(format_articles(articles))
    with open("../docs/note-du-jour.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("OK note-du-jour.html cree")
    with open("../docs/index.html", "w", encoding="utf-8") as f:
        f.write(f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta http-equiv="refresh" content="0;url=note-du-jour.html"><title>YAASAP Notes</title></head><body><a href="note-du-jour.html">YAASAP Notes - {DATE_STR}</a></body></html>')
    print(f"Publie : https://YAASAP.github.io/dailywatch/docs/note-du-jour.html")

if __name__ == "__main__":
    main()

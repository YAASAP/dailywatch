#!/usr/bin/env python3
"""
YAASAP Notes - Generateur automatique quotidien
"""

import os
import sys
import datetime
import requests
from pathlib import Path
import anthropic

NEWSAPI_KEY   = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_DIR    = Path("docs")
NOTE_FILENAME = "note-du-jour.html"

SOURCES = [
    "the-wall-street-journal",
    "financial-times",
    "le-monde",
    "les-echos",
    "reuters",
    "bloomberg",
]

QUERIES = [
    "oil gas energy OPEC brent",
    "geopolitics war sanctions Iran China Russia",
    "artificial intelligence AI model GPU",
    "pharma FDA drug biotech",
    "technology semiconductor chip",
]

TODAY = datetime.date.today()
ISSUE_NUM_FILE = Path("yaasap_generator/.issue_number")


def get_issue_number():
    if ISSUE_NUM_FILE.exists():
        n = int(ISSUE_NUM_FILE.read_text().strip()) + 1
    else:
        n = 1
    ISSUE_NUM_FILE.write_text(str(n))
    return n


def fetch_news():
    all_articles = []

    for source in SOURCES[:4]:
        try:
            r = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={"sources": source, "pageSize": 10, "apiKey": NEWSAPI_KEY},
                timeout=10
            )
            data = r.json()
            if data.get("status") == "ok":
                for art in data.get("articles", []):
                    art["_source_name"] = source
                    all_articles.append(art)
        except Exception as e:
            print(f"Erreur source {source}: {e}")

    for q in QUERIES:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": q,
                    "sources": ",".join(SOURCES),
                    "sortBy": "publishedAt",
                    "pageSize": 5,
                    "from": TODAY.isoformat(),
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=10
            )
            data = r.json()
            if data.get("status") == "ok":
                all_articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"Erreur query '{q}': {e}")

    seen = set()
    unique = []
    for a in all_articles:
        url = a.get("url", "")
        if url not in seen and url:
            seen.add(url)
            unique.append(a)

    print(f"OK {len(unique)} articles uniques recuperes")
    return unique


def format_articles_for_prompt(articles):
    lines = []
    for i, a in enumerate(articles[:40], 1):
        source  = a.get("source", {}).get("name", a.get("_source_name", "?"))
        title   = a.get("title", "")
        desc    = a.get("description", "") or ""
        pubdate = a.get("publishedAt", "")[:10]
        url     = a.get("url", "")
        lines.append(
            f"{i}. [{source} - {pubdate}] {title}\n"
            f"   Resume: {desc[:200]}\n"
            f"   URL: {url}"
        )
    return "\n\n".join(lines)


SYSTEM_PROMPT = """Tu es l'analyste senior de YAASAP Notes, une publication financiere professionnelle.
Tu produis des notes quotidiennes synthetiques au style editorial de presse financiere serieuse.
Tu analyses les signaux geopolitiques et economiques avec un impact boursier concret.
Tu te concentres sur 5 secteurs : petrole/energie, geopolitique, IT/tech, IA, pharma/biotech.
Tu ecris comme un analyste humain experimente. Tes analyses sont tranchees et actionnables."""


def generate_html(articles_text, issue_num, date_str):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    user_prompt = f"""Voici les articles du {date_str} :

{articles_text}

---

Genere la note quotidienne YAASAP Notes N{issue_num} en HTML complet.

REGLES :
- Style presse financiere professionnelle (pas style IA)
- Polices systeme uniquement (system-ui, Georgia, Courier New)
- Format paysage 1122x794px, 3 colonnes editoriales
- Theme clair et or : fond #f9f6f0, accents #b8952a, encre #1c1814
- Masthead YAASAP Notes + date + numero
- Kicker bar 7 metriques cles
- 3 colonnes : signal du jour / analyses sectorielles / valeurs a surveiller
- Verdict YAASAP fond sombre accent or
- Footer : YAASAP Notes - N{issue_num} - {date_str}

Genere UNIQUEMENT le HTML complet sans texte avant ou apres et sans backticks."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    html = message.content[0].text

    if "```" in html:
        parts = html.split("```")
        for p in parts:
            stripped = p.strip()
            if stripped.startswith("<!") or stripped.startswith("<html"):
                html = stripped
                break
        else:
            html = parts[1] if len(parts) > 1 else html
        if html.startswith("html\n"):
            html = html[5:]

    return html.strip()


def update_index(issue_num, date_str):
    index_path = OUTPUT_DIR / "index.html"
    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YAASAP Notes</title>
<meta http-equiv="refresh" content="0;url=note-du-jour.html">
<style>
  body {{ font-family:system-ui,sans-serif; background:#f9f6f0; color:#1c1814;
         display:flex; align-items:center; justify-content:center; min-height:100vh; }}
  .box {{ text-align:center; padding:40px; }}
  h1 {{ font-family:Georgia,serif; font-size:28px; margin-bottom:8px; }}
  h1 em {{ font-style:italic; color:#0d1f3c; }}
  a {{ color:#b8952a; text-decoration:none; font-size:14px; }}
  .note {{ margin-top:20px; font-size:13px; color:#6a5f52; }}
</style>
</head>
<body>
<div class="box">
  <h1>YAASAP <em>Notes</em></h1>
  <p class="note">Analyse financiere quotidienne</p>
  <p style="margin-top:20px;"><a href="note-du-jour.html">Note du jour - N{issue_num} - {date_str}</a></p>
</div>
</body>
</html>"""
    index_path.write_text(index_html, encoding="utf-8")
    print(f"OK Index mis a jour - N{issue_num}")


def main():
    print(f"\n{'='*50}")
    print(f"YAASAP Notes - Generation quotidienne")
    print(f"Date : {TODAY.isoformat()}")
    print(f"{'='*50}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gitkeep = OUTPUT_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()

    issue_num = get_issue_number()
    date_str  = TODAY.strftime("%d %B %Y")

    print("Recuperation des articles...")
    articles = fetch_news()
    if not articles:
        print("Aucun article recupere - arret")
        sys.exit(1)

    articles_text = format_articles_for_prompt(articles)

    print("Generation de la note via Claude...")
    html = generate_html(articles_text, issue_num, date_str)

    output_path = OUTPUT_DIR / NOTE_FILENAME
    output_path.write_text(html, encoding="utf-8")
    print(f"OK Note sauvegardee -> {output_path}")

    update_index(issue_num, date_str)

    print(f"\nNote N{issue_num} generee avec succes !")
    print(f"URL : https://YAASAP.github.io/dailywatch/note-du-jour.html")


if __name__ == "__main__":
    main()

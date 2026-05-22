#!/usr/bin/env python3
"""
YAASAP Notes — Générateur automatique quotidien
Fetch NewsAPI → Analyse Claude → HTML → Push GitHub
"""

import os
import json
import datetime
import requests
from pathlib import Path
import anthropic

# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════

NEWSAPI_KEY    = os.environ["NEWSAPI_KEY"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]
OUTPUT_DIR     = Path("docs")          # GitHub Pages lit depuis /docs
NOTE_FILENAME  = "note-du-jour.html"

SECTORS = ["pétrole", "géopolitique", "intelligence artificielle", "pharmaceutique", "technologie"]

SOURCES = [
    "the-wall-street-journal",
    "financial-times",
    "le-monde",
    "les-echos",
    # Fallback sources solides si les 4 principales ont peu d'articles
    "reuters",
    "bloomberg",
    "the-guardian",
]

QUERIES = [
    "oil gas energy OPEC brent",
    "geopolitics war sanctions Iran China Russia",
    "artificial intelligence AI model GPU",
    "pharma FDA drug biotech",
    "technology semiconductor chip",
]

TODAY = datetime.date.today()
ISSUE_NUM_FILE = Path(".issue_number")

def get_issue_number():
    if ISSUE_NUM_FILE.exists():
        n = int(ISSUE_NUM_FILE.read_text().strip()) + 1
    else:
        n = 1
    ISSUE_NUM_FILE.write_text(str(n))
    return n

# ══════════════════════════════════════════════
# 1. FETCH NEWSAPI
# ══════════════════════════════════════════════

def fetch_news():
    """Récupère les articles les plus impactants des 4 sources."""
    all_articles = []

    # A) Articles par source en priorité
    for source in SOURCES[:4]:
        try:
            r = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "sources": source,
                    "pageSize": 10,
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=10
            )
            data = r.json()
            if data.get("status") == "ok":
                for art in data.get("articles", []):
                    art["_source_name"] = source
                    all_articles.append(art)
        except Exception as e:
            print(f"⚠ Erreur source {source}: {e}")

    # B) Articles par thématique (pour couvrir les secteurs)
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
                    "language": "en,fr",
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=10
            )
            data = r.json()
            if data.get("status") == "ok":
                all_articles.extend(data.get("articles", []))
        except Exception as e:
            print(f"⚠ Erreur query '{q}': {e}")

    # Déduplication par URL
    seen = set()
    unique = []
    for a in all_articles:
        url = a.get("url", "")
        if url not in seen and url:
            seen.add(url)
            unique.append(a)

    print(f"✓ {len(unique)} articles uniques récupérés")
    return unique

def format_articles_for_prompt(articles):
    """Formate les articles pour le prompt Claude."""
    lines = []
    for i, a in enumerate(articles[:40], 1):  # 40 max pour rester dans le contexte
        source  = a.get("source", {}).get("name", a.get("_source_name", "?"))
        title   = a.get("title", "")
        desc    = a.get("description", "") or ""
        pubdate = a.get("publishedAt", "")[:10]
        url     = a.get("url", "")
        lines.append(
            f"{i}. [{source} · {pubdate}] {title}\n"
            f"   Résumé: {desc[:200]}\n"
            f"   URL: {url}"
        )
    return "\n\n".join(lines)

# ══════════════════════════════════════════════
# 2. GÉNÉRATION HTML VIA CLAUDE API
# ══════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es l'analyste senior de YAASAP Notes, une publication financière professionnelle.
Tu produis des notes quotidiennes synthétiques, au style éditorial de presse financière sérieuse (Financial Times, Les Echos).
Tu analyses les signaux géopolitiques et économiques avec un impact boursier concret.
Tu te concentres sur 5 secteurs : pétrole/énergie, géopolitique, IT/tech, IA, pharma/biotech.
Tu n'utilises jamais de style "IA générative" : pas de bullets automatiques, pas de listes exhaustives.
Tu écris comme un analyste humain expérimenté. Tes analyses sont tranchées et actionnables."""

def generate_html(articles_text, issue_num, date_str):
    """Appelle Claude API pour générer le HTML complet de la note."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    user_prompt = f"""Voici les articles du {date_str} issus du Financial Times, Wall Street Journal, Les Echos et Le Monde :

{articles_text}

---

Génère la note quotidienne YAASAP Notes N°{issue_num} en HTML complet.

RÈGLES IMPÉRATIVES :
- Style presse financière professionnelle (pas style IA)
- Police système uniquement (system-ui, Georgia, Courier New) — AUCUNE Google Font
- Format paysage A4 une page (1122×794px), 3 colonnes éditoriales
- Thème clair et or (fond #f9f6f0, accents #b8952a/#d4aa40, encre #1c1814)
- Inclure : masthead YAASAP Notes, kicker bar avec 7 métriques clés, 3 colonnes de contenu
- Sélectionne les 5–8 annonces les plus impactantes parmi les 5 secteurs prioritaires
- Pour chaque annonce : analyse de l'impact boursier (valeurs cotées concernées, direction, magnitude)
- Section "Signal du jour" : LA tendance la plus importante du jour en 3 lignes
- Tableau des valeurs à surveiller : ticker, impact, direction
- Verdict YAASAP en bas de page (fond sombre, accent or)
- Footer : YAASAP Notes · N°{issue_num} · {date_str}

STRUCTURE HTML EXACTE :
1. DOCTYPE + head avec styles CSS inline complets (pas de fichier externe)
2. .page (1122×794px, overflow hidden)
3. .masthead (YAASAP Notes + date + kicker)
4. .body (3 colonnes grid)
5. .verdict + .footer

Génère UNIQUEMENT le HTML complet, sans aucun texte avant ou après."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    html = message.content[0].text

    # Nettoyage au cas où Claude ajoute des backticks
    if html.startswith("```"):
        html = html.split("```", 2)[-1]
        if html.startswith("html"):
            html = html[4:]
    if html.endswith("```"):
        html = html.rsplit("```", 1)[0]

    return html.strip()

# ══════════════════════════════════════════════
# 3. GÉNÉRATION INDEX
# ══════════════════════════════════════════════

def update_index(issue_num, date_str):
    """Met à jour l'index GitHub Pages avec la nouvelle note."""
    index_path = OUTPUT_DIR / "index.html"
    archive_path = OUTPUT_DIR / "archives.html"

    # Lire archives existantes
    existing_notes = []
    if archive_path.exists():
        content = archive_path.read_text()
        # Extraction simplifiée des lignes d'archive
        for line in content.split("\n"):
            if 'href="note-' in line and "note-du-jour" not in line:
                existing_notes.append(line.strip())

    # Archiver la note précédente si elle existe
    prev_note = OUTPUT_DIR / NOTE_FILENAME
    if prev_note.exists():
        # Trouver la date de la note précédente depuis son contenu
        prev_content = prev_note.read_text()
        # Sauvegarder sous un nom daté
        archive_name = f"note-{(TODAY - datetime.timedelta(days=1)).isoformat()}.html"
        (OUTPUT_DIR / archive_name).write_text(prev_content)
        prev_link = f'<li><a href="{archive_name}">N°{issue_num-1} — {(TODAY - datetime.timedelta(days=1)).strftime("%d %B %Y")}</a></li>'
        existing_notes.insert(0, prev_link)

    # Générer index.html simple
    index_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YAASAP Notes — Publications</title>
<meta http-equiv="refresh" content="0;url=note-du-jour.html">
<style>
  body {{ font-family: system-ui, sans-serif; background:#f9f6f0; color:#1c1814;
         display:flex; align-items:center; justify-content:center; min-height:100vh; }}
  .box {{ text-align:center; padding:40px; }}
  h1 {{ font-family:Georgia,serif; font-size:28px; margin-bottom:8px; }}
  h1 em {{ font-style:italic; color:#0d1f3c; }}
  a {{ color:#b8952a; text-decoration:none; font-size:14px; }}
  a:hover {{ text-decoration:underline; }}
  .note {{ margin-top:20px; font-size:13px; color:#6a5f52; }}
  ul {{ list-style:none; padding:0; margin-top:16px; }}
  li {{ padding:4px 0; border-bottom:1px solid rgba(0,0,0,.06); }}
</style>
</head>
<body>
<div class="box">
  <h1>YAASAP <em>Notes</em></h1>
  <p class="note">Analyse financière quotidienne — Pétrole · Géopolitique · IT · IA · Pharma</p>
  <p style="margin-top:20px;">
    <a href="note-du-jour.html">📄 Note du jour — N°{issue_num} · {date_str}</a>
  </p>
  {f'<p style="margin-top:12px;"><a href="archives.html">📚 Archives ({len(existing_notes)} notes)</a></p>' if existing_notes else ''}
</div>
</body>
</html>"""

    index_path.write_text(index_html)

    # Mettre à jour archives si nécessaire
    if existing_notes:
        archive_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YAASAP Notes — Archives</title>
<style>
  body {{ font-family:system-ui,sans-serif; background:#f9f6f0; color:#1c1814; max-width:600px; margin:40px auto; padding:0 20px; }}
  h1 {{ font-family:Georgia,serif; font-size:22px; border-bottom:2px solid #b8952a; padding-bottom:8px; }}
  ul {{ list-style:none; padding:0; }}
  li {{ padding:8px 0; border-bottom:1px solid rgba(0,0,0,.06); }}
  a {{ color:#b8952a; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .back {{ margin-bottom:20px; font-size:13px; }}
</style>
</head>
<body>
<p class="back"><a href="index.html">← Retour</a></p>
<h1>Archives YAASAP Notes</h1>
<ul>
  {''.join(existing_notes)}
</ul>
</body>
</html>"""
        archive_path.write_text(archive_html)

    print(f"✓ Index mis à jour — N°{issue_num}")

# ══════════════════════════════════════════════
# 4. MAIN
# ══════════════════════════════════════════════

def main():
    print(f"\n{'='*50}")
    print(f"YAASAP Notes — Génération quotidienne")
    print(f"Date : {TODAY.isoformat()}")
    print(f"{'='*50}\n")

    # Créer le répertoire de sortie si nécessaire
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Numéro de note
    issue_num = get_issue_number()
    date_str  = TODAY.strftime("%d %B %Y")

    # 1. Fetch news
    print("📡 Récupération des articles…")
    articles = fetch_news()
    if not articles:
        print("❌ Aucun article récupéré — arrêt")
        return

    articles_text = format_articles_for_prompt(articles)

    # 2. Génération HTML
    print("🧠 Génération de la note via Claude…")
    html = generate_html(articles_text, issue_num, date_str)

    # 3. Sauvegarde
    output_path = OUTPUT_DIR / NOTE_FILENAME
    output_path.write_text(html, encoding="utf-8")
    print(f"✓ Note sauvegardée → {output_path}")

    # 4. Mise à jour index
    update_index(issue_num, date_str)

    print(f"\n✅ Note N°{issue_num} générée avec succès !")
    print(f"   URL : https://YAASAP.github.io/dailywatch/note-du-jour.html")

if __name__ == "__main__":
    main()

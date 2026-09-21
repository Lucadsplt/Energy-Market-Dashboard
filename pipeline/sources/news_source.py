import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import requests

FLUX = [
    {"source": "EIA", "url": "https://www.eia.gov/rss/todayinenergy.xml"},
    {"source": "OilPrice", "url": "https://oilprice.com/rss/main"},
    {"source": "Rigzone", "url": "https://www.rigzone.com/news/rss/rigzone_latest.aspx"},
    {"source": "IFPEN", "url": "https://www.ifpenergiesnouvelles.fr/rss/feed/newsroom"},
    {"source": "Oil & Gas Journal",
     "url": "https://www.ogj.com/__rss/website-scheduled-content.xml?input=%7B%22sectionAlias%22%3A%22general-interest%22%7D"},
]

UA = "Mozilla/5.0 (compatible; EnergyDashboard/1.0)"
JOURS_HISTORIQUE = 90

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "news.json"


def recuperer_image(url):
    """Recupere l'image d'apercu (og:image) de la page d'un article."""
    try:
        html = requests.get(url, headers={"User-Agent": UA}, timeout=8).text
        balise = re.search(r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]*>', html, re.I)
        if not balise:
            return None
        contenu = re.search(r'content=["\']([^"\']+)["\']', balise.group(0), re.I)
        return contenu.group(1) if contenu else None
    except Exception:
        return None


def date_iso(entry):
    """Date de l'article au format ISO (ou None)."""
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc).isoformat()


def charger_existant():
    """Articles deja stockes (accumulation)."""
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8")).get("articles", [])
        except Exception:
            return []
    return []


def main():
    # 1. Ce qu'on a deja, indexe par lien (pour dedoublonner)
    par_lien = {a["lien"]: a for a in charger_existant()}
    nouveaux = 0

    # 2. Parcourir les flux ; ajouter uniquement les articles inconnus
    for flux in FLUX:
        try:
            feed = feedparser.parse(flux["url"], agent=UA)
            for entry in feed.entries[:15]:
                lien = entry.get("link")
                if not lien or lien in par_lien:
                    continue
                par_lien[lien] = {
                    "source": flux["source"],
                    "titre": (entry.get("title") or "").strip(),
                    "lien": lien,
                    "date": date_iso(entry),
                    "image": recuperer_image(lien),   # telecharge une seule fois
                }
                nouveaux += 1
        except Exception as e:
            print(f"Flux ignore ({flux['source']}) : {e}")

    # 3. Elaguer : ne garder que les JOURS_HISTORIQUE derniers jours
    limite = datetime.now(timezone.utc) - timedelta(days=JOURS_HISTORIQUE)
    articles = []
    for a in par_lien.values():
        if a.get("date"):
            try:
                if datetime.fromisoformat(a["date"]) < limite:
                    continue
            except Exception:
                pass
        articles.append(a)

    # 4. Trier du plus recent au plus ancien
    articles.sort(key=lambda a: a.get("date") or "", reverse=True)

    # 5. Ecrire
    DATA_PATH.write_text(
        json.dumps({"articles": articles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Ecrit : {DATA_PATH} ({len(articles)} articles, {nouveaux} nouveaux)")


if __name__ == "__main__":
    main()

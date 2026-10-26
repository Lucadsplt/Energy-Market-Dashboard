"""Agenda des evenements a venir (banques centrales, OPEP+, politique, climat) et des publications hebdomadaires.

Deux sources :
  - pipeline/reference/agenda_evenements.json : evenements ponctuels, tenus A LA MAIN avec leur source (un discours non annonce ne
    peut pas figurer ici : il n'existe pas de flux gratuit et fiable des prises de parole a venir) ;
  - des regles : les publications hebdomadaires (stocks EIA, forages Baker Hughes, rapport COT) tombent toujours le meme jour
    de la semaine, on calcule donc leurs prochaines dates.
Le site masque lui-meme les evenements passes ; ce script ne garde que les evenements encore a venir.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import save_json

REFERENCE = Path(__file__).resolve().parents[1] / "reference" / "agenda_evenements.json"
NEW_YORK = ZoneInfo("America/New_York")
TYPES = {"banque_centrale", "opep", "politique", "climat"}
MARCHES = {"petrole", "gaz", "electricite"}
IMPORTANCES = {"haute", "moyenne", "faible"}
STATUTS = {"confirme", "a_confirmer"}

# jour_semaine : 0 = lundi ... 4 = vendredi ; heure en heure de New York (suit l'heure d'ete americaine)
HEBDOMADAIRES = [
    {"cle": "eia_petrole", "titre": "Stocks de pétrole aux États-Unis (EIA)", "jour_semaine": 2, "heure": "10:30", "marches": ["petrole"],
     "note": "Stocks de brut, d'essence et de distillats : l'un des chiffres les plus suivis du marché pétrolier.",
     "lien": "https://www.eia.gov/petroleum/supply/weekly/"},
    {"cle": "eia_gaz", "titre": "Stocks de gaz naturel aux États-Unis (EIA)", "jour_semaine": 3, "heure": "10:30", "marches": ["gaz"],
     "note": "Variation hebdomadaire des stocks, comparée à la moyenne des années passées.",
     "lien": "https://ir.eia.gov/ngs/ngs.html"},
    {"cle": "baker_hughes", "titre": "Forages en activité aux États-Unis (Baker Hughes)", "jour_semaine": 4, "heure": "13:00", "marches": ["petrole", "gaz"],
     "note": "Indicateur avancé de la production américaine.",
     "lien": "https://rigcount.bakerhughes.com/"},
    {"cle": "cot", "titre": "Positions des fonds spéculatifs (CFTC, rapport COT)", "jour_semaine": 4, "heure": "15:30", "marches": ["petrole", "gaz"],
     "note": "Les données datent du mardi précédent. Elles alimentent la règle « positionnement des fonds » de l'onglet Stratégies.",
     "lien": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm"},
]


def horodatage(valeur):
    """'2026-10-28T18:00:00Z' -> datetime UTC."""
    return datetime.fromisoformat(valeur).astimezone(timezone.utc)


def occurrences(regle, maintenant, nombre=2):
    """Prochaines dates (UTC, format ISO) d'une publication hebdomadaire. Un jour ferie americain peut la decaler d'un jour."""
    h, m = (int(x) for x in regle["heure"].split(":"))
    trouvees = []
    jour = maintenant.astimezone(NEW_YORK).date()
    for _ in range(30):
        if jour.weekday() == regle["jour_semaine"]:
            moment = datetime(jour.year, jour.month, jour.day, h, m, tzinfo=NEW_YORK).astimezone(timezone.utc)
            if moment >= maintenant:
                trouvees.append(moment.strftime("%Y-%m-%dT%H:%M:%SZ"))
                if len(trouvees) == nombre:
                    break
        jour += timedelta(days=1)
    return trouvees


def a_venir(evenements, maintenant):
    """Evenements pas encore termines, du plus proche au plus lointain."""
    garde = []
    for e in evenements:
        if "quand" in e:
            debut = horodatage(e["quand"])
            fini = debut + timedelta(hours=3)
        else:
            debut = datetime.fromisoformat(e["jour"]).replace(tzinfo=timezone.utc)
            fini = datetime.fromisoformat(e.get("fin_jour", e["jour"])).replace(tzinfo=timezone.utc) + timedelta(days=1)
        if fini >= maintenant:
            garde.append((debut, e))
    garde.sort(key=lambda x: x[0])
    return [e for _, e in garde]


def verifier(evenements):
    """Controle de forme du fichier de reference (leve une erreur explicite si une fiche est mal remplie)."""
    for e in evenements:
        nom = e.get("titre", "?")
        assert ("quand" in e) != ("jour" in e), f"{nom} : il faut soit « quand » (avec l'heure), soit « jour »"
        assert e["type"] in TYPES, f"{nom} : type inconnu"
        assert e["importance"] in IMPORTANCES, f"{nom} : importance inconnue"
        assert e["statut"] in STATUTS, f"{nom} : statut inconnu"
        assert e["marches"] and set(e["marches"]) <= MARCHES, f"{nom} : marches invalides"
        assert e.get("source"), f"{nom} : source manquante"
        assert e.get("lien") is None or e["lien"].startswith("https://"), f"{nom} : lien invalide"
        if "quand" in e:
            horodatage(e["quand"])
        else:
            date.fromisoformat(e["jour"])
            if "fin_jour" in e:
                assert date.fromisoformat(e["fin_jour"]) >= date.fromisoformat(e["jour"]), f"{nom} : fin avant le debut"


def construire(maintenant=None):
    maintenant = maintenant or datetime.now(timezone.utc)
    brut = json.loads(REFERENCE.read_text(encoding="utf-8"))
    verifier(brut["evenements"])
    return {
        "genere": maintenant.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verifie_le": brut["verifie_le"],
        "evenements": a_venir(brut["evenements"], maintenant),
        "hebdomadaires": [{**{k: r[k] for k in ("cle", "titre", "marches", "note", "lien")}, "prochaines": occurrences(r, maintenant)} for r in HEBDOMADAIRES],
    }


if __name__ == "__main__":
    agenda = construire()
    print(f"{len(agenda['evenements'])} événements à venir, dates vérifiées le {agenda['verifie_le']}")
    for e in agenda["evenements"]:
        print(" ", e.get("quand") or e["jour"], "|", e["statut"], "|", e["titre"])
    for h in agenda["hebdomadaires"]:
        print(" ", h["titre"], h["prochaines"])
    save_json(agenda, "agenda.json")

"""Fiche d'idees par marche : rassemble les indicateurs deja calcules par le site, avec leur FIABILITE STATISTIQUE.

Principe : un indicateur n'a pas la meme valeur selon qu'il a ete teste ou non. Chaque ligne de la fiche porte donc
  - sa LECTURE (haussier, baissier, neutre, ou « contexte » quand l'indicateur n'indique pas de sens) ;
  - sa FIABILITE : le verdict de l'onglet Strategies (demontre / non demontre / probable artefact) ou « non teste ».
Seuls les indicateurs issus d'une regle testee sont comptes dans la synthese. Rien ici n'est un conseil en investissement.

Ce module ne telecharge presque rien : il relit les fichiers de data/ (une seule requete, le positionnement des fonds
sur le gaz, qui peut echouer sans consequence).
"""
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import save_json

DATA = Path(__file__).resolve().parents[2] / "data"

# memes mots-cles que js/news.js (un test verifie qu'ils restent identiques)
MOTS = {
    "petrole": ["oil", "crude", "brent", "wti", "petrol", "pétrole", "opec", "opep",
                "baril", "barrel", "refin", "raffin", "shale", "drill", "offshore", "upstream"],
    "gaz": ["gas", "gaz", "lng", "gnl", "ttf", "henry hub", "pipeline", "methane", "méthane"],
    "electricite": ["electric", "électric", "power", "grid", "réseau", "renewable", "renouvelable",
                    "solar", "solaire", "wind", "éolien", "eolien", "nuclear", "nucléaire",
                    "utility", "utilities"],
}

# Instruments du simulateur CME : multiplicateur = dollars gagnes ou perdus pour 1,00 de variation du prix.
# Valeurs de connaissance generale des contrats, A CONFIRMER dans la fiche produit du simulateur.
INSTRUMENTS = {
    "petrole": [
        {"nom": "WTI Crude Oil", "code": "CL", "multiplicateur": 1000, "unite": "$/baril", "source_prix": "wti"},
        {"nom": "Micro WTI Crude Oil", "code": "MCL", "multiplicateur": 100, "unite": "$/baril", "source_prix": "wti"},
        {"nom": "Brent Crude", "code": "BZ", "multiplicateur": 1000, "unite": "$/baril", "source_prix": "brent"},
    ],
    "gaz": [
        {"nom": "Natural Gas (Henry Hub)", "code": "NG", "multiplicateur": 10000, "unite": "$/MMBtu", "source_prix": "hh"},
        {"nom": "Micro Henry Hub Natural Gas", "code": "MHNG", "multiplicateur": 1000, "unite": "$/MMBtu", "source_prix": "hh"},
    ],
    "electricite": [],
}


# ---------------------------------------------------------------- fonctions pures (testees)
def lecture_position(position):
    """Position theorique d'une regle (+1 / -1 / 0) -> lecture."""
    return "haussier" if position > 0 else "baissier" if position < 0 else "neutre"


def centile_cot(net, fenetre=156):
    """Part des (fenetre - 1) semaines precedentes dont la position nette est strictement inferieure a la derniere."""
    valeurs = np.asarray(net, dtype=float)
    if len(valeurs) < fenetre:
        return None
    w = valeurs[-fenetre:]
    return float((w[:-1] < w[-1]).mean())


def zscore_courant(serie, fenetre=252):
    """z-score de la derniere valeur par rapport aux `fenetre` dernieres (ecart-type d'echantillon)."""
    s = pd.Series(serie, dtype=float).dropna().iloc[-fenetre:]
    if len(s) < fenetre or s.std() == 0:
        return None
    return float((s.iloc[-1] - s.mean()) / s.std())


def volatilite_quotidienne(prix, jours=20):
    """Ecart-type des rendements logarithmiques quotidiens sur les derniers jours, en %."""
    s = pd.Series([p for p in prix if p is not None], dtype=float).iloc[-(jours + 1):]
    if len(s) < 6:
        return None
    return float(np.log(s).diff().dropna().std() * 100)


def classer_marches(titre):
    t = (titre or "").lower()
    return [m for m, mots in MOTS.items() if any(mot in t for mot in mots)]


def actualites(articles, marche, maintenant, nb_titres=6):
    """Volume d'articles recents du marche, rapporte au rythme moyen du dernier mois, et derniers titres."""
    dates = []
    pour_marche = []
    for a in articles:
        if marche not in classer_marches(a.get("titre")) or not a.get("date"):
            continue
        d = datetime.fromisoformat(a["date"])
        pour_marche.append((d, a))
    pour_marche.sort(key=lambda x: x[0], reverse=True)

    def depuis(jours):
        return sum(1 for d, _ in pour_marche if d >= maintenant - timedelta(days=jours))

    nb_7, nb_30 = depuis(7), depuis(30)
    rythme = nb_30 / 30 * 7
    return {
        "nb_24h": depuis(1), "nb_7j": nb_7, "nb_30j": nb_30,
        "rythme_hebdo_30j": round(rythme, 1),
        "ratio_vs_rythme": round(nb_7 / rythme, 2) if rythme > 0 else None,
        "derniers": [{"titre": a["titre"], "source": a.get("source"), "date": a["date"], "lien": a.get("lien")}
                     for _, a in pour_marche[:nb_titres]],
    }


def synthese(indicateurs):
    """Compte les indicateurs issus d'une regle testee (compte = True) et ceux dont le gain est demontre."""
    comptes = [i for i in indicateurs if i["compte"]]
    return {
        "haussiers": sum(1 for i in comptes if i["lecture"] == "haussier"),
        "baissiers": sum(1 for i in comptes if i["lecture"] == "baissier"),
        "neutres": sum(1 for i in comptes if i["lecture"] == "neutre"),
        "regles_comptees": len(comptes),
        "regles_demontrees": sum(1 for i in comptes if i["fiabilite"] == "demontre"),
    }


def phrase_synthese(s):
    h, b = s["haussiers"], s["baissiers"]
    if s["regles_comptees"] == 0:
        sens = "Aucune règle testée n'est disponible pour ce marché."
    elif h > b:
        sens = f"Les règles testées penchent du côté acheteur ({h} contre {b})."
    elif b > h:
        sens = f"Les règles testées penchent du côté vendeur ({b} contre {h})."
    else:
        sens = "Les règles testées ne donnent pas de sens clair."
    if s["regles_demontrees"] == 0 and s["regles_comptees"]:
        fiable = "Aucune n'a démontré un pouvoir de prévision : ce sont des hypothèses à tester en simulation, pas des signaux."
    elif s["regles_comptees"]:
        fiable = f"{s['regles_demontrees']} règle(s) sur {s['regles_comptees']} ont démontré un gain statistique."
    else:
        fiable = ""
    return f"{sens} {fiable}".strip()


def fr(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def sg(x, d=2):
    return ("+" if x > 0 else "−" if x < 0 else "") + fr(abs(x), d)


# ---------------------------------------------------------------- lecture des fichiers
def lire(nom):
    return json.loads((DATA / f"{nom}.json").read_text(encoding="utf-8"))


def dernier(serie):
    valeurs = [v for v in serie if v is not None]
    return valeurs[-1] if valeurs else None


def texte_verdict(verdict):
    """Phrase qui suit toujours le verdict reellement publie par l'onglet Strategies."""
    return {"artefact": "La règle de retour à la moyenne s'est révélée un artefact de mesure.",
            "non_demontre": "La règle de retour à la moyenne n'est pas démontrée.",
            "demontre": "La règle de retour à la moyenne a démontré un gain statistique."}.get(verdict, "")


def indicateur(cle, nom, valeur, lecture, detail, fiabilite="non_teste", compte=False):
    return {"cle": cle, "nom": nom, "valeur": valeur, "lecture": lecture, "detail": detail,
            "fiabilite": fiabilite, "compte": compte}


def depuis_regle(strat, cle, nom, detail):
    """Indicateur directement issu d'une regle de l'onglet Strategies."""
    s = next(x for x in strat["signaux"] if x["cle"] == cle)
    return indicateur(cle, nom, s["etat"]["libelle"], lecture_position(s["etat"]["position"]),
                      f"{detail} Depuis le {s['etat']['depuis'].split('-')[2]}/{s['etat']['depuis'].split('-')[1]}/{s['etat']['depuis'][:4]}.",
                      fiabilite=s["verdict"], compte=True)


# ---------------------------------------------------------------- les trois marches
def fiche_petrole():
    strat, oa, mar, risk, live = lire("strategies"), lire("oil_analysis"), lire("maritime"), lire("risk")["brent"], lire("oil_live")
    ind = [
        depuis_regle(strat, "momentum", "Tendance sur 63 jours (Brent)", "Le prix est comparé à celui d'il y a 63 jours."),
        depuis_regle(strat, "moyennes", "Moyennes mobiles 50 / 200 jours (Brent)", "Croisement de la moyenne 50 jours et de la moyenne 200 jours."),
        depuis_regle(strat, "cot", "Positionnement des fonds (COT, WTI)", "Lecture à contre-courant : les fonds très acheteurs sont vus comme un signal vendeur."),
    ]
    e = oa["ecart"]["stats"]
    verdict_ecart = next(x for x in strat["signaux"] if x["cle"] == "ecart")["verdict"]
    ind.append(indicateur("ecart", "Écart Brent − WTI (spot)", f"{fr(e['ecart_actuel'], 1)} $ (moyenne 1 an : {fr(e['moyenne_actuelle'], 1)} $), z = {sg(e['z_actuel'])}",
                          "contexte", "Un écart de plus de 2 écarts-types serait notable. " + texte_verdict(verdict_ecart), fiabilite=verdict_ecart))
    ormuz = next(d for d in mar["detroits"] if "Ormuz" in d["nom"])
    rupt = [d["nom"] for d in mar["detroits"] if d["zscore"] <= -2]
    ind.append(indicateur("maritime", "Trafic de pétroliers (Ormuz)", f"{fr(ormuz['actuel_7j'], 1)} pétroliers/jour contre {fr(ormuz['reference'], 1)} en 2025 (z = {sg(ormuz['zscore'], 1)})",
                          "contexte", f"{len(rupt)} détroit(s) sur {len(mar['detroits'])} en rupture ({', '.join(rupt) or 'aucun'}). Contexte d'offre, jamais testé comme signal d'achat ou de vente."))
    gs = oa["brent"]["monte_carlo"]["gaussien"]
    ind.append(indicateur("risque", "Risque du Brent à 30 jours", f"VaR 95 % : {fr(gs['var95'], 1)} %",
                          "contexte", "Perte qu'on ne dépasse pas 95 % du temps sur 30 jours, selon le modèle. Sert à dimensionner une position, pas à choisir un sens."))
    prix_wti, prix_brent = live["wti"]["prix"], live["brent"]["prix"]
    sigma = risk["parametres"]["sigma_quotidien"] * 100
    instruments = []
    for i in INSTRUMENTS["petrole"]:
        prix = prix_wti if i["source_prix"] == "wti" else prix_brent
        instruments.append({**i, "prix": round(prix, 2), "sigma_quotidien_pct": round(sigma, 2)})
    return ind, instruments


def fiche_gaz(fonds_hh):
    strat, ga, gas = lire("strategies_gaz"), lire("gas_analysis"), lire("gas")
    ind = [
        depuis_regle(strat, "momentum", "Tendance sur 63 jours (Henry Hub)", "Le prix est comparé à celui d'il y a 63 jours."),
        depuis_regle(strat, "saison", "Saisonnalité du Henry Hub", "Sens moyen du même mois sur les années passées."),
    ]
    ec = ga["ecart"]
    z = zscore_courant(ec["ecart"])
    v_ttf = next(x for x in strat["signaux"] if x["cle"] == "ecart_ttf_hh")["verdict"]
    ind.append(indicateur("ecart_ttf_hh", "Écart TTF − Henry Hub", f"{fr(ec['stats']['actuel'], 1)} €/MWh (médiane : {fr(ec['stats']['mediane'], 1)}), centile {fr(ec['stats']['centile_actuel'], 0)} %"
                          + (f", z = {sg(z)}" if z is not None else ""),
                          "contexte", "Écart de prix entre l'Europe et les États-Unis. " + texte_verdict(v_ttf), fiabilite=v_ttf))
    gn = ga["gnl"]["stats"]
    v_jkm = next(x for x in strat["signaux"] if x["cle"] == "ecart_jkm_ttf")["verdict"]
    ind.append(indicateur("ecart_jkm_ttf", "Écart JKM − TTF (GNL Asie / Europe)", f"{sg(gn['actuel'])} $/MMBtu (médiane : {fr(gn['mediane'])}), centile {fr(gn['centile_actuel'], 0)} %",
                          "contexte", "Positif : le GNL vaut plus cher en Asie. " + texte_verdict(v_jkm), fiabilite=v_jkm))
    if fonds_hh is not None:
        c = fonds_hh["centile"]
        ind.append(indicateur("cot_hh", "Positionnement des fonds (COT, Henry Hub)", f"Centile {fr(c * 100, 0)} % ; position nette {sg(fonds_hh['net_pct'], 1)} % de l'intérêt ouvert",
                              "contexte", "Rapport du " + fonds_hh["date"] + ". Lecture à contre-courant jamais testée sur le gaz : affiché pour information."))
    vol = dernier(gas["series"]["ttf_vol"])
    if vol is not None:
        ind.append(indicateur("vol_ttf", "Volatilité du TTF", f"{fr(vol, 1)} % annualisée (7 jours)", "contexte", "Un marché plus nerveux demande des positions plus petites."))
    prix_hh = dernier(gas["series"]["henry_hub"])
    sigma = volatilite_quotidienne(gas["series"]["henry_hub"])
    instruments = []
    for i in INSTRUMENTS["gaz"]:
        instruments.append({**i, "prix": round(prix_hh, 3) if prix_hh else None, "sigma_quotidien_pct": round(sigma, 2) if sigma else None})
    return ind, instruments


def fiche_electricite():
    el, ea = lire("electricity"), lire("electricity_analysis")["fr"]
    par_jour = {}
    for d, f, a in zip(el["dates"], el["series"]["fr"], el["series"]["de_lu"]):
        if f is not None:
            par_jour.setdefault(d[:10], []).append((f, a))
    jour = sorted(par_jour)[-1]
    fr_moy = sum(f for f, _ in par_jour[jour]) / len(par_jour[jour])
    ecarts = [f - a for f, a in par_jour[jour] if a is not None]
    prof, neg = ea["profil"]["stats"], ea["negatifs"]["stats"]
    ind = [
        indicateur("prix_fr", "Prix de marché de la France (moyenne du jour)", f"{fr(fr_moy, 1)} €/MWh le {jour[8:]}/{jour[5:7]} (moyenne 12 mois : {fr(prof['moyenne'], 1)})",
                   "contexte", "Prix day-ahead : ce n'est pas un prix auquel on peut acheter ou vendre dans le simulateur."),
        indicateur("negatifs", "Prix négatifs (12 mois)", f"{fr(neg['pct_total'], 1)} % des quarts d'heure, {fr(neg['pct_weekend'], 0)} % le week-end",
                   "contexte", "Surproduction renouvelable face à une demande faible : un fait de marché, pas un signal."),
    ]
    if ecarts:
        ind.append(indicateur("couplage", "Écart France − Allemagne", f"{sg(sum(ecarts) / len(ecarts), 1)} €/MWh en moyenne le jour affiché", "contexte",
                              "Positif : l'électricité vaut plus cher en France qu'en Allemagne."))
    return ind, []


# ---------------------------------------------------------------- positionnement des fonds sur le gaz (facultatif)
def positionnement_gaz():
    try:
        from pipeline.sources.cot import CODES, fetch_net_fonds
        net = fetch_net_fonds(CODES["henry_hub"])
        c = centile_cot(net)
        if c is None:
            return None
        return {"centile": c, "net_pct": float(net.iloc[-1]) * 100, "date": net.index[-1].strftime("%d/%m/%Y")}
    except Exception as erreur:        # le reseau ou la CFTC peut etre indisponible : l'indicateur est simplement omis
        print("COT gaz indisponible :", erreur)
        return None


# ---------------------------------------------------------------- assemblage
def construire():
    maintenant = datetime.now(timezone.utc)
    articles = lire("news")["articles"]
    marches = {}
    for cle, (ind, instruments) in {"petrole": fiche_petrole(), "gaz": fiche_gaz(positionnement_gaz()), "electricite": fiche_electricite()}.items():
        s = synthese(ind)
        marches[cle] = {
            "indicateurs": ind, "synthese": s, "phrase": phrase_synthese(s),
            "actualites": actualites(articles, cle, maintenant), "instruments": instruments,
        }
    return {"genere": maintenant.strftime("%Y-%m-%dT%H:%M:%SZ"), "marches": marches}


if __name__ == "__main__":
    fiche = construire()
    for cle, m in fiche["marches"].items():
        print(f"\n== {cle} : {m['phrase']}")
        for i in m["indicateurs"]:
            print(f"  [{i['lecture']:9s}|{i['fiabilite']:12s}] {i['nom']} : {i['valeur']}")
        a = m["actualites"]
        print(f"  actualités : {a['nb_24h']} / 24 h, {a['nb_7j']} / 7 j (rythme {a['rythme_hebdo_30j']}, x{a['ratio_vs_rythme']})")
        for i in m["instruments"]:
            print(f"  instrument {i['code']} : prix {i['prix']}, sigma {i['sigma_quotidien_pct']} %")
    save_json(fiche, "idees.json")

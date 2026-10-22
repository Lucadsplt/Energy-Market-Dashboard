"""Regles de trading testees sur le gaz, evaluees par le meme moteur que le petrole.

Les quatre regles sont fixees AVANT de regarder les resultats. Pour les ecarts (TTF - Henry Hub, JKM - TTF),
les prix sont releves a des heures differentes : on s'attend a un risque d'artefact de mesure, que le test
de retard d'execution permet de detecter.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.gas_spread import MWH_PAR_MMBTU
from pipeline.analysis.strategies_engine import (COUT_PAR_JAMBE, RETARD_REFERENCE, evaluer, metriques,
                                                 p_valeur_bootstrap, verdict)
from pipeline.analysis.strategies_oil import courbe_mensuelle, depuis_quand, libelle_position
from pipeline.export.json_export import save_json
from pipeline.sources.gas_history import fetch_close, fetch_eurusd

NB_TESTS = 4
SEUIL_CORRIGE = 0.05 / NB_TESTS
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


# ------------------------------------------------------------------ les quatre regles
# Chaque regle renvoie : rendements de l'actif, position, cout, libelle d'etat, prix de reference, date de coupure.
def regle_momentum(hh, fenetre=63):
    """Tendance : acheteur si le Henry Hub est plus haut qu'il y a 3 mois, vendeur sinon."""
    position = np.sign(hh / hh.shift(fenetre) - 1).fillna(0)
    etat = libelle_position(position.iloc[-1], "Acheteur : le Henry Hub est plus haut qu'il y a 63 jours",
                            "Vendeur : le Henry Hub est plus bas qu'il y a 63 jours", "Hors marché")
    return hh.pct_change(), position, COUT_PAR_JAMBE, etat, hh, "2013-01-01"


def regle_saison(hh, annees_min=5):
    """Saisonnalite sans regard dans le futur : pour chaque mois, on regarde la hausse moyenne de CE mois
    sur les annees PASSEES seulement. Acheteur si elle est positive, vendeur sinon (hors marche avant 5 ans d'historique)."""
    mensuel = np.log(hh).resample("ME").last().diff().dropna()
    table = pd.DataFrame({"r": mensuel.values, "annee": mensuel.index.year, "mois": mensuel.index.month})

    signal = {}
    for annee, mois in sorted({(d.year, d.month) for d in hh.index}):
        passe = table[(table["mois"] == mois) & (table["annee"] < annee)]["r"]
        signal[(annee, mois)] = float(np.sign(passe.mean())) if len(passe) >= annees_min else 0.0
    position = pd.Series([signal[(d.year, d.month)] for d in hh.index], index=hh.index)

    d = hh.index[-1]
    passe = table[(table["mois"] == d.month) & (table["annee"] < d.year)]["r"]
    moyenne = float(passe.mean()) * 100
    etat = libelle_position(position.iloc[-1],
                            f"Acheteur : en {MOIS[d.month - 1]}, le Henry Hub a monté de {moyenne:.1f} % en moyenne sur {len(passe)} ans",
                            f"Vendeur : en {MOIS[d.month - 1]}, le Henry Hub a baissé de {abs(moyenne):.1f} % en moyenne sur {len(passe)} ans",
                            "Hors marché")
    return hh.pct_change(), position, COUT_PAR_JAMBE, etat, hh, "2013-01-01"


def regle_ecart(ecart, base, fenetre=252, entree=2.0, sortie=0.5):
    """Retour a la moyenne d'un ecart : on parie sur son retour quand son z-score depasse 2 ; on sort sous 0,5."""
    z = (ecart - ecart.rolling(fenetre).mean()) / ecart.rolling(fenetre).std()

    position = pd.Series(0.0, index=z.index)
    en_cours = 0.0
    for date, valeur in z.items():
        if np.isnan(valeur):
            continue
        if en_cours == 0 and valeur > entree:
            en_cours = -1.0
        elif en_cours == 0 and valeur < -entree:
            en_cours = 1.0
        elif en_cours != 0 and abs(valeur) < sortie:
            en_cours = 0.0
        position[date] = en_cours

    rend_ecart = ecart.diff() / base.shift(1)       # gain de l'ecart rapporte au prix de la jambe de reference
    z_actuel = float(z.iloc[-1])
    etat = libelle_position(position.iloc[-1],
                            f"Acheteur d'écart : z-score de {z_actuel:+.1f}, on parie sur sa hausse",
                            f"Vendeur d'écart : z-score de {z_actuel:+.1f}, on parie sur sa baisse",
                            f"Hors marché : z-score de {z_actuel:+.1f} (seuil d'entrée ±2)")
    return rend_ecart, position, COUT_PAR_JAMBE, etat, None, "2022-01-01"     # normalise par les deux jambes : 5 pb de l'exposition totale


# ------------------------------------------------------------------ construction des ecarts
def serie_ttf_hh(ttf, hh, fx):
    """Ecart TTF - Henry Hub en EUR/MWh, et prix du Henry Hub converti (jambe de reference)."""
    df = pd.concat({"ttf": ttf, "hh": hh, "fx": fx}, axis=1)
    df["fx"] = df["fx"].ffill()
    df = df.dropna()
    hh_eur = df["hh"] / MWH_PAR_MMBTU / df["fx"]
    return df["ttf"] - hh_eur, df["ttf"] + hh_eur       # ecart, exposition totale (les deux jambes)


def serie_jkm_ttf(jkm, ttf, fx):
    """Ecart JKM - TTF en $/MMBtu, et prix du TTF converti (jambe de reference)."""
    df = pd.concat({"jkm": jkm, "ttf": ttf, "fx": fx}, axis=1)
    df["fx"] = df["fx"].ffill()
    df = df.dropna()
    ttf_usd = df["ttf"] * MWH_PAR_MMBTU * df["fx"]
    return df["jkm"] - ttf_usd, df["jkm"] + ttf_usd     # ecart, exposition totale (les deux jambes)


# ------------------------------------------------------------------ orchestration
def analyse_strategies_gaz():
    hh = fetch_close("NG=F")
    ttf = fetch_close("TTF=F")
    jkm = fetch_close("JKM=F")
    fx = fetch_eurusd()

    ecart_ttf_hh, hh_eur = serie_ttf_hh(ttf, hh, fx)
    ecart_jkm_ttf, ttf_usd = serie_jkm_ttf(jkm, ttf, fx)


    regles = [
        ("momentum", "Tendance sur 63 jours", "Henry Hub", regle_momentum(hh),
         "Si le prix est plus haut qu'il y a trois mois, on est acheteur ; sinon vendeur."),
        ("saison", "Saisonnalité du Henry Hub", "Henry Hub", regle_saison(hh),
         "Chaque mois, on suit ce qu'a fait ce même mois sur les années passées : acheteur s'il a plutôt monté, vendeur sinon (au moins 5 ans d'historique)."),
        ("ecart_ttf_hh", "Écart TTF − Henry Hub : retour à la moyenne", "Écart TTF − Henry Hub", regle_ecart(ecart_ttf_hh, hh_eur),
         "Quand l'écart s'éloigne de plus de 2 écarts-types de sa moyenne sur un an, on parie sur son retour ; on sort sous 0,5 écart-type."),
        ("ecart_jkm_ttf", "Écart JKM − TTF : retour à la moyenne", "Écart JKM − TTF", regle_ecart(ecart_jkm_ttf, ttf_usd),
         "Même principe sur l'arbitrage du GNL entre l'Asie et l'Europe."),
    ]

    signaux = []
    for cle, nom, actif, (rend, position, cout, etat, prix_ref, coupure), regle in regles:
        evaluation = evaluer(rend, position, cout, coupure)
        cle_verdict, explication = verdict(evaluation, SEUIL_CORRIGE)
        signaux.append({
            "cle": cle, "nom": nom, "actif": actif, "regle": regle,
            "metriques": evaluation["metriques"],
            "metriques_sans_retard": evaluation["metriques_sans_retard"],
            "retard": evaluation["retard"],
            "sous_periodes": evaluation["sous_periodes"],
            "p_valeur": evaluation["p_valeur"],
            "verdict": cle_verdict,
            "explication": explication,
            "courbe": courbe_mensuelle(evaluation["net"], prix_ref),
            "etat": {"libelle": etat, "depuis": depuis_quand(position), "position": float(position.iloc[-1])},
        })

    achat_garde = hh.pct_change().fillna(0)
    reference = metriques(achat_garde, pd.Series(1.0, index=achat_garde.index))
    reference["p_valeur"] = round(p_valeur_bootstrap(achat_garde), 3)

    return {
        "meta": {
            "periode": f"{hh.index[0].strftime('%Y-%m-%d')} → {hh.index[-1].strftime('%Y-%m-%d')}",
            "cout_pb_par_jambe": COUT_PAR_JAMBE * 10000,
            "retard_reference_jours": RETARD_REFERENCE,
            "nb_tests": NB_TESTS,
            "seuil_corrige": round(SEUIL_CORRIGE, 4),
            "donnees": "Contrats à terme continus Henry Hub (NG=F), TTF (TTF=F), JKM (JKM=F) et EUR/USD, Yahoo Finance",
        },
        "reference": reference,
        "signaux": signaux,
    }


if __name__ == "__main__":
    resultat = analyse_strategies_gaz()
    print(resultat["meta"]["periode"])
    for s in resultat["signaux"]:
        m = s["metriques"]
        print(f'{s["nom"]:48s} Sharpe {s["metriques_sans_retard"]["sharpe"]:+.2f} (sans retard) -> {m["sharpe"]:+.2f} (1 j) | '
              f'hasard {s["p_valeur"]:.3f} | {s["verdict"]}')
        print(f'      état actuel : {s["etat"]["libelle"]}')
    save_json(resultat, "strategies_gaz.json")
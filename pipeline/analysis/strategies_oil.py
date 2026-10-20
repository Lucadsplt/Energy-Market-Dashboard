"""Regles de trading testees sur le petrole, evaluees par le moteur de backtest.

Les quatre regles ont ete choisies et fixees AVANT de regarder leurs resultats : aucun parametre n'est ajuste
pour « faire marcher » une regle. Ce sont des hypotheses classiques, pas des recommandations.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.strategies_engine import (COUT_PAR_JAMBE, RETARD_REFERENCE, evaluer, metriques, p_valeur_bootstrap,
                                                 rendements_nets, verdict)
from pipeline.export.json_export import save_json
from pipeline.sources.cot import CODES, fetch_net_fonds
from pipeline.sources.oil_history import fetch_brent_history, fetch_brent_wti_history

DEBUT = "2000-01-01"
NB_TESTS = 4
SEUIL_CORRIGE = 0.05 / NB_TESTS      # correction de Bonferroni : 4 regles essayees, il faut etre 4 fois plus exigeant


def depuis_quand(position):
    """Date a laquelle la position actuelle a commence."""
    changements = position[position.diff().fillna(0) != 0]
    return changements.index[-1].strftime("%Y-%m-%d") if len(changements) else position.index[0].strftime("%Y-%m-%d")


def libelle_position(valeur, achat, vente, neutre):
    return achat if valeur > 0 else vente if valeur < 0 else neutre


# ------------------------------------------------------------------ les quatre regles
def regle_momentum(brent, fenetre=63):
    """Tendance : acheteur si le Brent est plus haut qu'il y a 3 mois, vendeur sinon."""
    position = np.sign(brent / brent.shift(fenetre) - 1).fillna(0)
    etat = libelle_position(position.iloc[-1], "Acheteur : le Brent est plus haut qu'il y a 63 jours",
                            "Vendeur : le Brent est plus bas qu'il y a 63 jours", "Hors marché")
    return brent.pct_change(), position, COUT_PAR_JAMBE, etat, brent


def regle_moyennes(brent, courte=50, longue=200):
    """Croisement de moyennes mobiles : acheteur si la moyenne 50 jours est au-dessus de la moyenne 200 jours."""
    position = np.sign(brent.rolling(courte).mean() - brent.rolling(longue).mean()).fillna(0)
    etat = libelle_position(position.iloc[-1], "Acheteur : la moyenne 50 jours est au-dessus de la moyenne 200 jours",
                            "Vendeur : la moyenne 50 jours est sous la moyenne 200 jours", "Hors marché")
    return brent.pct_change(), position, COUT_PAR_JAMBE, etat, brent


def regle_ecart(brent, wti, fenetre=252, entree=2.0, sortie=0.5):
    """Retour a la moyenne de l'ecart Brent - WTI : on parie sur son retour quand son z-score depasse 2."""
    df = pd.concat({"b": brent, "w": wti}, axis=1).dropna()
    ecart = df["b"] - df["w"]
    z = (ecart - ecart.rolling(fenetre).mean()) / ecart.rolling(fenetre).std()

    position = pd.Series(0.0, index=z.index)
    en_cours = 0.0
    for date, valeur in z.items():
        if np.isnan(valeur):
            continue
        if en_cours == 0 and valeur > entree:
            en_cours = -1.0                      # ecart anormalement haut : on parie sur sa baisse
        elif en_cours == 0 and valeur < -entree:
            en_cours = 1.0
        elif en_cours != 0 and abs(valeur) < sortie:
            en_cours = 0.0
        position[date] = en_cours

    rend_ecart = ecart.diff() / df["w"].shift(1)         # gain de l'ecart rapporte au prix du WTI
    z_actuel = float(z.iloc[-1])
    etat = libelle_position(position.iloc[-1],
                            f"Acheteur d'écart : z-score de {z_actuel:+.1f}, on parie sur sa hausse",
                            f"Vendeur d'écart : z-score de {z_actuel:+.1f}, on parie sur sa baisse",
                            f"Hors marché : z-score de {z_actuel:+.1f} (seuil d'entrée ±2)")
    return rend_ecart, position, 2 * COUT_PAR_JAMBE, etat, None      # deux jambes : deux fois les frais


def regle_cot(wti):
    """Positionnement des fonds (COT) a contre-courant : vendeur quand ils sont tres acheteurs, et inversement."""
    net = fetch_net_fonds(CODES["wti"])
    centile = net.rolling(156, min_periods=156).apply(lambda w: (w[:-1] < w[-1]).mean(), raw=True)
    signal = pd.Series(0.0, index=centile.index)
    signal[centile > 0.9] = -1.0
    signal[centile < 0.1] = 1.0
    signal.index = signal.index + pd.Timedelta(days=3)           # donnees du mardi, publiees le vendredi
    position = signal.reindex(wti.index, method="ffill").fillna(0)
    dernier = float(centile.dropna().iloc[-1])
    etat = libelle_position(position.iloc[-1], f"Acheteur : fonds très vendeurs (centile {dernier * 100:.0f})",
                            f"Vendeur : fonds très acheteurs (centile {dernier * 100:.0f})",
                            f"Hors marché : positionnement des fonds banal (centile {dernier * 100:.0f})")
    return wti.pct_change(), position, COUT_PAR_JAMBE, etat, wti


# ------------------------------------------------------------------ orchestration
def courbe_mensuelle(net, reference_prix):
    """Valeur d'un placement de 100 au debut, a la fin de chaque mois : strategie (apres couts) et reference."""
    strat = (1 + net.dropna()).cumprod() * 100
    mensuel = strat.resample("ME").last()
    sortie = {"dates": [d.strftime("%Y-%m") for d in mensuel.index], "strategie": [round(float(v), 1) for v in mensuel]}
    if reference_prix is not None:
        ref = (1 + reference_prix.reindex(strat.index).pct_change().fillna(0)).cumprod() * 100
        sortie["reference"] = [round(float(v), 1) for v in ref.resample("ME").last().reindex(mensuel.index)]
    return sortie


def analyse_strategies_petrole():
    brent = fetch_brent_history(years=28)
    brent = brent[brent.index >= DEBUT]
    donnees = fetch_brent_wti_history(years=28)
    wti = donnees["wti"][donnees.index >= DEBUT]
    wti = wti[wti > 5]                                   # on retire les jours de prix quasi nuls (avril 2020)

    regles = [
        ("momentum", "Tendance sur 63 jours", "Brent", regle_momentum(brent),
         "Si le prix est plus haut qu'il y a trois mois, on est acheteur ; sinon vendeur. Position inversée chaque fois que la tendance change."),
        ("moyennes", "Moyennes mobiles 50 / 200 jours", "Brent", regle_moyennes(brent),
         "Acheteur quand la moyenne des 50 derniers jours passe au-dessus de celle des 200 derniers jours, vendeur dans le cas contraire."),
        ("ecart", "Écart Brent − WTI : retour à la moyenne", "Écart Brent − WTI", regle_ecart(brent, wti),
         "Quand l'écart s'éloigne de plus de 2 écarts-types de sa moyenne sur un an, on parie sur son retour ; on sort sous 0,5 écart-type."),
        ("cot", "Positionnement des fonds (COT) à contre-courant", "WTI", regle_cot(wti),
         "Vendeur quand la position nette des fonds spéculatifs est dans les 10 % les plus acheteuses de ses 3 dernières années, acheteur dans les 10 % les plus vendeuses."),
    ]

    signaux = []
    for cle, nom, actif, (rend, position, cout, etat, prix_ref), regle in regles:
        evaluation = evaluer(rend, position, cout)
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

    # reference : acheter et garder le Brent
    achat_garde = brent.pct_change().fillna(0)
    reference = metriques(achat_garde, pd.Series(1.0, index=achat_garde.index))
    reference["p_valeur"] = round(p_valeur_bootstrap(achat_garde), 3)

    return {
        "meta": {
            "periode": f"{brent.index[0].strftime('%Y-%m-%d')} → {brent.index[-1].strftime('%Y-%m-%d')}",
            "cout_pb_par_jambe": COUT_PAR_JAMBE * 10000,
            "retard_reference_jours": RETARD_REFERENCE,
            "nb_tests": NB_TESTS,
            "seuil_corrige": round(SEUIL_CORRIGE, 4),
            "donnees": "Prix spot Brent et WTI (FRED) ; positions des fonds (CFTC, rapports COT)",
        },
        "reference": reference,
        "signaux": signaux,
    }


if __name__ == "__main__":
    resultat = analyse_strategies_petrole()
    print(resultat["meta"]["periode"])
    for s in resultat["signaux"]:
        m = s["metriques"]
        print(f'{s["nom"]:48s} Sharpe {s["metriques_sans_retard"]["sharpe"]:+.2f} (sans retard) -> {m["sharpe"]:+.2f} (1 j) | '
              f'hasard {s["p_valeur"]:.3f} | {s["verdict"]}')
        print(f'      état actuel : {s["etat"]["libelle"]}')
    save_json(resultat, "strategies.json")

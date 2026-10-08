import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.distribution import distribution
from pipeline.analysis.monte_carlo import calibrer, resumer, simuler
from pipeline.analysis.returns import log_returns
from pipeline.export.json_export import save_json
from pipeline.sources.oil_history import fetch_brent_history

HORIZON = 30
VARIATIONS = [-20, -10, 10, 20]    # niveaux testes, en % du prix actuel


def monte_carlo_petrole(prix, kurtosis):
    """Compare les chocs gaussiens et les chocs a queues epaisses (Student)."""
    params = calibrer(prix)
    dernier = float(prix.iloc[-1])
    x0 = np.log(dernier)
    df = 6 / kurtosis + 4                       # epaisseur des queues deduite du kurtosis

    chemins = {
        "gaussien": simuler(params, x0, HORIZON),
        "queues_epaisses": simuler(params, x0, HORIZON, df=df),
    }

    # memes barres d'histogramme pour les deux, pour pouvoir les comparer
    finaux = [c[-1] for c in chemins.values()]
    bas = min(np.percentile(f, 0.5) for f in finaux)
    haut = max(np.percentile(f, 99.5) for f in finaux)

    resultat = {"dernier_prix": round(dernier, 2), "horizon_jours": HORIZON, "df": round(float(df), 1)}
    for nom, c in chemins.items():
        comptes, bords = np.histogram(c[-1], bins=40, range=(bas, haut))
        resume = resumer(c, dernier)
        probas = []
        for v in VARIATIONS:
            seuil = dernier * (1 + v / 100)
            # perte : on teste si le prix descend jusqu'au seuil a un moment ; gain : s'il monte
            touche = c.min(axis=0) <= seuil if v < 0 else c.max(axis=0) >= seuil
            probas.append({"variation": v, "seuil": round(seuil, 1), "proba": round(float(touche.mean() * 100), 1)})
        resultat[nom] = {
            "histogramme": {
                "centres": ((bords[:-1] + bords[1:]) / 2).round(1).tolist(),
                "pourcent": (comptes / len(c[-1]) * 100).round(2).tolist(),
            },
            "mediane": round(float(np.median(c[-1])), 1),
            "var95": round(resume["var95"], 1),
            "es95": round(resume["es95"], 1),
            "probas": probas,
        }
    return resultat


def analyse_petrole():
    prix = fetch_brent_history(years=5)
    dist = distribution(log_returns(prix))
    return {"brent": {
        "distribution": dist,
        "monte_carlo": monte_carlo_petrole(prix, dist["stats"]["kurtosis_exces"]),
    }}


if __name__ == "__main__":
    resultat = analyse_petrole()
    mc = resultat["brent"]["monte_carlo"]
    print("df =", mc["df"])
    for nom in ("gaussien", "queues_epaisses"):
        print(nom, "VaR", mc[nom]["var95"], "ES", mc[nom]["es95"], mc[nom]["probas"])
    save_json(resultat, "oil_analysis.json")
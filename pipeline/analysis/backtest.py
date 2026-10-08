import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.monte_carlo import calibrer, simuler


def kupiec(n_tests, n_depassements, p=0.05):
    """Test de Kupiec : le taux de depassements observe est-il compatible avec p ?

    Renvoie une valeur p : > 0.05 = on ne peut pas rejeter le modele.
    """
    x, n = n_depassements, n_tests
    if x == 0:
        lr = -2 * n * math.log(1 - p)
    else:
        taux = x / n
        lr = (-2 * ((n - x) * math.log(1 - p) + x * math.log(p))
              + 2 * ((n - x) * math.log(1 - taux) + x * math.log(taux)))
    return math.erfc(math.sqrt(max(lr, 0) / 2))


def backtest_var(prix, fenetre_ans, horizon=30, pas=30, debut="2008-01-01", n=2000):
    """Backtest de la VaR 95 % a `horizon` jours, pour une fenetre de calibration donnee.

    A chaque date t (tous les `pas` jours) :
      1. calibrer sur les `fenetre_ans` annees AVANT t (jamais apres : pas de triche)
      2. simuler et lire les percentiles 5 % et 95 % du rendement a `horizon` jours
      3. comparer au rendement reel observe `horizon` jours plus tard
    """
    dates = prix.index
    premier = int(np.searchsorted(dates, pd.Timestamp(debut)))
    bas = haut = ignores = tests = 0
    var_moyenne = []

    for i in range(premier, len(prix) - horizon, pas):
        t = dates[i]
        passe = prix[(dates > t - pd.DateOffset(years=fenetre_ans)) & (dates <= t)]
        try:
            params = calibrer(passe)
        except ValueError:          # pas de retour a la moyenne detecte : date ignoree
            ignores += 1
            continue

        dernier = float(passe.iloc[-1])
        chemins = simuler(params, np.log(dernier), horizon, n=n, seed=1)
        rend_sim = chemins[-1] / dernier - 1
        seuil_bas, seuil_haut = np.percentile(rend_sim, [5, 95])

        reel = float(prix.iloc[i + horizon]) / dernier - 1
        tests += 1
        bas += int(reel < seuil_bas)
        haut += int(reel > seuil_haut)
        var_moyenne.append(-seuil_bas * 100)

    return {
        "fenetre_ans": fenetre_ans,
        "tests": tests,
        "ignores": ignores,
        "depassement_bas_pct": round(bas / tests * 100, 1),
        "depassement_haut_pct": round(haut / tests * 100, 1),
        "p_kupiec": round(kupiec(tests, bas), 3),
        "var_moyenne": round(float(np.mean(var_moyenne)), 1),
    }
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.monte_carlo import calibrer, resumer, simuler
from pipeline.export.json_export import save_json
from pipeline.sources.oil_history import fetch_brent_history

HORIZON = 30    # jours ouvres simules


def rapport_brent():
    prix = fetch_brent_history(years=10)
    params = calibrer(prix)
    dernier = float(prix.iloc[-1])

    chemins = simuler(params, np.log(dernier), HORIZON)
    resume = resumer(chemins, dernier)

    dates_futures = pd.bdate_range(prix.index[-1] + pd.Timedelta(days=1), periods=HORIZON)
    recent = prix.tail(90)
    return {
        "historique": {
            "dates": [d.strftime("%Y-%m-%d") for d in recent.index],
            "prix": [round(float(v), 2) for v in recent],
        },
        "futur": {"dates": [d.strftime("%Y-%m-%d") for d in dates_futures], **resume["bandes"]},
        "parametres": {
            "kappa": round(float(params["kappa"]), 5),
            "mu_prix": round(float(np.exp(params["mu"])), 2),
            "sigma_quotidien": round(float(params["sigma"]), 5),
        },
        "risque": {"var95": round(resume["var95"], 2), "es95": round(resume["es95"], 2)},
        "dernier_prix": round(dernier, 2),
        "horizon_jours": HORIZON,
    }


if __name__ == "__main__":
    rapport = {"brent": rapport_brent()}
    print(rapport["brent"]["parametres"], rapport["brent"]["risque"])
    save_json(rapport, "risk.json")
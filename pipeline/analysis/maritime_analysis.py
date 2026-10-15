import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.maritime import analyse_detroits
from pipeline.export.json_export import save_json
from pipeline.sources.oil_history import fetch_brent_history
from pipeline.sources.portwatch import DETROITS, fetch_all_detroits

ORMUZ = "Strait of Hormuz"


def analyse_maritime():
    df = fetch_all_detroits(depuis="2025-01-01")
    moy7 = df.rolling(7).mean().dropna()                 # jours ou la moyenne 7 jours existe

    # prix spot du Brent (FRED), aligne sur les memes jours : vide quand FRED n'a pas encore publie
    brent = fetch_brent_history(years=3).reindex(moy7.index)

    return {
        "derniere_date": df.index[-1].strftime("%Y-%m-%d"),
        "ormuz_vs_brent": {
            "dates": [d.strftime("%Y-%m-%d") for d in moy7.index],
            "ormuz_7j": [round(float(v), 1) for v in moy7[ORMUZ]],
            "brent": [None if v != v else round(float(v), 2) for v in brent],
        },
        "detroits": analyse_detroits(df, DETROITS),
    }


if __name__ == "__main__":
    resultat = analyse_maritime()
    print("derniere date PortWatch :", resultat["derniere_date"])
    for d in resultat["detroits"]:
        print(f'{d["nom"]:24s} {d["actuel_7j"]:6} vs {d["reference"]:6}  ({d["variation_pct"]:+.0f} %, z = {d["zscore"]})')
    save_json(resultat, "maritime.json")
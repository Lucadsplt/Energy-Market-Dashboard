import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.price_profile import profil_horaire
from pipeline.export.json_export import save_json
from pipeline.sources.elec_history import fetch_electricity_history
from pipeline.analysis.negative_prices import prix_negatifs


def analyse_electricite():
    prix = fetch_electricity_history(days=365, zone="FR")
    return {"fr": {"profil": profil_horaire(prix), "negatifs": prix_negatifs(prix)}}


if __name__ == "__main__":
    resultat = analyse_electricite()
    print(resultat["fr"]["profil"]["stats"])
    print(resultat["fr"]["negatifs"]["stats"])
    save_json(resultat, "electricity_analysis.json")
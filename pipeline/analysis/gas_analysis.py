import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.seasonality import indice_saisonnier
from pipeline.export.json_export import save_json
from pipeline.sources.gas_history import fetch_gas_history


def analyse_gaz():
    ttf = fetch_gas_history("TTF=F")
    return {"ttf": {"saisonnalite": indice_saisonnier(ttf)}}


if __name__ == "__main__":
    resultat = analyse_gaz()
    print(resultat["ttf"]["saisonnalite"]["mediane"])
    save_json(resultat, "gas_analysis.json")
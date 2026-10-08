import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.analysis.gas_spread import ecart_ttf_hh
from pipeline.analysis.seasonality import indice_saisonnier
from pipeline.export.json_export import save_json
from pipeline.sources.gas_history import fetch_eurusd, fetch_gas_history


def analyse_gaz():
    ttf = fetch_gas_history("TTF=F")
    hh = fetch_gas_history("NG=F")
    return {
        "ttf": {"saisonnalite": indice_saisonnier(ttf)},
        "ecart": ecart_ttf_hh(ttf, hh, fetch_eurusd()),
    }


if __name__ == "__main__":
    resultat = analyse_gaz()
    print(resultat["ecart"]["stats"])
    save_json(resultat, "gas_analysis.json")
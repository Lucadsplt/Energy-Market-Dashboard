import sys
from pathlib import Path

import os
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

# Ajoute la racine du projet au chemin de recherche de Python
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import to_chart_json, save_json

load_dotenv()
fred_api_key = os.getenv("FRED_API_KEY")
fred = Fred(api_key=fred_api_key)

# Symboles FRED pour le pétrole
SERIES = {
    "brent": "DCOILBRENTEU",   # Europe
    "wti": "DCOILWTICO",       # US
}


def fetch_oil():
    """Recupere les prix spot du petrole (Brent et WTI) via FRED.

    Renvoie un DataFrame : une colonne par serie, indexe par date.
    """
    prix = {}
    for nom, code in SERIES.items():
        prix[nom] = fred.get_series(code)
    return pd.DataFrame(prix).tail(30)


if __name__ == "__main__":
    data = fetch_oil()
    data["spread"] = data["brent"] - data["wti"]
    print(data.tail())
    chart_data = to_chart_json(data)
    save_json(chart_data, "oil.json")
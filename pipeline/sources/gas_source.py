import sys
from pathlib import Path

import yfinance as yf
import pandas as pd

# Ajoute la racine du projet au chemin de recherche de Python
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import to_chart_json, save_json
from pipeline.analysis.volatility import rolling_volatility

# Symboles Yahoo Finance pour le gaz
TICKERS = {
    "ttf": "TTF=F",        # Europe (front-month)
    "henry_hub": "NG=F",   # US Henry Hub
}


def fetch_gas(period="1mo"):
    """Recupere les prix de cloture du gaz (TTF et Henry Hub).

    Renvoie un DataFrame : une colonne par marche, indexe par date.
    """
    prix = {}
    for nom, symbole in TICKERS.items():
        df = yf.Ticker(symbole).history(period=period)
        prix[nom] = df["Close"]
    return pd.DataFrame(prix)


if __name__ == "__main__":
    data = fetch_gas()
    data["ttf_vol"] = rolling_volatility(data["ttf"])
    data["henry_hub_vol"] = rolling_volatility(data["henry_hub"])
    print(data.tail())
    chart_data = to_chart_json(data)
    save_json(chart_data, "gas.json")
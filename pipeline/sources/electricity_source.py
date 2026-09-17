import sys
from pathlib import Path

import os
import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

# Ajoute la racine du projet au chemin de recherche de Python
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import to_chart_json, save_json

load_dotenv()
client = EntsoePandasClient(api_key=os.getenv("ENTSOE_API_KEY"))

# Zones de marche ENTSO-E
ZONES = {
    "fr": "FR",
    "de_lu": "DE_LU",
}


def fetch_electricity(days=3):
    """Recupere les prix day-ahead (FR + DE_LU) via ENTSO-E.

    Renvoie un DataFrame : une colonne par zone, indexe par datetime (15 min),
    en heure locale d'Europe centrale.
    """
    end = pd.Timestamp.now(tz="Europe/Brussels")
    start = end - pd.Timedelta(days=days)
    prix = {}
    for nom, code in ZONES.items():
        prix[nom] = client.query_day_ahead_prices(code, start=start, end=end)
    df = pd.DataFrame(prix)
    df.index = df.index.tz_convert("Europe/Brussels")   # <-- repasse en heure locale
    return df


if __name__ == "__main__":
    data = fetch_electricity()
    data["spread_fr_de"] = data["fr"] - data["de_lu"]   # <-- nouvelle ligne
    print(data.tail())
    chart_data = to_chart_json(data, date_format="%Y-%m-%d %H:%M")
    save_json(chart_data, "electricity.json")
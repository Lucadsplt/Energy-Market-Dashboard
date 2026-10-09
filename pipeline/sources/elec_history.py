import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from entsoe import EntsoePandasClient

sys.path.append(str(Path(__file__).resolve().parents[2]))

load_dotenv()
client = EntsoePandasClient(api_key=os.getenv("ENTSOE_API_KEY"))


def fetch_electricity_history(days=365, zone="FR"):
    """Prix day-ahead d'une zone sur les `days` derniers jours, en heure locale (Europe/Brussels)."""
    fin = pd.Timestamp.now(tz="Europe/Brussels").normalize()
    prix = client.query_day_ahead_prices(zone, start=fin - pd.Timedelta(days=days), end=fin)
    prix.index = prix.index.tz_convert("Europe/Brussels")
    return prix


if __name__ == "__main__":
    h = fetch_electricity_history()
    print(len(h), "points,", h.index[0], "->", h.index[-1])    # attendu : ~35 000 points (15 min)
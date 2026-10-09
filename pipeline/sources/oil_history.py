import os

import pandas as pd
from dotenv import load_dotenv
from fredapi import Fred

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))


def fetch_brent_history(years=5):
    """Prix spot du Brent (FRED) sur les `years` dernieres annees, sans valeurs vides."""
    prix = fred.get_series("DCOILBRENTEU").dropna()
    debut = prix.index[-1] - pd.DateOffset(years=years)
    return prix[prix.index >= debut]


def fetch_brent_wti_history(years=6):
    """Brent et WTI sur les `years` dernieres annees, aux jours ou les deux existent."""
    df = pd.DataFrame({
        "brent": fred.get_series("DCOILBRENTEU"),
        "wti": fred.get_series("DCOILWTICO"),
    }).dropna()
    return df[df.index >= df.index[-1] - pd.DateOffset(years=years)]


if __name__ == "__main__":
    h = fetch_brent_history()
    print(len(h), "points,", h.index[0].date(), "->", h.index[-1].date())   # attendu : ~1250 points

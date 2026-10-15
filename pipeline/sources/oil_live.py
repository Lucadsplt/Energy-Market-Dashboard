import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# Ajoute la racine du projet au chemin de recherche de Python
sys.path.append(str(Path(__file__).resolve().parents[2]))
from pipeline.export.json_export import save_json

# Contrats a terme du mois en cours (Yahoo Finance) : ce n'est PAS le prix spot de FRED.
#   - spot (FRED)   : prix du baril physique livre immediatement, publie avec ~1 semaine de retard
#   - terme (Yahoo) : prix d'un baril livre dans environ un mois, cote en continu
TICKERS = {
    "brent": "BZ=F",   # Brent, ICE
    "wti": "CL=F",     # WTI, NYMEX
}


def fetch_marche(symbole):
    """Dernier prix (intraday si disponible), cloture de la veille et 30 jours de clotures."""
    ticker = yf.Ticker(symbole)
    jours = ticker.history(period="1mo")["Close"].dropna()
    intraday = ticker.history(period="1d", interval="5m")["Close"].dropna()

    if len(intraday):
        prix, instant = float(intraday.iloc[-1]), intraday.index[-1]
    else:                                   # marche ferme / pas de donnee intraday
        prix, instant = float(jours.iloc[-1]), jours.index[-1]

    # la derniere cloture quotidienne peut etre celle du jour en cours : on cherche celle d'avant
    if jours.index[-1].date() == instant.date():
        veille = float(jours.iloc[-2])
    else:
        veille = float(jours.iloc[-1])

    return {
        "prix": round(prix, 2),
        "veille": round(veille, 2),
        "variation": round(prix - veille, 2),
        "variation_pct": round((prix / veille - 1) * 100, 2),
        "heure_utc": instant.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dates": [d.strftime("%Y-%m-%d") for d in jours.index],
        "clotures": [round(float(v), 2) for v in jours],
    }


def fetch_oil_live():
    return {nom: fetch_marche(symbole) for nom, symbole in TICKERS.items()}


if __name__ == "__main__":
    data = fetch_oil_live()
    for nom, d in data.items():
        print(nom, d["prix"], f"({d['variation']:+} / {d['variation_pct']:+} %)", d["heure_utc"])
    save_json(data, "oil_live.json")

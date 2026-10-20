import json
import urllib.parse
import urllib.request

import pandas as pd

# Rapports COT (Commitments of Traders), version « Disaggregated Futures Only » de la CFTC.
# Donnees publiques et gratuites ; le code du contrat ne change pas meme quand la CFTC renomme le marche.
URL = "https://publicreporting.cftc.gov/resource/72hh-3qpy.json"

CODES = {
    "wti": "067651",         # WTI, NYMEX (renomme « WTI-PHYSICAL » en 2022)
    "henry_hub": "023651",   # Henry Hub, NYMEX
}


def fetch_net_fonds(code):
    """Position nette des fonds speculatifs (« managed money ») en % de l'open interest, par date de rapport.

    net = (positions acheteuses - positions vendeuses) / open interest.
    La date est celle du mardi ; le rapport n'est publie que le vendredi suivant.
    """
    params = {
        "$select": "report_date_as_yyyy_mm_dd,open_interest_all,m_money_positions_long_all,m_money_positions_short_all",
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "5000",
    }
    with urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(params), timeout=90) as reponse:
        df = pd.DataFrame(json.load(reponse))

    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    for colonne in ("open_interest_all", "m_money_positions_long_all", "m_money_positions_short_all"):
        df[colonne] = pd.to_numeric(df[colonne])
    net = (df["m_money_positions_long_all"] - df["m_money_positions_short_all"]) / df["open_interest_all"]
    net.index = df["date"]
    return net


if __name__ == "__main__":
    net = fetch_net_fonds(CODES["wti"])
    print(len(net), "rapports,", net.index[0].date(), "->", net.index[-1].date(), "| dernier net :", round(float(net.iloc[-1]) * 100, 1), "% de l'OI")

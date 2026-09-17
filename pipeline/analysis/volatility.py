import pandas as pd


def rolling_volatility(prix, window=7):
    """Volatilite glissante d'une serie de prix.

    - rendements = variation en % d'un jour a l'autre (pct_change)
    - volatilite = ecart-type des rendements sur une fenetre glissante
    - annualisee via la regle de la racine du temps (x sqrt(252))
    Renvoie une Series : volatilite annualisee, en pourcentage.
    """
    rendements = prix.pct_change()
    vol = rendements.rolling(window).std()
    return vol * (252 ** 0.5) * 100   # annualisee, en %


# Auto-test : recupere le TTF et affiche sa volatilite glissante
if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from pipeline.sources.gas_source import fetch_gas

    df = fetch_gas()
    vol_ttf = rolling_volatility(df["ttf"])
    print(vol_ttf.tail(10))
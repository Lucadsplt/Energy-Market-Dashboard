import pandas as pd

MWH_PAR_MMBTU = 0.293071    # 1 MMBtu = 0,293071 MWh


def ecart_ttf_hh(ttf, hh, eurusd):
    """Ecart TTF - Henry Hub, en euros par MWh.

    Henry Hub est cote en $/MMBtu : on le convertit en EUR/MWh
    (division par MWh/MMBtu puis par le taux EUR/USD).
    """
    df = pd.concat({"ttf": ttf, "hh": hh, "fx": eurusd}, axis=1)
    df["fx"] = df["fx"].ffill()        # le change n'est pas cote certains jours : on reprend la veille
    df = df.dropna()                   # on garde les jours ou les 3 series existent

    df["hh_eur"] = df["hh"] / MWH_PAR_MMBTU / df["fx"]
    df["ecart"] = df["ttf"] - df["hh_eur"]

    e = df["ecart"]
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "ttf": df["ttf"].round(2).tolist(),
        "hh_eur": df["hh_eur"].round(2).tolist(),
        "ecart": e.round(2).tolist(),
        "stats": {
            "actuel": round(float(e.iloc[-1]), 1),
            "mediane": round(float(e.median()), 1),
            "minimum": round(float(e.min()), 1),
            "date_min": e.idxmin().strftime("%Y-%m-%d"),
            "maximum": round(float(e.max()), 1),
            "date_max": e.idxmax().strftime("%Y-%m-%d"),
            "centile_actuel": round(float((e < e.iloc[-1]).mean() * 100), 0),
        },
    }
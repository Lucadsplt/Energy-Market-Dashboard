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


def ecart_jkm_ttf(jkm, ttf, eurusd):
    """Ecart JKM - TTF, en $/MMBtu : arbitrage du GNL entre l'Asie et l'Europe.

    Le TTF est cote en EUR/MWh : on le convertit en $/MMBtu (x MWh par MMBtu, x taux EUR/USD)
    pour le comparer au JKM. Ecart > 0 : le GNL vaut plus cher en Asie (les cargaisons vont vers l'Asie) ;
    ecart < 0 : il vaut plus cher en Europe.
    """
    df = pd.concat({"jkm": jkm, "ttf": ttf, "fx": eurusd}, axis=1)
    df["fx"] = df["fx"].ffill()
    df = df.dropna()

    df["ttf_usd"] = df["ttf"] * MWH_PAR_MMBTU * df["fx"]
    df["ecart"] = df["jkm"] - df["ttf_usd"]

    e = df["ecart"]
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in df.index],
        "jkm": df["jkm"].round(2).tolist(),
        "ttf_usd": df["ttf_usd"].round(2).tolist(),
        "ecart": e.round(2).tolist(),
        "stats": {
            "jkm": round(float(df["jkm"].iloc[-1]), 2),
            "ttf_usd": round(float(df["ttf_usd"].iloc[-1]), 2),
            "actuel": round(float(e.iloc[-1]), 2),
            "mediane": round(float(e.median()), 2),
            "asie_plus_chere_pct": round(float((e > 0).mean() * 100), 0),
            "centile_actuel": round(float((e < e.iloc[-1]).mean() * 100), 0),
            "minimum": round(float(e.min()), 1),
            "date_min": e.idxmin().strftime("%Y-%m-%d"),
            "maximum": round(float(e.max()), 1),
            "date_max": e.idxmax().strftime("%Y-%m-%d"),
        },
    }

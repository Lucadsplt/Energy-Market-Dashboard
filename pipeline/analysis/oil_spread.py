from pipeline.analysis.zscore import zscore_glissant


def analyse_ecart(df, fenetre=252):
    """Z-score de l'ecart Brent - WTI et quelques chiffres cles."""
    ecart = df["brent"] - df["wti"]
    z, moyenne = zscore_glissant(ecart, fenetre)

    d = ecart.to_frame("ecart")
    d["moyenne"] = moyenne
    d["z"] = z
    d = d.dropna()                          # on retire les jours de "chauffe" de la fenetre

    return {
        "dates": [x.strftime("%Y-%m-%d") for x in d.index],
        "z": d["z"].round(2).tolist(),
        "stats": {
            "ecart_actuel": round(float(d["ecart"].iloc[-1]), 1),
            "moyenne_actuelle": round(float(d["moyenne"].iloc[-1]), 1),
            "z_actuel": round(float(d["z"].iloc[-1]), 2),
            "jours_extremes_pct": round(float((d["z"].abs() > 2).mean() * 100), 1),
        },
    }
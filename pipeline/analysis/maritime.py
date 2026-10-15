def zscore_vs_reference(moy7, annee_ref=2025):
    """Ecart de la moyenne 7 jours actuelle a l'annee de reference, en ecarts-types.

    On compare le niveau actuel a la distribution des moyennes 7 jours de l'annee de reference.
    """
    ref = moy7[moy7.index.year == annee_ref].dropna()
    return (moy7.iloc[-1] - ref.mean()) / ref.std(), ref.mean()


def analyse_detroits(df, noms, annee_ref=2025):
    """Pour chaque detroit : trafic actuel, reference, variation, z-score et mini-serie (90 jours)."""
    moy7 = df.rolling(7).mean()          # moyenne glissante sur 7 jours : lisse le bruit quotidien
    resultat = []
    for cle, nom in noms.items():
        z, ref = zscore_vs_reference(moy7[cle], annee_ref)
        actuel = float(moy7[cle].iloc[-1])
        resultat.append({
            "nom": nom,
            "actuel_7j": round(actuel, 1),
            "reference": round(float(ref), 1),
            "variation_pct": round(float((actuel / ref - 1) * 100), 0),
            "zscore": round(float(z), 1),
            "serie": [round(float(v), 1) for v in moy7[cle].tail(90)],
        })
    return resultat